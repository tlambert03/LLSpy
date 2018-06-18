from abc import ABC, abstractmethod
import logging
import os
import numpy as np
from enum import Enum
from llspy.libcudawrapper import (RL_interface, camcor, camcor_init,
                                  RLContext, deskewGPU, rotateGPU)
from llspy.camera import CameraParameters, calc_correction, selectiveMedianFilter
from llspy.arrayfun import interleave, deinterleave, sub_background, detect_background
from llspy.util import imread
from llspy import LLSdir
from llspy.otf import choose_otf

logger = logging.getLogger()


def interleaved(func):
    """ method decorator to interleave/deinterlave data before/after processing"""
    def wrapper(self, data, meta):
        nc = len(meta['c'])
        data, meta = func(self, interleave(data), meta)
        return deinterleave(data, nc), meta
    return wrapper


def without_background(func):
    """ method decorator to interleave/deinterlave data before/after processing"""
    def wrapper(self, data, meta):
        if not meta.get('has_background', True):
            self.background = 0
        nc = len(meta['c'])
        _background = []
        if nc > 1:
            for c in range(nc):
                b = detect_background(data[c])
                _background.append(b)
                data[c] = sub_background(data[c], b)
        else:
            b = detect_background(data)
            _background.append(b)
            data = sub_background(data, b)
        data, meta = func(self, data, meta)
        meta['has_background'] = False
        meta['background_removed'] = _background
        return data, meta
    return wrapper


def for_channel(inplace=True):
    # set inplace to False if the processed data is not the same shape
    # as the input data
    def real_decorator(func):
        def wrapper(self, data, meta):
            if len(meta['c']) > 1:
                if inplace:
                    for c in range(len(meta['c'])):
                        data[c], meta = func(self, data[c], meta)
                else:
                    for c in range(len(meta['c'])):
                        _data, meta = func(self, data[c], meta)
                        if c == 0:
                            out = np.empty((len(meta['c']),) + _data.shape,
                                           dtype=data.dtype)
                        out[c] = _data
                    data = out
            else:
                data, meta = func(self, data, meta)
            return data, meta
        return wrapper
    return real_decorator


class BitDepth(Enum):
    uint16 = '16-bit'
    float32 = '32-bit'


