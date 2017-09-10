import numpy as np
import os
import glob
import tifffile as tf
import multiprocessing
from scipy.optimize import least_squares
from numba import jit
import warnings
from . import util
from . import llsdir


def get_channel_list(folder):
    """Generate list of all ch0 and ch1 tiffs in a given folder, with error checking

    sorting is important because the assumption made is that every plane in
    stack PRE (see below) came immediately before the corresponding plane in
    stack POST.
    """
    ch0list = sorted(glob.glob(os.path.join(folder, '*_ch0_*tif')))
    ch0list = [f for f in ch0list if 'dark' not in f]  # remove dark images
    ch1list = sorted(glob.glob(os.path.join(folder, '*_ch1_*tif')))
    ch1list = [f for f in ch1list if 'dark' not in f]  # remove dark images
    assert len(ch0list) == len(ch1list), 'The number of stacks in ch0 and ch1 must be the same'

    shapes = [tf.TiffFile(f).series[0].shape for f in (ch0list + ch1list)]
    assert len(set(shapes)) == 1, 'All stacks must have the same number of pixels and planes'

    return ch0list, ch1list


def combine_stacks(ch0, ch1, darkavg):
    """Read tifs into two large stacks ...

    #TODO: see if we do this sequentially to minimize the amount of RAM required
    """
    shp = list(tf.TiffFile(ch0[0]).series[0].shape)
    nZ = shp[0]
    shp[0] *= len(ch0)
    pre = np.zeros(shp, dtype=np.float)
    post = np.zeros(shp, dtype=np.float)
    for n in range(len(ch0)):
        pre[n*nZ:n*nZ+nZ, :, :] = tf.imread(ch0[n]).astype(np.float) - darkavg
        post[n*nZ:n*nZ+nZ, :, :] = tf.imread(ch1[n]).astype(np.float) - darkavg
    return pre, post


@jit(nopython=True, nogil=True)
def fun(p, x, y):
    ''' single phase exponential association curve '''
    return p[0] * (1 - np.exp(-p[1] * x)) - y


def fitstickypixel(xdata, ydata, i, j):
    ''' fit data to curve, return optimal parameters from function '''
    p0 = np.array([100, 0.0019])  # starting guess
    bounds = ([0, 0], [800, 0.01])  # min and max bounds
    res = least_squares(fun, p0, args=(xdata, ydata), bounds=bounds)
    return res.x, i, j


def splat_fit(args):
    # helper function to unwarp arguments to fitter
    return fitstickypixel(*args)


def parallel_fit(xdata, ydata, callback=None):
    ''' parallelize fitting and return 3D numpy array where...

    first plane = paramater a = plateau of exponential association
    second plane = parameter b = rate of exponential association
    '''
    pool = multiprocessing.Pool()
    M = xdata.shape[1]
    N = xdata.shape[2]
    imap_iter = pool.imap(splat_fit,
        ((xdata[:, i, j], ydata[:, i, j], i, j)
            for i in range(M) for j in range(N)), chunksize=8)

    out = np.zeros((2, M, N), dtype=np.float32)
    for i in imap_iter:
        out[:2, i[1], i[2]] = i[0]
        if callback is not None:
            callback(1)
        # print("result: {}, I: {}, J: {}".format(*i))
    return out


def process_dark_images(folder, callback=None):
    darklist = sorted(glob.glob(os.path.join(folder, '*dark*.tif')))

    shapes = np.zeros((len(darklist), 3))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i, d in enumerate(darklist):
            with tf.TiffFile(d) as t:
                shapes[i, :] = t.series[0].shape
                if callback is not None:
                    callback(1)

    if len(set(shapes[:, 1])) + len(set(shapes[:, 2])) > 2:
        raise ValueError("All images must have same XY shape")

    darkstack = np.zeros((int(shapes[:, 0].sum()), int(shapes[0, 1]),
                          int(shapes[0, 2])), dtype=np.uint16)

    plane = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for d in darklist:
            t = tf.imread(d)
            nz = t.shape[0]
            darkstack[plane:plane+nz, :, :] = t
            plane += nz
            if callback is not None:
                callback(1)

    # nZ = shp[0]
    # shp[0] *= len(darklist)
    # darkstack = tf.imread(darklist[0])
    # for n in range(1, len(darklist)):
    #   darkstack = np.vstack((darkstack, tf.imread(darklist[n])))

    print("\nCalculating offset map...")
    darkavg = darkstack.mean(0)
    print("Calculating noise map...")
    darkstd = darkstack.std(0)
    return darkavg, darkstd


def process_bright_images(folder, darkavg, darkstd, callback=None):

    ch0list, ch1list = get_channel_list(folder)
    pre, post = combine_stacks(ch0list, ch1list, darkavg)

    results = parallel_fit(pre, post, callback)
    results = np.vstack((results, darkavg[None, :, :], darkstd[None, :, :]))
    results = util.reorderstack(results, 'zyx').astype(np.float32)

    E = llsdir.LLSdir(folder, ditch_partial=False)
    outname = "FlashParam_sn{}_roi{}_date{}.tif".format(
        E.settings.camera.serial,
        "-".join([str(i) for i in E.settings.camera.roi]),
        E.date.strftime('%Y%m%d'))

    tf.imsave(os.path.join(folder, outname), results, imagej=True,
        resolution=(1 / E.parameters.dx, 1 / E.parameters.dx),
        metadata={
            'unit': 'micron',
            'hyperstack': 'true',
            'mode': 'composite'})


if __name__ == '__main__':

    # this script assumes you have aquired a series of 2-channel zstacks
    # (not actually a stack,  turn off Z galvo,  and Z and Sample Piezos
    # the first channel is "bright" and "even" (such as 488 laser sheet exciting FITC)
    # and the second channel is "dark" (I use another wavelength with the laser off
    # ... this is repeated for many different "bright channel" intensities:
    # start at very low power (0.1# laser) and gradually acquire stacks at
    # higher powers. It's particularly important to get a lot of low-powered
    # stacks: 1%,  2%,  3% etc... then after 10% you can begin to take bigger steps
    #
    # also,  make sure to use a bigger camera ROI than you ever otherwise do
    # 1024x512 worked for me (I rarely image greater than 800 x 400 pixels)
    # and it's nice to confirm you're centered on the camera
    #
    # this is the folder with all of the stacks

    folder = '/Users/talley/Desktop/FlashCarryoverCalibration161219/'

    # futhermore ... there should be a folder inside of that called 'dark' that
    # holds the following files:
    # '.\dark\dark_AVG.tif'  -> an Avgerage projection of > 20,000 dark images
    # '.\dark\dark_STD.tif'  -> an StdDev projection of > 20,000 dark images
    # darkavg = tf.imread(os.path.join(folder, 'dark', 'dark_AVG.tif'))
    # darkstd = tf.imread(os.path.join(folder, 'dark', 'dark_STD.tif'))

    process_bright_images(folder, *process_dark_images(folder))
