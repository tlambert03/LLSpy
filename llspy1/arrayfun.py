from __future__ import print_function, division
from .libcudawrapper import deskewGPU as deskew
from .util import imread

import numpy as np
from scipy.ndimage.filters import gaussian_filter
from scipy.stats import mode


def threshold_li(image):
    """Return threshold value based on adaptation of Li's Minimum Cross Entropy method.

    From skimage.filters.threshold_li
    Parameters
    ----------
    image : (N, M) ndarray
        Input image.
    Returns
    -------
    threshold : float
        Upper threshold value. All pixels with an intensity higher than
        this value are assumed to be foreground.
    References
    ----------
    .. [1] Li C.H. and Lee C.K. (1993) "Minimum Cross Entropy Thresholding"
           Pattern Recognition, 26(4): 617-625
           DOI:10.1016/0031-3203(93)90115-D
    .. [2] Li C.H. and Tam P.K.S. (1998) "An Iterative Algorithm for Minimum
           Cross Entropy Thresholding" Pattern Recognition Letters, 18(8): 771-776
           DOI:10.1016/S0167-8655(98)00057-9
    .. [3] Sezgin M. and Sankur B. (2004) "Survey over Image Thresholding
           Techniques and Quantitative Performance Evaluation" Journal of
           Electronic Imaging, 13(1): 146-165
           DOI:10.1117/1.1631315
    .. [4] ImageJ AutoThresholder code, http://fiji.sc/wiki/index.php/Auto_Threshold
    """
    # Make sure image has more than one value
    if np.all(image == image.flat[0]):
        raise ValueError("threshold_li is expected to work with images "
                         "having more than one value. The input image seems "
                         "to have just one value {0}.".format(image.flat[0]))

    # Copy to ensure input image is not modified
    image = image.copy()
    # Requires positive image (because of log(mean))
    immin = np.min(image)
    image -= immin
    imrange = np.max(image)
    tolerance = 0.5 * imrange / 256

    # Calculate the mean gray-level
    mean = np.mean(image)

    # Initial estimate
    new_thresh = mean
    old_thresh = new_thresh + 2 * tolerance

    # Stop the iterations when the difference between the
    # new and old threshold values is less than the tolerance
    while abs(new_thresh - old_thresh) > tolerance:
        old_thresh = new_thresh
        threshold = old_thresh + tolerance   # range
        # Calculate the means of background and object pixels
        mean_back = image[image <= threshold].mean()
        mean_obj = image[image > threshold].mean()

        temp = (mean_back - mean_obj) / (np.log(mean_back) - np.log(mean_obj))

        if temp < 0:
            new_thresh = temp - tolerance
        else:
            new_thresh = temp + tolerance

    return threshold + immin


def trimedges(im, trim, ninterleaved=1):
    nz, ny, nx = im.shape
    im = im[
        trim[0][0] * ninterleaved: nz - trim[0][1] * ninterleaved,
        trim[1][0]: ny - trim[1][1],
        trim[2][0]: nx - trim[2][1]]
    return im


def cropX(im, width=0, shift=0):
    nz, ny, nx = im.shape
    if width == 0:
        width = nx - np.abs(shift)
    middle = np.ceil(nx/2 + shift)
    left = int(np.maximum(np.ceil(middle - width/2), 0))
    right = int(np.minimum(np.ceil(middle + width/2), nx))
    im = im[:, :, left:right]
    return im


def interleave(data):
    """ interleave timepoints into the channel axis

    for instance, convert an array of shape (10,3,512,512) to
    one with shape (30, 512, 512) where the first axis is alternating
    between three channels
    """
    if data.ndim == 4:
        ny, nx = data.shape[-2:]
        data = data.transpose(1, 0, 2, 3).reshape((-1, ny, nx))
    return data


def deinterleave(data, nc):
    """ undo the interleave function"""
    return np.stack([data[i::nc] for i in range(nc)]) if nc > 1 else data


def imcontentbounds(im, sigma=2):
    """Get image content bounding box via gaussian filter and threshold."""
    # get rid of the first two planes in case of high dark noise
    if im.ndim == 3:
        im = np.squeeze(np.max(im[2:], 0))
    im = im.astype(np.float)
    fullwidth = im.shape[-1]
    # from scipy.ndimage.filters import median_filter
    # mm = median_filter(b.astype(float),3)
    mm = im
    imgaus = gaussian_filter(mm, sigma)
    mask = imgaus > threshold_li(imgaus)
    linesum = np.sum(mask, 0)
    abovethresh = np.where(linesum > 0)[0]
    right = abovethresh[-1]
    left = abovethresh[0]
    return [left, right, fullwidth]


def feature_width(E, background=None, pad=50, t=0):
    """automated detection of post-deskew image content width.

    the width can be used during deskewing to crop the final image to
    reasonable bounds
    """

    # first deskew just first and last timepoints of each channel
    P = E.parameters
    # first and last timepoint
    maxT = max(P.tset)
    minT = min(P.tset)
    raw_stacks = [imread(f) for f in E.get_files(t=(minT, maxT))]
    raw_stacks = [sub_background(f, background) for f in raw_stacks]
    if P.samplescan:
        deskewed_stacks = [deskew(s, P.dz, P.dx, P.angle) for s in raw_stacks]
    else:
        deskewed_stacks = raw_stacks

    # then get minimum bounding box of features
    bounds = np.array([imcontentbounds(d) for d in deskewed_stacks])
    rightbound = np.max(bounds[:, 1])
    leftbound = np.min(bounds[:, 0])
    deskewedWidth = bounds[0, 2]
    width = int(rightbound - leftbound + pad)
    middle = np.floor((rightbound + leftbound) / 2)
    offset = int(np.floor(middle - (deskewedWidth / 2)))

    return {'width': width, 'offset': offset, 'deskewed_nx': deskewedWidth}


def detect_background(im):
    """ get mode of the first plane """
    if im.ndim == 4:
        im = im[0][2]
    if im.ndim == 3:
        im = im[1]  # pick the third plane... avoid noise in first plane on lattice
    return mode(im.flatten())[0][0]


def sub_background(im, background=None):
    """ subtract provided background or autodetct as mode of the first plane"""
    if background is None:
        background = detect_background(im)
    out = im.astype(np.float) - background
    out[out < 0] = 0
    return out


def deskew_gputools(rawdata, dz=0.5, dx=0.102, angle=31.5, filler=0):
    try:
        import gputools
    except ImportError:
        # sys.stdout = sys.__stdout__
        print("could not import gputools")

    deskewFactor = np.cos(angle * np.pi / 180) * dz / dx
    T = np.array([[1, 0, deskewFactor, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]])
    (nz, ny, nx) = rawdata.shape
    # Francois' method:
    # nxOut = math.ceil((nz - 1) * deskewFactor) + nx
    nxOut = np.int(np.floor((nz - 1) * dz *
            abs(np.cos(angle * np.pi / 180)) / dx) + nx)
    # +1 to pad left side with 1 column of filler pixels
    # otherwise, edge pixel values are smeared across the image
    paddedData = np.ones((nz, ny, nxOut), rawdata.dtype) * filler
    paddedData[..., :nx] = rawdata
    out = gputools.transforms.affine(
        paddedData, T, interpolation="linear", mode="wrap")
    return out  # return is np.float32