class ImgProcessor(ABC):
    """ Image Processor abstract class.

    All subclasses of ImgProcessor must override the process() method, which
    should accept a single numpy array and return a single processed array.
    channel_specific class attributes specify which of the parameters must
    be specified for each channel in the dataset
    """

    def __init__(self):
        super().__init__()

    def __call__(self, data, meta, **kwargs):
        assert isinstance(data, np.ndarray), 'Input to ImgProcessor must be np.ndarray'
        logger.debug('{} called on data with shape {}'
                     .format(self, data.shape))
        data = self.process(data, meta, **kwargs)
        if kwargs.get('callback', False):
            kwargs.get('callback')(data, **kwargs)
        return data

    @classmethod
    def name(cls):
        """ look for attribute called verbose_name, otherwise return class name"""
        return getattr(cls, 'verbose_name', cls.__name__)

    @classmethod
    def verb(cls):
        """ look for attribute called verbose_name, otherwise return class name"""
        return getattr(cls, 'processing_verb', cls.name())

    @abstractmethod
    def process(self, data, meta):
        """ All child classes must override this method.

        Args:
            data (np.ndarray): Volume of data to be processed.
                should be able to handle data of arbitrary dimensions,
                data *should* be an info array that has an "axes"
                attribute, declaring the order of axes (usually CZYX).
            meta (dict): Information about the data.  This dict is
                initialized by the `ProcessPlan` instance that executes
                the image processor, but can be modified during processing
                by each ImgProcessor in the chain.
                API is still unset, but current values will be:
                    axes (str): name of axes for each dimension
                    t (int, list): timepoint(s) in the current data volume
                    c (list): channel(s) in the current data volume
                    w (list): wavelength(s) in the current data volume
                        where len(w) must == len(c)
                    params (dict): full llsdir.params dict
                    has_background (bool): whether background has been subbed
        Returns:
            tuple: (processed `data`, modified `meta`
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
    processing_verb = 'Fixing Flash Artifact'

    class Target(Enum):
        CPU = 'CPU'
        GPU = 'GPU'

    def __init__(self, data_roi, param_file='', perform_on=Target.CPU, data_shape=None):
        if not isinstance(perform_on, self.Target):
            try:
                perform_on = self.Target(perform_on.upper())
            except ValueError:
                raise ValueError('"{}" is not a valid FlashProcessor target'
                                 .format(perform_on))
        if not isinstance(param_file, CameraParameters):
            try:
                param_file = CameraParameters(param_file)
            except Exception as e:
                raise self.ImgProcessorError('Error creating cam_params: {}'
                                             .format(e))
        # may raise an error... should catch here?
        try:
            self.cam_params = param_file.get_subroi(data_roi)
        except Exception as e:
            raise self.ImgProcessorError('Error creating cam_params: {}'
                                         .format(e))
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
    def process(self, data, meta):
        """ interleaves and corrects 4D data, or just correct 3D """
        if self.target == self.Target.CPU:
            a, b, offset = self.cam_params.data[:3]
            data = calc_correction(data, a, b, offset)
        else:
            data = camcor(data)
        meta['has_background'] = False
        return data, meta

    @classmethod
    def from_llsdir(cls, llsdir, **kwargs):
        kwargs.pop('data_roi')
        data_roi = llsdir.params.get('roi')
        if data_roi is None:
            raise cls.ImgProcessorError('Failed to extract camera ROI from settings.')
        kwargs['data_shape'] = llsdir.data.shape[-4:]
        return cls(data_roi, **kwargs)


class SelectiveMedianProcessor(ImgProcessor):
    """correct bad pixels on sCMOS camera.

    guidoc: selective median filter as in Amat 2015
    """

    verbose_name = 'Selective Median Filter'
    processing_verb = 'Performing Median Filter'
    gui_layout = {
        'background': (0, 1),
        'median_range': (0, 0),
        'with_mean': (0, 2),
    }
    valid_range = {
        'background': (0, 1000),
        'median_range': (1, 9),
    }

    def __init__(self, background=0, median_range=3, with_mean=True):
        super(SelectiveMedianProcessor, self).__init__()
        self.background = background
        self.median_range = median_range
        self.with_mean = with_mean

    def process(self, data, meta):
        nc = len(meta['c'])
        ny, nx = data.shape[-2:]
        if nc > 1:
            data = data.reshape(-1, ny, nx)
        data, _ = selectiveMedianFilter(data, self.background,
                                        self.median_range, self.with_mean)
        if nc > 1:
            data = data.reshape(nc, -1, ny, nx)
        return data, meta


class DivisionProcessor(ImgProcessor):
    """ Divides and image by another image, e.g. for flatfield correction

    guidoc: divisor can be tiff file or LLSdir, with flatfield image
    """

    class Projector(Enum):
        mean = 'mean'
        max = 'max'

    verbose_name = "Flatfield Correction"
    projectors = {
        'mean': lambda x: np.mean(x, 0),
        'max': lambda x: np.max(x, 0),
    }

    def __init__(self, divisor_path='', offset=90, projection=Projector.mean):
        if isinstance(divisor_path, str):
            try:
                if os.path.isdir(divisor_path):
                    _d = LLSdir(divisor_path)
                    _d = _d.data.asarray(t=0)
                elif os.path.isfile(divisor_path):
                    _d = imread(divisor_path)
            except Exception:
                raise self.ImgProcessorError(
                    '"Divisor" argument not recognized as file or LLS directory')
        if not isinstance(divisor_path, np.ndarray):
            raise self.ImgProcessorError(
                '"Divisor" argument not recognized as file or LLS directory')
        # only accept 2D or 3D inputs (single channel, optional Z stack)
        if not 1 < divisor_path.ndim < 4:
            raise self.ImgProcessorError(
                'Divisor Image must have 2 or 3 dimensions')
        # convert all images to 2D with provided projector func
        if divisor_path.ndim == 3:
            divisor = self.projectors[projection.name](divisor_path)
        self.divisor = (divisor - offset).astype(np.float32)
        # preserve intensity in original image
        self.divisor /= self.divisor.mean()

    @without_background
    def process(self, data, meta):
        if (isinstance(self.divisor, np.ndarray) and
                (data.shape[-2:] != self.divisor.shape)):
            raise self.ImgProcessorError(
                'Cannot divide data with shape {} by divisor with shape {}'
                .format(data.shape, self.divisor.shape))
        data = np.divide(data, self.divisor)
        return data, meta


class BleachCorrectionProcessor(ImgProcessor):
    """ Divides and image by another image, e.g. for flatfield correction """

    verbose_name = "Bleach Correction"
    processing_verb = 'Correcting Photobleaching'

    def __init__(self, first_timepoint):
        # convert first_timepoint into divisor
        # get mean above background
        zyx = range(first_timepoint.ndim)[-3:]
        self.first_mean = first_timepoint.mean(axis=tuple(zyx))

    def process(self, data, meta):
        dtype = data.dtype
        if data.ndim <= 3:
            scaler = self.first_mean / data.mean()
        elif data.ndim == 4:
            mean = data.mean(axis=(1, 2, 3))
            scaler = (self.first_mean / mean).reshape(data.shape[0], 1, 1, 1)
        else:
            raise self.ImgProcessorError('Bleach correction can only accept 3 or 4D')
        data = np.multiply(data, scaler).astype(dtype)
        return data, meta

    @classmethod
    def from_llsdir(cls, llsdir, **kwargs):
        return cls(llsdir.data.asarray(t=0))


class TrimProcessor(ImgProcessor):
    """ trim pixels off of the edge each dimension in XYZ """

    verbose_name = "Trim Edges"
    processing_verb = 'Trimming Edges'
    gui_layout = {
        'trim_x': (0, 0),
        'trim_y': (1, 0),
        'trim_z': (2, 0)
    }

    def __init__(self, trim_z=(0, 0), trim_y=(0, 0), trim_x=(0, 0)):
        self.slices = (np.s_[trim_z[0]:-trim_z[1]] if trim_z[1] else np.s_[trim_z[0]:],
                       np.s_[trim_y[0]:-trim_y[1]] if trim_y[1] else np.s_[trim_y[0]:],
                       np.s_[trim_x[0]:-trim_x[1]] if trim_x[1] else np.s_[trim_x[0]:])

    def process(self, data, meta):
        if data.ndim > len(self.slices):
            self.slices = (np.s_[:],) * (data.ndim - 3) + self.slices
        data = data[tuple(self.slices)]
        return data, meta


class CUDADeconProcessor(ImgProcessor):
    """  Perform richardson lucy deconvolution on the GPU

    NOTE: needs to be called within a RLContext()
    """

    verbose_name = 'Deconvolution/Deskewing'
    processing_verb = 'Deconvolving'
    valid_range = {
        'background': (0, 1000),
        'n_iters': (1, 20),
    }

    # gui_layout = {
    #     'otf_dir': (0, 0),
    #     'background': (1, 1),
    #     'n_iters': (1, 0),
    #     'shift': (1, 2),
    #     'save_deskewed': (2, 0),
    #     'rescale': (2, 1),
    # }

    def __init__(self, background=100, n_iters=10, shift=0, otf_dir='',
                 bit_depth=BitDepth.uint16, save_deskewed=False):
        if not os.path.isdir(otf_dir):
            raise self.ImgProcessorError(
                '"otf_dir" argument not an existing directory')
        self.otf_dir = otf_dir
        self.background = background
        self.n_iters = n_iters
        self.width = 0
        self.shift = shift
        self.save_deskewed = save_deskewed
        self.rescale = False
        if bit_depth in (BitDepth.uint16, '16'):
            self.dtype = np.uint16
        elif bit_depth in (BitDepth.float32, '32'):
            self.dtype = np.float32

    def _decon(self, data, outshape):
        nz, ny, nx = data.shape
        # must be 16 bit going in
        if not np.issubdtype(data.dtype, np.uint16):
            data = data.astype(np.uint16)
        if not data.flags['C_CONTIGUOUS']:
            data = np.ascontiguousarray(data)

        decon_result = np.empty(outshape, dtype=np.float32)
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

    def _process_channel(self, data, wave, meta):
        otf = choose_otf(wave, self.otf_dir, meta['params'].date,
                         meta['params'].mask)

        # TODO: expose shift and width parameters
        with RLContext(data.shape, otf, meta['params'].dz,
                       deskew=meta['params'].deskew,
                       width=self.width) as ctx:
            return self._decon(data, ctx.out_shape)

    @without_background
    def process(self, data, meta):
        if len(meta['c']) > 1:
            for c in range(len(meta['c'])):
                wave = meta['w'][c]
                if c == 0:
                    d = self._process_channel(data[c], wave, meta)
                    shp = (len(meta['c']),) + d.shape
                    newdata = np.empty(shp)
                    newdata[0] = d
                else:
                    newdata[c] = self._process_channel(data[c], wave, meta)
        else:
            newdata = self._decon(data, meta.get('out_shape'))
        return newdata.astype(self.dtype), meta

    @classmethod
    def from_llsdir(cls, llsdir, **kwargs):
        if not any(llsdir.params.wavelengths):
            raise cls.ImgProcessorError('Cannot perform Decon on a dataset '
                                        'with unknown wavelengths')
        return cls(**kwargs)


class AffineProcessor(ImgProcessor):
    """ Perform Affine Transformation, e.g. for channel registration """

    def __init__(self, reg_file=''):
        if not os.path.isfile(reg_file):
            raise self.ImgProcessorError('reg_file cannot be blank')

    def process(self, data, meta):
        return data, meta


class DeskewProcessor(ImgProcessor):
    """ Deskewing only, no deconvolution """
    verbose_name = 'Deskew Only'
    valid_range = {
        'width': (0, 2048),
        'shift': (-1024, 1024),
    }

    def __init__(self, width=0, shift=0):
        super(DeskewProcessor, self).__init__()
        self.width = width
        self.shift = shift

    @for_channel(False)
    def process(self, data, meta):
        dtype = data.dtype
        _data = deskewGPU(data, meta['params'].dz,
                          meta['params'].dx, meta['params'].deskew,
                          self.width, self.shift)
        return _data.astype(dtype), meta


class RotateYProcessor(AffineProcessor):
    """ Subclass of affine processor, for simplified rotation of the image in Y """

    verbose_name = "Rotate to Coverslip"

    def __init__(self, angle):
        pass

    @for_channel(False)
    def process(self, data, meta):
        d = rotateGPU(data, angle=32.5, xzRatio=0.4253, reverse=False)
        return d, meta

    @classmethod
    def from_llsdir(cls, llsdir, *args, **kwargs):
        return cls(*args, **kwargs)
