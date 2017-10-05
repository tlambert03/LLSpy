from .util import load_lib
import ctypes
import numpy as np
import os
import sys
import logging
logger = logging.getLogger(__name__)

cudaLib = load_lib('libcudaDeconv')

if not cudaLib:
    logger.error('Could not load libcudaDeconv!  Read docs for more info')
else:
    try:
        # Deskew is used when no decon is desired
        # https://stackoverflow.com/questions/5862915/passing-numpy-arrays-to-a-c-function-for-input-and-output
        Deskew_interface = cudaLib.Deskew_interface
        Deskew_interface.restype = ctypes.c_int
        Deskew_interface.argtypes = [np.ctypeslib.ndpointer(ctypes.c_float, flags="C_CONTIGUOUS"),
                        ctypes.c_int,
                        ctypes.c_int,
                        ctypes.c_int,
                        ctypes.c_float,
                        ctypes.c_float,
                        ctypes.c_float,
                        np.ctypeslib.ndpointer(ctypes.c_float, flags="C_CONTIGUOUS"),
                        ctypes.c_int,
                        ctypes.c_int]

        # Affine transformation
        Affine_interface = cudaLib.Affine_interface
        Affine_interface.restype = ctypes.c_int
        Affine_interface.argtypes = [np.ctypeslib.ndpointer(ctypes.c_float, flags="C_CONTIGUOUS"),
                        ctypes.c_int,
                        ctypes.c_int,
                        ctypes.c_int,
                        np.ctypeslib.ndpointer(ctypes.c_float, flags="C_CONTIGUOUS"),
                        np.ctypeslib.ndpointer(ctypes.c_float, flags="C_CONTIGUOUS")]

        # setup
        camcor_interface_init = cudaLib.camcor_interface_init
        camcor_interface_init.restype = ctypes.c_int
        camcor_interface_init.argtypes = [
                        ctypes.c_int,
                        ctypes.c_int,
                        ctypes.c_int,
                        np.ctypeslib.ndpointer(ctypes.c_float, flags="C_CONTIGUOUS")]

        # execute camcor
        camcor_interface = cudaLib.camcor_interface
        camcor_interface.restype = ctypes.c_int
        camcor_interface.argtypes = [np.ctypeslib.ndpointer(ctypes.c_uint16, flags="C_CONTIGUOUS"),
                        ctypes.c_int,
                        ctypes.c_int,
                        ctypes.c_int,
                        np.ctypeslib.ndpointer(ctypes.c_uint16, flags="C_CONTIGUOUS")]

        # RL_interface_init must be used before using RL_interface
        RL_interface_init = cudaLib.RL_interface_init
        RL_interface_init.restype = ctypes.c_int
        RL_interface_init.argtypes = [ctypes.c_int,     # nx
                            ctypes.c_int,               # ny
                            ctypes.c_int,               # nz
                            ctypes.c_float,             # drdata
                            ctypes.c_float,             # dzdata
                            ctypes.c_float,             # drpsf
                            ctypes.c_float,             # dzpsf
                            ctypes.c_float,             # angle
                            ctypes.c_float,             # rotate
                            ctypes.c_int,               # outputwidth
                            ctypes.c_char_p]            # otfpath.encode()

        # used between init and RL_interface to retrieve the post-deskewed image dimensions
        get_output_nx = cudaLib.get_output_nx
        get_output_ny = cudaLib.get_output_ny
        get_output_nz = cudaLib.get_output_nz

        # The actual decon
        RL_interface = cudaLib.RL_interface
        RL_interface.restype = ctypes.c_int
        RL_interface.argtypes = [np.ctypeslib.ndpointer(ctypes.c_ushort, flags="C_CONTIGUOUS"),  # im
                        ctypes.c_int,                                                   # nx
                        ctypes.c_int,                                                   # ny
                        ctypes.c_int,                                                   # nz
                        np.ctypeslib.ndpointer(ctypes.c_float, flags="C_CONTIGUOUS"),
                        np.ctypeslib.ndpointer(ctypes.c_float, flags="C_CONTIGUOUS"),   # result
                        ctypes.c_float,                                                 # background
                        ctypes.c_bool,                                                  # doRescale
                        ctypes.c_bool,                                                  # saveDeskewed
                        ctypes.c_int,                                                   # nIters
                        ctypes.c_int]                                                   # shift

        # call after
        RL_cleanup = cudaLib.RL_cleanup

    except AttributeError as e:
        logger.warning('Failed to properly import libcudaDeconv')
        print(e)


