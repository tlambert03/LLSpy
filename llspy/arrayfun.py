from __future__ import print_function, division
from .libcudawrapper import deskewGPU as deskew
from .util import imread

import numpy as np
from skimage.filters import gaussian, threshold_li
from scipy.stats import mode


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
    imgaus = gaussian(mm, sigma=sigma)
    mask = imgaus > threshold_li(imgaus)
    linesum = np.sum(mask, 0)
    abovethresh = np.where(linesum > 0)[0]
    right = abovethresh[-1]
    left = abovethresh[0]
    return [left, right, fullwidth]


def feature_width(E, background=None, pad=50):
    """automated detection of post-deskew image content width.

    the width can be used during deskewing to crop the final image to
    reasonable bounds
    """

    # first deskew just first and last timepoints of each channel
    P = E.parameters
    # first and last timepoint
    raw_stacks = [imread(f) for f in E.get_files(t=(0, P.nt - 1))]
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


def deskew_gputools(rawdata, dz=0.3, dx=0.105, angle=31.5, filler=0):
    try:
        import sys
        # silence gputools error if config file is missing
        # sys.stdout = open(os.devnull, "w")
        # the PyPI gputools repo doesn't yet have the required affine params
        sys.path.insert(0, '/Users/talley/Dropbox (HMS)/Python/repos/gputools/')
        import gputools
        # sys.stdout = sys.__stdout__
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
