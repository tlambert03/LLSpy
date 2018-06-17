from . import libcudawrapper as libcu
from .util import imread
from . import arrayfun
from scipy.ndimage.filters import median_filter

import os
import re
import warnings
import numpy as np
from numba import jit
import math
import logging

logger = logging.getLogger(__name__)


# #THIS ONE WORKS BEST SO FAR
@jit(nopython=True, nogil=True)
def calc_correction(stack, a, b, offset):
    res = np.empty_like(stack)
    for i in range(stack.shape[0]):
        for j in range(stack.shape[1]):
            for k in range(stack.shape[2]):
                if i == 0:
                    d = stack[i, j, k] - offset[j, k]
                    res[i, j, k] = d if d > 0 else 0
                else:
                    cor = (1 - math.exp(-b[j, k] * (stack[i - 1, j, k] -
                                        offset[j, k]))) * a[j, k]
                    d = stack[i, j, k] - offset[j, k] - 0.88 * cor
                    res[i, j, k] = d if d > 0 else 0
    return res


def selectiveMedianFilter(stack, background, median_range=3, with_mean=False):
    """correct bad pixels on sCMOS camera.
    based on MATLAB code by Philipp J. Keller,
    HHMI/Janelia Research Campus, 2011-2014

    """
    from llspy.gpumedfilt import gpu_med_filt

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        devProj = np.std(stack, 0, ddof=1)
        devProjMedFiltered = gpu_med_filt(devProj)
        # devProjMedFiltered = median_filter(devProj, median_range, mode='constant')
        deviationDistances = np.abs(devProj - devProjMedFiltered)
        deviationDistances[deviationDistances == np.inf] = 0
        deviationThreshold = determineThreshold(sorted(deviationDistances.flatten()))

        deviationMatrix = deviationDistances > deviationThreshold

        if with_mean:
            meanProj = np.mean(stack, 0) - background
            meanProjMedFiltered = gpu_med_filt(meanProj)
            # meanProjMedFiltered = median_filter(meanProj, median_range)
            meanDistances = np.abs(meanProj - meanProjMedFiltered / meanProjMedFiltered)
            meanDistances[meanDistances == np.inf] = 0
            meanThreshold = determineThreshold(sorted(meanDistances.flatten()))

            meanMatrix = meanDistances > meanThreshold

            pixelMatrix = deviationMatrix | meanMatrix
            pixelCorrection = [deviationDistances, deviationThreshold,
                               meanDistances, meanThreshold]
        else:
            pixelMatrix = deviationMatrix
            pixelCorrection = [deviationDistances, deviationThreshold]

        pixpercent = 100 * np.sum(
            pixelMatrix.flatten()) / float(len(pixelMatrix.flatten()))
        logger.info('Bad pixels detected: {} ({:0.2f}%)'.format(
            np.sum(pixelMatrix.flatten()), pixpercent))

        dt = stack.dtype
        out = np.zeros(stack.shape, dt)
        # apply pixelMatrix to correct insensitive pixels
        for z in range(stack.shape[0]):
            frame = np.asarray(stack[z], 'Float32')
            filteredFrame = gpu_med_filt(frame)
            # filteredFrame = median_filter(frame, median_range)
            frame[pixelMatrix == 1] = filteredFrame[pixelMatrix == 1]
            out[z] = np.asarray(frame, dt)

        return out, pixelCorrection


def determineThreshold(array, maxSamples=50000):
    array = np.array(array)
    elements = len(array)

    if elements > maxSamples:  # subsample
        step = round(elements / maxSamples)
        array = array[0::step]
        elements = len(array)

    connectingline = np.linspace(array[0], array[-1], elements)
    distances = np.abs(array - connectingline)
    position = np.argmax(distances)

    threshold = array[position]
    if np.isnan(threshold):
        threshold = 0
    return threshold


class CameraROI(np.ndarray):
    """ Basic class to hold ROI of camera used during acquisition """

    def __new__(cls, input_array):
        obj = np.asarray(input_array, dtype=np.int16).view(cls)
        return obj

    def __contains__(self, subroi):
        # check whether the Parameter ROI contains the data ROI
        return not np.any((subroi - self) * np.array([-1, -1, 1, 1]) > 0)

    @property
    def left(self):
        return self[0]

    @property
    def top(self):
        return self[1]

    @property
    def right(self):
        return self[2]

    @property
    def bottom(self):
        return self[3]

    @property
    def width(self):
        return abs(self.right - self.left) + 1

    @property
    def height(self):
        return abs(self.bottom - self.top) + 1

    def __repr__(self):
        l, t, r, b = self
        return 'CameraROI([%d, %d, %d, %d])' % (l, t, r, b)

    def __str__(self):
        l, t, r, b = self
        return '<CameraROI left:%d, top:%d, right:%d, bot:%d>' % (l, t, r, b)