def requireCUDAlib(func, *args, **kwargs):
    def dec(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if not cudaLib:
                raise Exception("Could not find libcudaDeconv library! These "
                                "functions will not be available:\n"
                                "Preview\nAutoCrop\nCUDA camera corrections\n"
                                "Channel Registration")
            else:
                raise e
    return dec


def quickCamcor(imstack, camparams):
    """Correct Flash residual pixel artifact on GPU"""
    camcor_init(imstack.shape, camparams)
    camcor(imstack)


@requireCUDAlib
def camcor_init(rawdata_shape, camparams):
    """ initialize camera correction on GPU.
    shape is nz/ny/nx of the concatenated stacks from a single timepoint
    """
    nz, ny, nx = rawdata_shape
    if not np.issubdtype(camparams.dtype, np.float32):
        camparams = camparams.astype(np.float32)
    camcor_interface_init(nx, ny, nz, camparams)


@requireCUDAlib
def camcor(imstack):
    if not np.issubdtype(imstack.dtype, np.uint16):
        print('CONVERTING')
        imstack = imstack.astype(np.uint16)
    nz, ny, nx = imstack.shape
    result = np.empty_like(imstack)
    camcor_interface(imstack, nx, ny, nz, result)
    return result


@requireCUDAlib
def deskewGPU(im, dz=0.5, dr=0.102, angle=31.5, width=0, shift=0):
    """Deskew data acquired in stage-scanning mode on GPU"""
    nz, ny, nx = im.shape
    if not np.issubdtype(im.dtype, np.float32):
        im = im.astype(np.float32)
    # have to calculate this here to know the size of the return array
    if width == 0:
        deskewedNx = np.int(nx + np.floor(nz * dz * abs(np.cos(angle * np.pi / 180)) / dr))
    else:
        deskewedNx = width

    result = np.empty((nz, ny, deskewedNx), dtype=np.float32)
    Deskew_interface(im, nx, ny, nz, dz, dr, angle, result, deskewedNx, shift)
    return result


@requireCUDAlib
def affineGPU(im, tmat):
    """Perform affine transformation of image with provided transformation matrix"""
    nz, ny, nx = im.shape
    if not np.issubdtype(im.dtype, np.float32) or not im.flags['C_CONTIGUOUS']:
        im = np.ascontiguousarray(im, dtype=np.float32)
    if not np.issubdtype(tmat.dtype, np.float32):
        tmat = tmat.astype(np.float32)
    # have to calculate this here to know the size of the return array
    result = np.empty((nz, ny, nx), dtype=np.float32)
    Affine_interface(im, nx, ny, nz, result, tmat)
    return result


def rotateGPU(im, angle=32.5, xzRatio=0.4253, reverse=False):
    # TODO: crop smarter
    npad = ((0, 0), (0, 0), (0, 0))
    im = np.pad(im, pad_width=npad, mode='constant', constant_values=0)

    theta = angle * np.pi/180
    theta = theta if not reverse else -theta

    nz, ny, nx = im.shape
    # first translate the middle of the image to the origin
    T1 = np.array([ [1, 0, 0, nx/2],
                    [0, 1, 0, ny/2],
                    [0, 0, 1, nz/2],
                    [0, 0, 0, 1]])
    # then scale (resample) the Z axis the dz/dx ratio
    S = np.array([  [1, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, xzRatio, 0],
                    [0, 0, 0, 1]])
    # then rotate theta degrees about the Y axis
    R = np.array([[np.cos(theta), 0, -np.sin(theta), 0],
                    [0, 1, 0, 0],
                    [np.sin(theta), 0, np.cos(theta), 0],
                    [0, 0, 0, 1]])
    # then translate back to the original origin
    T2 = np.array([ [1, 0, 0, -nx/2],
                    [0, 1, 0, -ny/2],
                    [0, 0, 1, -nz/2],
                    [0, 0, 0, 1]])
    T = np.eye(4)
    T = np.dot(np.dot(np.dot(np.dot(T, T1), S), R), T2)

    rotated = affineGPU(im, T)

    return rotated


def quickDecon(im, otfpath, savedeskew=False, **kwargs):
    """Perform deconvolution of im with otf at otfpath

    kwargs can be:
        drdata      float
        dzdata      float
        dzpsf       float
        drpsf       float
        wavelength  int
        deskew      float  (0 is no deskew)
        nIters      int
        savedeskew  bool
        width       int
        shift       int
        rotate      float
    """
    RL_init(im.shape, otfpath, **kwargs)
    if savedeskew:
        decon_result, deskew_result = RL_decon(im, savedeskew=True, **kwargs)
        RL_cleanup()
        return decon_result, deskew_result
    else:
        decon_result = RL_decon(im, savedeskew=False, **kwargs)
        RL_cleanup()
        return decon_result


@requireCUDAlib
def RL_init(rawdata_shape, otfpath, drdata=0.104, dzdata=0.5, drpsf=0.104,
    dzpsf=0.1, deskew=31.5, rotate=0, width=0, **kwargs):
    nz, ny, nx = rawdata_shape
    RL_interface_init(nx, ny, nz, drdata, dzdata, drpsf, dzpsf, deskew, rotate,
        width, otfpath.encode())


@requireCUDAlib
def RL_decon(im, background=80, nIters=10, shift=0, savedeskew=False,
    rescale=False, **kwargs):
    nz, ny, nx = im.shape
    decon_result = np.empty((get_output_nz(), get_output_ny(),
            get_output_nx()), dtype=np.float32)

    if savedeskew:
        deskew_result = np.empty_like(decon_result)
    else:
        deskew_result = np.empty(1, dtype=np.float32)

    if not np.issubdtype(im.dtype, np.uint16):
        im = im.astype(np.uint16)
    RL_interface(im, nx, ny, nz, decon_result, deskew_result,
                background, rescale, savedeskew, nIters, shift)

    if savedeskew:
        return decon_result, deskew_result
    else:
        return decon_result


if __name__ == "__main__":
    import sys
    import tifffile as tf
    import matplotlib.pyplot as plt

    if len(sys.argv) >= 2:
        if sys.argv[1] == 'affine':
            # affine test
            im = tf.imread('/Users/talley/Dropbox (HMS)/CBMF/lattice_sample_data/lls_basic_samp/Deskewed/cell5_ch0_stack0001_488nm_0000000msec_0020931273msecAbs_deskewed.tif')
            T = np.array([
                    [1, 0, 0, -50],
                    [0, 1, 0, -100],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]])
            q = affineGPU(im, T)
            tf.imshow(q, vmin=-10, vmax=150)
            plt.show()
        elif sys.argv[1] == 'deskew':
            # deskew test
            im = tf.imread('/Users/talley/Dropbox (HMS)/CBMF/lattice_sample_data/lls_basic_samp/cell5_ch0_stack0000_488nm_0000000msec_0020931273msecAbs.tif')
            tf.imshow(deskewGPU(im, 0.3))
            plt.show()

            # zstep = sys.argv[1]
            # for i in sys.argv[2:]:
            #   p = p = os.path.abspath(i).replace('\\', '')
            #   if os.path.isfile(p):
            #       tf.imshow(deskewGPU(tf.imread(p), float(zstep)))
            #       plt.show()

        elif sys.argv[1] == 'rotate':
            im = tf.imread('/Users/talley/Dropbox (HMS)/CBMF/lattice_sample_data/lls_registration_samp/reg_ex1/tspeck/GPUdecon/tspeck_ch0_stack0000_488nm_0000000msec_0001881189msecAbs_decon.tif')
            angle = float(sys.argv[2]) if len(sys.argv) > 2 else 32.5
            dz = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4
            dx = 0.1
            xzRatio = dx / (np.deg2rad(angle) * dz)
            rotated = rotateGPU(im, angle, xzRatio)
            tf.imshow(rotated, vmin=0, vmax=rotated.max() * 0.5)
            plt.show()

        elif (sys.argv[1] == 'decon') or (sys.argv[1] == 'deconv'):
            im = tf.imread('/Users/talley/Dropbox (HMS)/CBMF/lattice_sample_data/lls_bidirectional/bidir_ch0_stack0000_488nm_0000000msec_0007232334msecAbs.tif')
            otfpath = '/Users/talley/Dropbox (HMS)/CBMF/lattice_sample_data/lls_PSFs/488_otf.tif'
            RL_init(im.shape, otfpath, dzdata=0.4)
            decon = RL_decon(im, nIters=15)
            tf.imshow(decon, vmin=0, vmax=decon.max() * 0.5)
            plt.show()
            RL_cleanup()
        elif sys.argv[1] == 'camcor':

            from llspy import llsdir
            from llspy import samples
            import time

            E = llsdir.LLSdir(samples.stickypix)

            # from llspy.util import util
            # from llspy.camera.camera import CameraParameters, CameraROI

            # camparams = CameraParameters()
            # camparams = camparams.get_subroi(CameraROI(E.settings.camera.roi))

            # camparams.init_CUDAcamcor((E.parameters.nz*E.parameters.nc,
            #   E.parameters.ny, E.parameters.nx))

            # stacks = [util.imread(f) for f in E.get_t(0)]
            # interleaved = np.stack(stacks, 1).reshape((-1, E.parameters.ny, E.parameters.nx))
            # corrected = camcor(interleaved)

            start = time.time()
            E.correct_flash(target='cuda', median=False)
            end = time.time()
            print("CUDA Time: " + str(end - start))

            start = time.time()
            E.correct_flash(target='cpu', median=False)
            end = time.time()
            print("Parallel Time: " + str(end - start))

        else:
            p = os.path.abspath(sys.argv[1]).replace('\\', '')
            if os.path.isfile(p):
                tf.imshow(deskewGPU(tf.imread(p), 0.5))
                plt.show()

