from abc import ABC, abstractmethod
import logging
import os
import numpy as np
from enum import Enum
from llspy.libcudawrapper import (get_output_nx, get_output_ny,
                                  get_output_nz, RL_interface, camcor,
                                  camcor_init)
from llspy.camera import CameraParameters, calc_correction, selectiveMedianFilter
from llspy.arrayfun import interleave, deinterleave
from llspy.util import imsave

logger = logging.getLogger()


def interleaved(func):
    """ method decorator to interleave/deinterlave data before/after processing"""
    def wrapper(self, data):
        nc = data.shape[-4] if data.ndim > 3 else 1
        data = func(self, interleave(data))
        return deinterleave(data, nc)
    return wrapper


class ImgProcessor(ABC):
    """ Image Processor abstract class.

    All subclasses of ImgProcessor must override the process() method, which
    should accept a single numpy array and return a single processed array.
    channel_specific class attributes specify which of the parameters must
    be specified for each channel in the dataset
    """

    def __init__(self):
        super().__init__()

    def __call__(self, data, *args, **kwargs):
        assert isinstance(data, np.ndarray), 'Input to ImgProcessor must be np.ndarray'
        logger.debug('{} called with args {} on data with shape {}'
                     .format(self, args, data.shape))
        data = self.process(data, *args, **kwargs)
        if kwargs.get('callback', False):
            kwargs.get('callback')(data, *args, **kwargs)
        return data

    @abstractmethod
    def process(self, data):
        """ child classes override this method.

        must always accept a numpy array and return a numpy array (even)
        if not performing any changes to or calculations on the data.
        """
        pass

    def __repr__(self):
        name = self.__class__.__name__
        attrs = []
        for k, v in self.__dict__.items():
            if not isinstance(v, (int, str, float)):
                v = v.__class__.__name__
            attrs.append('{}={}'.format(k, v))

        attrs = ' <{}>'.format(','.join(attrs)) if len(attrs) else ''
        return "{}{}".format(name, attrs)

    @classmethod
    def from_llsdir(cls, llsdir=None, **kwargs):
        """ instantiate the class based on data from an llsdir object.

        All ImgProcessors should be able to be completely instanstiated by
        calling `ImgProcessor.from_llsdir(llsdir, **options)`,
        where `options` are any of the additional parameters required
        for instantiation that are not secific to the dataset.  All other
        ImgProcessor parameters should have a default value with the same
        dtype of the eventual value.  Validation of empty default values
        should be performed in __init__.
        """
        return cls(**kwargs)

    class ImgProcessorError(Exception):
        """ generic ImgProcessor Exception Class """
        pass

    class ImgProcessorInvalid(ImgProcessorError):
        """ Error for when the ImgProcessor has been improperly written """
        pass


class ImgWriter(ImgProcessor):
    pass


class FlashProcessor(ImgProcessor):
    """ Corrects flash artifact """

    verbose_name = 'Flash Artifact Correction'

    class Target(Enum):
        CPU = 'CPU'
        GPU = 'GPU'

    def __init__(self, data_roi, cam_params='file', perform_on=Target.CPU, data_shape=None):
        if not isinstance(perform_on, self.Target):
            try:
                perform_on = self.Target(perform_on.upper())
            except ValueError:
                raise ValueError('"{}" is not a valid FlashProcessor target'
                                 .format(perform_on))
        if not isinstance(cam_params, CameraParameters):
            try:
                cam_params = CameraParameters(cam_params)
            except Exception as e:
                raise self.ImgProcessorError('Error creating cam_params: {}'
                                             .format(e))
        # may raise an error... should catch here?
        self.cam_params = cam_params.get_subroi(data_roi)
        self.target = perform_on
        if self.target == self.Target.GPU:
            if not data_shape:
                raise self.ImgProcessorError('data_shape must be provided '
                                             'when requesting FlashProcessor '
                                             'on the gpu'
                                             .format(self.target))
            a, b, offset = self.cam_params.data[:3]
            camcor_init(data_shape, a, b, offset)
        super(FlashProcessor, self).__init__()

    @interleaved
    def process(self, data):
        """ interleaves and corrects 4D data, or just correct 3D """
        if self.target == self.Target.CPU:
            a, b, offset = self.cam_params.data[:3]
            return calc_correction(data, a, b, offset)
        else:
            return camcor(data)

    @classmethod
    def from_llsdir(cls, llsdir, **kwargs):
        kwargs.pop('data_roi')
        data_roi = llsdir.params.roi
        kwargs['data_shape'] = llsdir.data.shape[-4:]
        return cls(data_roi, **kwargs)


