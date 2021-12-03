import numpy as np
from scipy.ndimage.interpolation import map_coordinates

from .imref import imref3d

try:
    from numba import njit
except ImportError:

    def njit(f):
        return f


def imwarp(inputImage, tform, R_A=None, outputRef=None):
    """transform input image with provided tform matrix"""

    # checkImageAgreementWithTform(inputImage,tform)

    if R_A is None:
        R_A = imref3d(inputImage.shape)
    else:
        pass
        # checkSpatialRefAgreementWithInputImage(inputImage,R_A)

    if outputRef is None:
        # TODO: decide how to handle this... calculateOutputRA gives the impression
        # that nothing has been done... (need to pass outputRef to see translaiton, eg.)
        # but is probably more extensible...
        outputRef = R_A
        # outputRef = calculateOutputSpatialReferencing(R_A, tform)
    else:
        pass
        # checkOutputViewAgreementWithTform(outputRef,tform)

        # Resampling the input image must be done in a floating point type.
    if not np.issubdtype(inputImage.dtype, np.float):
        inputImage = inputImage.astype(np.float64)

        # Form grid of intrinsic points in output image.
    destZIntrinsic, destYIntrinsic, destXIntrinsic = np.mgrid[
        1 : outputRef.ImageSize[0] + 1,
        1 : outputRef.ImageSize[1] + 1,
        1 : outputRef.ImageSize[2] + 1,
    ]

    # Find location of pixel centers of destination image in world coordinates
    # as the starting point for reverse mapping.
    destXWorld, destYWorld, destZWorld = outputRef.intrinsicToWorld(
        destXIntrinsic, destYIntrinsic, destZIntrinsic
    )
    # del destXIntrinsic, destYIntrinsic, destZIntrinsic

    # Reverse map pixel centers from destination image to source image via
    # inverse transformation.
    srcXWorld, srcYWorld, srcZWorld = transformPoints(
        tform, destXWorld, destYWorld, destZWorld, inverse=True
    )
    # del destXWorld, destYWorld, destZWorld

    # Find srcX, srcY, srcZ in intrinsic coordinates to use when
    # interpolating.
    srcXIntrinsic, srcYIntrinsic, srcZIntrinsic = R_A.worldToIntrinsic(
        srcXWorld, srcYWorld, srcZWorld
    )
    # del srcXWorld, srcYWorld, srcZWorld

    # map_coordinates(input, coordinates, output=None, order=3, mode='constant', cval=0.0, prefilter=True)
    outputImage = map_coordinates(
        inputImage, [srcZIntrinsic - 1, srcYIntrinsic - 1, srcXIntrinsic - 1], order=1
    )
    return outputImage


def calculateOutputSpatialReferencing(R_in, tform):
    XWorldLimitsOut, YWorldLimitsOut, ZWorldLimitsOut = outputLimits(
        tform, R_in.XWorldLimits, R_in.YWorldLimits, R_in.ZWorldLimits
    )
    R_out = snapWorldLimitsToSatisfyResolution(
        XWorldLimitsOut,
        YWorldLimitsOut,
        ZWorldLimitsOut,
        R_in.PixelExtentInWorldX,
        R_in.PixelExtentInWorldY,
        R_in.PixelExtentInWorldZ,
    )
    return R_out


def snapWorldLimitsToSatisfyResolution(
    idealWLX, idealWLY, idealWLZ, outRX, outRY, outRZ
):
    idealWLX = np.array(idealWLX)
    idealWLY = np.array(idealWLY)
    idealWLZ = np.array(idealWLZ)

    numCols = int(np.ceil(np.diff(idealWLX)[0] / outRX))
    numRows = int(np.ceil(np.diff(idealWLY)[0] / outRY))
    numPlanes = int(np.ceil(np.diff(idealWLZ)[0] / outRZ))

    xNudge = (numCols * outRX - np.diff(idealWLX)[0]) / 2
    yNudge = (numRows * outRY - np.diff(idealWLY)[0]) / 2
    zNudge = (numPlanes * outRZ - np.diff(idealWLZ)[0]) / 2

    XWorldLimOut = idealWLX + np.array([-xNudge, xNudge])
    YWorldLimOut = idealWLY + np.array([-yNudge, yNudge])
    ZWorldLimOut = idealWLZ + np.array([-zNudge, zNudge])

    outputImageSize = [numPlanes, numRows, numCols]
    return imref3d(outputImageSize, XWorldLimOut, YWorldLimOut, ZWorldLimOut)


def outputLimits(tform, xLimitsIn, yLimitsIn, zLimitsIn):
    u = [xLimitsIn[0], np.mean(xLimitsIn), xLimitsIn[1]]
    v = [yLimitsIn[0], np.mean(yLimitsIn), yLimitsIn[1]]
    w = [zLimitsIn[0], np.mean(zLimitsIn), zLimitsIn[1]]

    # Form grid of boundary points and internal points used by
    # findbounds algorithm.
    U, V, W = np.meshgrid(u, v, w)
    # Transform gridded points forward
    X, Y, Z = transformPoints(tform, U, V, W)

    xo = np.array([np.min(X), np.max(X)])
    yo = np.array([np.min(Y), np.max(Y)])
    zo = np.array([np.min(Z), np.max(Z)])

    return xo, yo, zo


def transformPackedPointsInverse(tform, x, y, z):
    # make sure they are the same size
    if not tform.shape == (4, 4):
        raise ValueError("transformation expects a 4x4 tform matrix")
    packed = np.array([x.ravel(), y.ravel(), z.ravel()])
    ndim = ndim = packed.shape[0]
    homo = np.vstack((packed, np.ones((1, packed.shape[1]))))
    tformed_points = np.dot(np.linalg.inv(tform), homo)[:ndim, :]
    xt = tformed_points[0].reshape(x.shape)
    yt = tformed_points[1].reshape(y.shape)
    zt = tformed_points[2].reshape(z.shape)
    return xt, yt, zt


@njit
def transformPoints(M, x, y, z, inverse=False):
    if not len({A.shape for A in (x, y, z)}):
        raise ValueError("coordinate lists must all be the same size")
    if not M.shape == (4, 4):
        raise ValueError("transformation expects a 4x4 tform matrix")
    if inverse:
        M = np.linalg.inv(M)
    xt = M[0, 0] * x + M[0, 1] * y + M[0, 2] * z + M[0, 3]
    yt = M[1, 0] * x + M[1, 1] * y + M[1, 2] * z + M[1, 3]
    zt = M[2, 0] * x + M[2, 1] * y + M[2, 2] * z + M[2, 3]
    return xt, yt, zt