def seemsValidCamParams(path):
    try:
        data = imread(path)
        if not data.ndim == 3:
            return False
        if not data.shape[0] >= 3:
            return False
        # third plane should be a dark image, usually offset around 100
        if not (50 < data[2].mean() < 250):
            return False
        # second plane is that rate of association, usually very low
        if data[1].mean() > 1:
            return False
        return True
    except Exception:
        return False


class CameraParameters(object):
    """Class to store parameters for camera correction

    Filename: path to tif file that stores the camera correction parameters,
        first plane = param A
        second plane = param B
        third plane = dark image (offset map)
        #TODO: fourth plane = variance map
    """

    def __init__(self, path=None, data=None, roi=None):
        if data is None and path is None:
            raise ValueError('Must provide either filename or data array')
        if data is not None:
            self.data = data.astype(np.float32)
            self.path = path
        else:
            if not os.path.isfile(path):
                raise IOError("No such file: {}".format(path))
            self.path = path
            roi = re.search(r'roi(\d+)-(\d+)-(\d+)-(\d+)', path)
            if roi:
                roi = [int(r) for r in roi.groups()]
            # TODO: ignore warnings from tifffile
            self.data = imread(path).astype(np.float64)

        if roi is None or not len(roi):
            raise ValueError("Could not parse CamParams ROI from from filename. "
                             "If using a FlashParam file, please ensure that "
                             "'roi[left]-[top]-[right]-[bottom]' is in "
                             "the FlashParam filename.")
        self.roi = CameraROI(roi)
        _shape = self.data.shape
        if not _shape[0] >= 3:
            raise ValueError("Camera parameter file must have at least "
                             "3 planes. {} has only {}"
                             .format(path, _shape[0]))
        if not self.roi.width == _shape[1]:
            raise ValueError("Tiff file provided does not have the same width "
                             "({}) as the proivded roi ({})"
                             .format(_shape[1], self.roi.width))
        if not self.roi.height == _shape[2]:
            raise ValueError("Tiff file provided does not have the same height "
                             "({}) as the proivded roi ({})"
                             .format(_shape[2], self.roi.height))
        self.a, self.b, self.offset = self.data[:3]

    def __repr__(self):
        return 'CameraParameters({})'.format(os.path.basename(self.path))

    def get_subroi(self, subroi):
        if not isinstance(subroi, CameraROI):
            if isinstance(subroi, (tuple, list)) and len(subroi) == 4:
                subroi = CameraROI(subroi)
            else:
                raise ValueError(
                    'subroi argument must be a CameraROI instance or 4-tuple')
        # make sure the Parameter ROI contains the data ROI
        if subroi not in self.roi:
            raise ValueError(
                'ROI for correction file does not encompass data ROI')

        diffroi = subroi - self.roi
        # either Labview or the camera is doing
        # something weird with the ROI... or I am calculating the required ROI
        # alignment wrong... this is the hack I empirically came up with
        vshift = self.roi.left + self.roi.right - subroi.left - subroi.right
        # it appears that the camera never shifts the roi horizontally...
        hshift = 0
        subP = self.data[:, diffroi[0] + vshift:diffroi[2] + vshift,
                         diffroi[1] + hshift:diffroi[3] + hshift]
        return CameraParameters(data=subP, roi=subroi, path=self.path)

    def init_CUDAcamcor(self, shape):
        libcu.camcor_init(shape, self.data[:3])

    def correct_stacks(self, stacks, medianFilter=False,
                       trim=((0, 0), (0, 0), (0, 0)),
                       flashCorrectTarget='cpu', dampening=0.88):
        """interleave stacks and apply correction for "sticky" Flash pixels.

        Expects a list of 3D np.ndarrays ordered in order of acquisition:
            e.g. [stack_ch0, stack_ch1, stack_ch2, ...]

        Returns a corrected list of np.ndarrays of the same
        shape and length as the input ... unless trimedges is used
        trim edges is a tuple of 2tuples that controls how many pixels are trimmed
        from the ((1stplane,lastplane),(top,bottom), (left, right))
        by default: trim first Z plane and single pixel from X-edges
        """
        if isinstance(stacks, list):
            # for backwards compatibility for now
            if not len(stacks):
                raise ValueError('Empty list of stacks received: {}'
                                 .format(stacks))
            if len({S.shape for S in stacks}) > 1:
                raise ValueError('All stacks in list must have the same shape')
            if not all([isinstance(S, np.ndarray) for S in stacks]):
                raise ValueError('All stacks in list must be of type: np.ndarray')
            # interleave stacks into single 3D so that they are in the order:
            #  ch0_XYt0, ch1_XYt0, chN_XYt0, ch0_XYt1, ch1_XYt1, ...
            ny, nx = stacks[0].shape[-2:]
            numStacks = len(stacks)
            typ = stacks[0].dtype
            interleaved = np.stack(stacks, 1).reshape((-1, ny, nx))
        elif isinstance(stacks, np.ndarray):
            # if it's already a numpy array assume it's CZYX
            if stacks.ndim == 4:
                ny, nx = stacks.shape[-2:]
                interleaved = stacks.transpose(1, 0, 2, 3).reshape((-1, ny, nx))
            elif stacks.ndim == 3:
                # assume single channel, which doesn't need to be interleaved
                interleaved = stacks

        if flashCorrectTarget == 'cuda' or flashCorrectTarget == 'gpu':
            # this must be called before! but better to do it outside of this function
            # libcu.camcor_init(interleaved.shape, self.a, self.b, self.offset)
            interleaved = libcu.camcor(interleaved)
        else:
            if flashCorrectTarget == 'cpu':
                # JIT VERSION
                interleaved = calc_correction(interleaved, self.a, self.b, self.offset)
            elif flashCorrectTarget == 'numpy':
                # NUMPY VERSION
                interleaved = np.subtract(interleaved, self.offset)
                correction = self.a * (1 - np.exp(-self.b * interleaved[:-1, :, :]))
                interleaved[1:, :, :] -= dampening * correction
                interleaved[interleaved < 0] = 0
            else:
                raise ValueError(
                    'unrecognized value for flashCorrectTarget '
                    'parameter: {}'.format(flashCorrectTarget))

            # interleaved = np.subtract(interleaved, self.offset)
            # correction = self.a * (1 - np.exp(-self.b * interleaved[:-1, :, :]))
            # interleaved[1:, :, :] -= dampening * correction
            # interleaved[interleaved < 0] = 0

        # do Philpp Keller medianFilter Filter
        if medianFilter:
            interleaved, pixCorrection = selectiveMedianFilter(interleaved, 0)

        # sometimes the columns on the very edge are brighter than the rest
        # (particularly if an object is truncated and there's more content
        # just off to the side of the camera ROI)
        # this will delete the edge columns
        if any([any(i) for i in trim]):
            interleaved = arrayfun.trimedges(interleaved, trim, numStacks)

        if not np.issubdtype(interleaved.dtype, typ):
            warnings.warn('CONVERTING')
            interleaved = interleaved.astype(typ)

        deinterleaved = [s for s in np.split(interleaved, interleaved.shape[0])]
        deinterleaved = [np.concatenate(deinterleaved[q::numStacks])
                         for q in range(numStacks)]

        return deinterleaved