class SelectiveMedianProcessor(ImgProcessor):
    """correct bad pixels on sCMOS camera.

    guidoc: selective median filter as in Amat 2015
    """

    verbose_name = 'Selective Median Filter'
    gui_layout = {
        'background': (0, 1),
        'median_range': (0, 0),
        'with_mean': (0, 2),
    }

    def __init__(self, background=0, median_range=3, with_mean=True):
        super(SelectiveMedianProcessor, self).__init__()
        self.background = background
        self.median_range = median_range
        self.with_mean = with_mean

    def process(self, data):
        nc = data.shape[-4] if data.ndim > 3 else 1
        ny, nx = data.shape[-2:]
        if nc > 1:
            data = data.reshape(-1, ny, nx)
        data, _ = selectiveMedianFilter(data, self.background,
                                        self.median_range, self.with_mean)
        if nc > 1:
            data = data.reshape(nc, -1, ny, nx)
        return data


class DivisionProcessor(ImgProcessor):
    """ Divides and image by another image, e.g. for flatfield correction """

    class Projector(Enum):
        mean = 'mean'
        max = 'max'

    verbose_name = "Flatfield Correction"
    projectors = {
        'mean': lambda x: np.mean(x, 0),
        'max': lambda x: np.max(x, 0),
    }

    def __init__(self, divisor='file', projection=Projector.mean):
        if not isinstance(divisor, np.ndarray):
            pass
        # only accept 2D or 3D inputs (single channel, optional Z stack)
        if not 1 < divisor.ndim < 4:
            raise self.ImgProcessorError(
                'Divisor Image must have 2 or 3 dimensions')
        # convert all images to 2D with provided projector func
        if divisor.ndim == 3:
            divisor = self.projectors[projection.name](divisor)
        self.divisor = divisor

    def process(self, data):
        if (isinstance(self.divisor, np.ndarray) and
                (data.shape[-2:] != self.divisor.shape)):
            raise self.ImgProcessorError(
                'Cannot divide data with shape {} by divisor with shape {}'
                .format(data.shape, self.divisor.shape))
        return np.divide(data, self.divisor)


class BleachCorrectionProcessor(ImgProcessor):
    """ Divides and image by another image, e.g. for flatfield correction """

    verbose_name = "Bleach Correction"

    def __init__(self, first_timepoint):
        # convert first_timepoint into divisor
        # get mean above background
        zyx = range(first_timepoint.ndim)[-3:]
        self.first_mean = first_timepoint.mean(axis=tuple(zyx))

    def process(self, data):
        if data.ndim <= 3:
            scaler = self.first_mean / data.mean()
        elif data.ndim == 4:
            mean = data.mean(axis=(1, 2, 3))
            scaler = (self.first_mean / mean).reshape(data.shape[0], 1, 1, 1)
        else:
            raise self.ImgProcessorError('Bleach correction can only accept 3 or 4D')
        return np.multiply(data, scaler)

    @classmethod
    def from_llsdir(cls, llsdir, **kwargs):
        return cls(llsdir.data.asarray(t=0))


