from abc import ABC, abstractmethod
import logging
import os
import numpy as np
from llspy.libcudawrapper import (get_output_nx, get_output_ny, get_output_nz,
                                  RL_interface, camcor, camcor_init, RLContext)
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
        """ child classes override this method """
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
    def from_llsdir(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    class ImgProcessorError(Exception):
        """ generic ImgProcessor Exception Class """
        pass


class FlashProcessor(ImgProcessor):
    """ Corrects flash artifact """

    data_specific = ('data_roi', 'data_shape')

    def __init__(self, cam_params, data_roi, target='cpu', data_shape=None):
        if target not in ('cpu', 'cuda', 'gpu'):
            raise ValueError('Unrecognized target ""{}" for FlashProcessor'
                             .format(target))
        if not isinstance(cam_params, CameraParameters):
            try:
                cam_params = CameraParameters(cam_params)
            except Exception as e:
                raise self.ImgProcessorError('Error creating cam_params: {}'
                                             .format(e))
        # may raise an error... should catch here?
        self.cam_params = cam_params.get_subroi(data_roi)
        self.data_roi = data_roi
        self.target = target
        if self.target == 'gpu':
            if not data_shape:
                raise self.ImgProcessorError('data_shape must be provided '
                                             'when requesting FlashProcessor '
                                             'on the gpu'
                                             .format(target))
            a, b, offset = self.cam_params.data[:3]
            camcor_init(data_shape, a, b, offset)
        super(FlashProcessor, self).__init__()

    @interleaved
    def process(self, data):
        """ interleaves and corrects 4D data, or just correct 3D """
        if self.target == 'cpu':
            a, b, offset = self.cam_params.data[:3]
            return calc_correction(data, a, b, offset)
        else:
            return camcor(data)

    @classmethod
    def from_llsdir(cls, llsdir, *args, **kwargs):
        data_roi = llsdir.settings.camera.roi
        data_shape = llsdir.data.shape[-4:]
        return cls(cam_params, data_roi, target=target, data_shape=data_shape, **kwargs)


class SelectiveMedianProcessor(ImgProcessor):
    """correct bad pixels on sCMOS camera.    """

    data_specific = ('background')

    def __init__(self, background=0, median_range=3, with_mean=False):
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

    def __init__(self, divisor, projector=lambda x: np.mean(x, 0)):
        assert isinstance(divisor, np.ndarray)
        # only accept 2D or 3D inputs (single channel, optional Z stack)
        if not 1 < divisor.ndim < 4:
            raise self.ImgProcessorError(
                'Divisor Image must have 2 or 3 dimensions')
        # convert all images to 2D with provided projector func
        if divisor.ndim == 3:
            divisor = projector(divisor)
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

    data_specific = ('first_timepoint')

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

    def __init__(self, z=(0, 0), y=(0, 0), x=(0, 0)):
        self.slices = (np.s_[z[0]:-z[1]] if z[1] else np.s_[z[0]:],
                       np.s_[y[0]:-y[1]] if y[1] else np.s_[y[0]:],
                       np.s_[x[0]:-x[1]] if x[1] else np.s_[x[0]:])

    def process(self, data):
        if data.ndim > len(self.slices):
            self.slices = (np.s_[:],) * (data.ndim - 3) + self.slices
        return data[tuple(self.slices)]


class CUDADeconProcessor(ImgProcessor):
    """  Perform richardson lucy deconvolution on the GPU

    NOTE: needs to be called within a RLContext()
    """

    channel_specific = ('background',)
    requires_context = (RLContext,)
    data_specific = ('background')

    def __init__(self, background=80, n_iters=10, shift=0,
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

    channel_specific = ('tform',)

    def __init__(self, tform):
        pass

    def process(self, data):
        return data


class RotateYProcessor(AffineProcessor):
    """ Subclass of affine processor, for simplified rotation of the image in Y """

    channel_specific = None

    def __init__(self, angle):
        pass

    def process(self, data):
        return data

    @classmethod
    def from_llsdir(cls, llsdir, *args, **kwargs):
        return cls(*args, **kwargs)


class TiffWriter(ImgProcessor):
    """ Subclass of affine processor, for simplified rotation of the image in Y """

    def __init__(self, outdir, frmt='{t:04d}.tif'):
        self.outdir = outdir
        self.format = frmt

    def process(self, data, nt):
        outpath = os.path.join(self.outdir, self.format.format(t=nt))
        imsave(data, outpath, dx=1, dz=1, dt=1, unit='micron')
        return data