if __name__ == '__main__':

    from llspy import llsdir
    from llspy import samples

    paramfile = samples.camparams  # path to the calibration file

    E = llsdir.LLSdir(samples.stickypix)  # special class for my data...
    # you'll need to work around this to generate a list of filenames you want to correct

    # get the master parameters TIF file and then crop it according to the
    # roi used for the raw data set... if raw data is the same as the calibration
    # you can use corrector = camparams
    camparams = CameraParameters(paramfile)
    corrector = camparams.get_subroi(CameraROI(E.settings.camera.roi))

    # this is the list you need to make
    stacks = [imread(str(t)) for t in E.tiff.raw if 'stack0000' in str(t)]
    niters = 5

    import time
    start = time.time()
    for _ in range(niters):
        d1 = corrector.correct_stacks(stacks, medianFilter=False, flashCorrectTarget='cpu')
    end = time.time()
    print("JitCPU Time: " + str((end - start) / niters))

    start = time.time()
    for _ in range(niters):
        d2 = corrector.correct_stacks(stacks, medianFilter=False, flashCorrectTarget='numpy')
    end = time.time()
    print("NumpyCPU Time: " + str((end - start) / niters))
    print("Equal? = " + str(np.mean(d1[0] - d2[0])))
    print("Equal? = " + str(np.mean(d1[1] - d2[1])))
    print("Equal? = " + str(np.mean(d1[2] - d2[2])))

    start = time.time()
    corrector.init_CUDAcamcor(stacks[0].shape * np.array([len(stacks), 1, 1]))
    for _ in range(niters):
        d3 = corrector.correct_stacks(stacks, medianFilter=False, flashCorrectTarget='cuda')
    end = time.time()
    print("CUDA Time: " + str((end - start) / niters))
    print("Equal? = " + str(np.mean(d3[0] - d1[0])))
    print("Equal? = " + str(np.mean(d3[1] - d1[1])))
    print("Equal? = " + str(np.mean(d3[2] - d1[2])))