class TrimProcessor(ImgProcessor):
    """ trim pixels off of the edge each dimension in XYZ """

    verbose_name = "Volume Edge Trim"

    gui_layout = {
        'trim_x': (0, 0),
        'trim_y': (1, 0),
        'trim_z': (2, 0)
    }

    def __init__(self, trim_z=(0, 0), trim_y=(0, 0), trim_x=(0, 0)):
        self.slices = (np.s_[trim_z[0]:-trim_z[1]] if trim_z[1] else np.s_[trim_z[0]:],
                       np.s_[trim_y[0]:-trim_y[1]] if trim_y[1] else np.s_[trim_y[0]:],
                       np.s_[trim_x[0]:-trim_x[1]] if trim_x[1] else np.s_[trim_x[0]:])

    def process(self, data):
        if data.ndim > len(self.slices):
            self.slices = (np.s_[:],) * (data.ndim - 3) + self.slices
        return data[tuple(self.slices)]


class CUDADeconProcessor(ImgProcessor):
    """  Perform richardson lucy deconvolution on the GPU

    NOTE: needs to be called within a RLContext()
    """

    verbose_name = 'Deconvolution/Deskewing'
    gui_layout = {
        'background': (0, 1),
        'n_iters': (0, 0),
        'shift': (0, 2),
        'save_deskewed': (1, 0),
        'rescale': (1, 1),
    }

    def __init__(self, background=80.0, n_iters=10, shift=0,
                 save_deskewed=False, rescale=False, out_shape=None):
        self.background = background
        self.n_iters = n_iters
        self.shift = shift
        self.save_deskewed = save_deskewed
        self.rescale = rescale
        self.out_shape = out_shape

    def process(self, data):
        if hasattr(data, 'has_background'):
            if not data.has_background:
                self.background = 0
        nz, ny, nx = data.shape
        # must be 16 bit going in
        if not np.issubdtype(data.dtype, np.uint16):
            data = data.astype(np.uint16)
        if not data.flags['C_CONTIGUOUS']:
            data = np.ascontiguousarray(data)

        if self.out_shape is None:
            self.out_shape = (get_output_nz(), get_output_ny(), get_output_nx())
        else:
            try:
                assert len(self.out_shape) == 3
            except Exception:
                raise self.ImgProcessorError('CUDADeconProcessor out_shape must '
                                             'be an iterable with length==3')

        decon_result = np.empty(tuple(self.out_shape), dtype=np.float32)
        if self.save_deskewed:
            deskew_result = np.empty_like(decon_result)
        else:
            deskew_result = np.empty(1, dtype=np.float32)

        RL_interface(data, nx, ny, nz, decon_result, deskew_result,
                     self.background, self.rescale, self.save_deskewed,
                     self.n_iters, self.shift)

        # if save_deskewed was requested, data is returned as a tuple
        # stack it together to create a 4D dataset
        if self.save_deskewed:
            return np.stack((decon_result, deskew_result))
        else:
            return decon_result


class AffineProcessor(ImgProcessor):
    """ Perform Affine Transformation, e.g. for channel registration """

    verbose_name = "Channel Registration"

    def __init__(self, reg_file='file'):
        pass

    def process(self, data):
        return data


class RotateYProcessor(AffineProcessor):
    """ Subclass of affine processor, for simplified rotation of the image in Y """

    verbose_name = "Rotate to Coverslip"

    def __init__(self, angle):
        pass

    def process(self, data):
        return data

    @classmethod
    def from_llsdir(cls, llsdir, *args, **kwargs):
        return cls(*args, **kwargs)


class TiffWriter(ImgWriter):
    """ Subclass of affine processor, for simplified rotation of the image in Y """

    def __init__(self, output_dir='{datadir}', frmt='{t:04d}.tif'):
        self.outdir = output_dir
        self.format = frmt

    def process(self, data, nt):
        outpath = os.path.join(self.outdir, self.format.format(t=nt))
        imsave(data, outpath, dx=1, dz=1, dt=1, unit='micron')
        return data
