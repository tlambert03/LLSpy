import numpy as np
import os
import sys
from PIL import Image
from numpy.fft import fft2, ifftshift, fftshift
from scipy.interpolate import RectBivariateSpline, RegularGridInterpolator
from scipy.ndimage.interpolation import rotate
from numba import jit


def ronchi_ruling(width=1, slm_xpix=1280, slm_ypix=1024, orientation='horizontal',
                  outdir=None):
    out = np.zeros((slm_ypix, slm_xpix), np.int8)
    if orientation.lower() == 'vertical':
        for i in range(width):
            out[i::width*2] = 1
    elif orientation.lower() == 'horizontal':
        for i in range(width):
            out[:, i::width*2] = 1
    else:
        raise ValueError('orientation argument must be either "horizontal" or "vertical", '
                         'got: '.format(orientation))

    if outdir is not None:
        outdir = os.path.abspath(os.path.expanduser(outdir))
        if os.path.isdir(outdir):
            name = 'Ronchi_{}pix'.format(width)
            outpath = os.path.join(outdir, name + '.png')
            imout = Image.fromarray(out.astype(np.uint8)*255)
            imout = imout.convert('1')
            imout.save(outpath)

    return out


def makeSLMPattern(wave=0.488, NA_inner=0.44, NA_outer=0.55, spacing=None,
                   n_beam='fill', crop=0.22, tilt=0, shift_x=0, shift_y=0,
                   mag=167.364, pixel=13.662, slm_xpix=1280, slm_ypix=1024,
                   fillchip=0.95, fudge=0.95, show=False, outdir=None,
                   pattern_only=True):

    # auto-choose good spacing
    if not spacing:
        spacing = fudge * wave / NA_inner

    #  to fill the chip
    if n_beam == 'fill' and fillchip:
        n_beam = int(np.floor(1 + ((fillchip * (slm_xpix * (pixel/mag)/2)) / spacing)))

    # expand cropping for single bessel
    # if n_beam == 1:
    #    crop = min((.0291, crop))

    # Populate real space array
    dx = pixel / mag
    x = np.arange(-(slm_xpix)/2, (slm_xpix+1)/2, 1.0) * dx
    y = x
    # for scipy interpolation functions, we don't use the meshgrid...
    # [x, y] = np.meshgrid(x, y)
    # x_slm = linspace(x[0, 0], x[-1, -1], slm_xpix)
    x_slm = np.linspace(x[0], x[-1], slm_xpix)
    y_slm = x_slm
    # [x_slm, y_slm] = np.meshgrid(x_slm, y_slm)

    # Populate k space array
    dk = 2 * np.pi / (slm_xpix + 1) / dx
    kx = np.arange(-(slm_xpix)/2, (slm_xpix+1)/2, 1.0) * dk
    ky = kx
    [kx, ky] = np.meshgrid(kx, ky)
    kr = np.sqrt(kx*kx + ky*ky)

    # Mask k-space array according to inner and outer NA
    pupil_mask = (kr < NA_outer * (2 * np.pi / wave)) & (kr > NA_inner * (2 * np.pi/wave))

    # Generate array of bessel beams by applying phase ramps in k-space
    pupil_field_ideal = pupil_mask.astype(np.complex128)

    f = kx * spacing * np.cos(tilt) + ky * spacing * np.sin(tilt)

    if getattr(sys, 'frozen', False):
        @jit(nopython=True)
        def calc(v, ii):
            A = np.exp(1j * f * ii) + np.exp(-1j * f * ii)
            return v + np.multiply(pupil_mask, A)
    else:
        @jit(nopython=True, cache=True)
        def calc(v, ii):
            A = np.exp(1j * f * ii) + np.exp(-1j * f * ii)
            return v + np.multiply(pupil_mask, A)

    for ii in range(1, n_beam):
        # A = np.exp(1j * f * ii)
        # B = np.exp(-1j * f * ii)
        # pupil_field_ideal += pupil_mask * (A+B)
        pupil_field_ideal = calc(pupil_field_ideal, ii)
    pupil_field_ideal *= np.exp(1j * (kx * shift_x + ky * shift_y))

    # Ideal SLM field of fourier transform of pupil field
    slm_field_ideal = fftshift(fft2(ifftshift(pupil_field_ideal))).real
    slm_field_ideal /= np.max(np.max(np.abs(slm_field_ideal)))

    # Display ideal intensity at sample (incorporates supersampling)
    if show:
        import matplotlib.pyplot as plt
        plt.figure()
        plt.imshow(abs(slm_field_ideal*slm_field_ideal))
        plt.title('Ideal coherent bessel light sheet intensity')
        plt.axis('image')

    # Interpolate back onto SLM pixels and apply cropping factor
    # interpolator = interp2d(x, x, slm_field_ideal)
    interpolator = RectBivariateSpline(x, y, slm_field_ideal)
    slm_pattern = interpolator(x_slm, y_slm)
    slm_pattern *= abs(slm_pattern) > crop
    slm_pattern = np.sign(slm_pattern + 0.001) * np.pi/2 + np.pi/2

    # needed slightly higher cropping value for python

    # Account for rectangular aspect ratio of SLM and convert phase to binary
    low = int(np.floor((slm_xpix/2)-(slm_ypix/2)-1))
    high = int(low + slm_ypix)
    slm_pattern_final = (slm_pattern[low:high, :] / np.pi) != 0

    if outdir is not None:
        outdir = os.path.abspath(os.path.expanduser(outdir))
        if os.path.isdir(outdir):
            namefmt = '{:.0f}_{:2d}b_s{:.2f}_c{:.2f}_na{:.0f}-{:.0f}_x{:02f}_y{:02f}_t{:0.3f}'
            name = namefmt.format(wave*1000, n_beam*2-1, spacing, crop,
                                  100*NA_outer, 100*NA_inner, shift_x, shift_y, tilt)
            name = name.replace('.', 'p')
            outpath = os.path.join(outdir, name + '.png')

            imout = Image.fromarray(slm_pattern_final.astype(np.uint8)*255)
            imout = imout.convert('1')
            imout.save(outpath)

    if show:
        plt.figure()
        plt.imshow(slm_pattern, interpolation='nearest')
        plt.title('Cropped and pixelated phase from SLM pattern exiting the polarizing beam splitter')
        plt.axis('image')

        plt.figure()
        plt.imshow(slm_pattern_final, interpolation='nearest', cmap='gray')
        plt.title('Binarized image to output to SLM')

    if pattern_only:
        if show:
            plt.show()
        return slm_pattern_final

    # THIS SHOULD GO INTO SEPERATE FUNCTION

    # Convert SLM pattern to phase modulation
    # Interpolate back so that there is odd number of pixels for FFT calculation (want center at 0)

    # this method uses nearest neighbor like the matlab version
    [xmesh, ymesh] = np.meshgrid(x, y)
    coords = np.array([xmesh.flatten(), ymesh.flatten()]).T
    interpolator = RegularGridInterpolator((x_slm, y_slm), slm_pattern, method='nearest')
    slm_pattern_cal = interpolator(coords)  # supposed to be nearest neighbor
    slm_pattern_cal = slm_pattern_cal.reshape(len(x), len(y)).T
    slm_field = np.exp(1j * slm_pattern_cal)

    # at this point, matlab has complex component = 0.0i

    # Compute intensity impinging on annular mask
    pupil_field_impinging = fftshift(fft2(ifftshift(slm_field)))
    # Compute intensity passing through annular mask
    pupil_field = pupil_field_impinging * pupil_mask

    if show:
        plt.figure()
        ax1 = plt.subplot(1, 2, 1)
        plt.imshow((pupil_field_impinging * np.conj(pupil_field_impinging)).real, interpolation='nearest', cmap='inferno')
        plt.clim(0, (2 * n_beam-1) * 3e6)
        plt.title('Intensity impinging on annular mask')
        plt.subplot(1, 2, 2, sharex=ax1)
        plt.imshow((pupil_field * np.conj(pupil_field)).real, interpolation='nearest', cmap='inferno')
        plt.clim(0, (2 * n_beam-1) * 3e6)
        plt.title('Intensity after annular mask')

    # Compute intensity at sample
    field_final = fftshift(fft2(ifftshift(pupil_field)))
    intensity_final = (field_final * np.conj(field_final)).real

    if show:
        plt.figure()
        plt.imshow(intensity_final, interpolation='nearest')
        plt.title('Actual intensity at sample')
        plt.axis('image')

        plt.show()

    pupil_field = np.real(pupil_field * np.conj(pupil_field))
    return slm_pattern_final, intensity_final, pupil_field


def makeSLMPattern_hex(wave=0.488, pixel=13.665, mag=167.364,
                       shift_x=0, shift_y=0, NA_outer=0.6,
                       NA_ideal=0.55, NA_inner=0.505, tilt=0, field_sign=1,
                       slm_xpix=1280, slm_ypix=1024,
                       xyPol=(0, 1), pos_offset=(0, 0),
                       bound='gauss', fill_factor=0.75, crop=0.15,
                       pattern_only=True, outdir=None, **kwargs):

    f = 0.866025403784438
    PW = np.array([[1, 0, 0, 0, -1, 0],
                [0.5, f, 0, f, -0.5, 0],
                [0.5, -f, 0, f, 0.5, 0],
                [1, 0, 0, 0, 1, 0],
                [0.5, f, 0, -f, 0.5, 0],
                [0.5, -f, 0, -f, -0.5, 0]])

    # define the plot dimensions for the lattice:
    SLMPixSize = pixel / mag  # SLM pixel size when projected to the sample, in microns
    numpix = [int(slm_xpix/2), int(slm_ypix/2)]
    pixsize = np.array([SLMPixSize, SLMPixSize]) / (wave / 1.33)

    # calc the cone angle for the wavevectors of the ideal 2D lattice
    # which is written to the SLM:
    # NA_ideal = min(max(NA_ideal, NA_inner), NA_outer)
    index = 1.33  # refractive index of the imaging medium
    ConeAng = np.arcsin(NA_ideal/index)  # cone angle of illumination in radians

    # ensure that the k vectors lie in a plane (i.e., cone angle = 90 deg):
    PW[:, 3:5] = PW[:, 3:5] / np.sqrt(1 - PW[0, 5]**2)
    PW[:, 5] = 0

    # now modify each k vector to reflect the cone angle upon which they lie:
    PW[:, 3:5] = np.sin(ConeAng) * PW[:, 3:5]
    PW[:, 5] = np.cos(ConeAng)

    # normalize the input polarization and make it a 1 x 3 vector:
    xyPol = np.array(xyPol)
    InputPol = np.array([xyPol[0], xyPol[1], 0])
    InputPol = InputPol / np.linalg.norm(InputPol)

    B = PW.shape
    for n in range(B[0]):
        # find the orthonormal vectors defining the coordinate system for the
        # nth beam when entering the rear pupil:
        phivec = np.cross(np.squeeze(PW[n, 3:6]), np.array([0, 0, 1]))
        phivec = phivec / np.linalg.norm(phivec)  # azimuthal unit vector
        radvec = np.cross(np.array([0, 0, 1]), phivec)  # radial unit vector

        # the azimuthal component of the electric field is unaffected when passing
        # through the objective:
        ephi = np.dot(phivec, InputPol)

        # the radial component is tilted by refraction when passing through the
        # objective to point in the theta direcclose ation as defined by a spherical
        # coordinate system centered at the focal point:
        thetavec = np.cross(np.squeeze(PW[n, 3:6]), phivec)
        etheta = np.dot(radvec, InputPol)
        #
        # the sum of the azimuthal and theta components gives the total electric
        # field for the nth plane wave of the lattice:
        PW[n, 0:3] = ephi * phivec + etheta * thetavec
        #
        # confirm that the electric field is of unit strength:
        PW[n, 0:3] = PW[n, 0:3] / np.linalg.norm(PW[n, 0:3])

    # find the degree of confinement of the 2D lattice along the theoretically
    #     unpattered y direction, based on the max and min illumination NAs:
    # kzmax = 2 * np.pi * np.sqrt(1 - (NA_inner/index)**2)
    # kzmin = 2 * np.pi * np.sqrt(1 - (NA_outer/index)**2)
    # kzdiff = kzmax - kzmin
    # yextent = np.pi / kzdiff  # approximate extent of the lattice in y, in media wavelengths

    # find the period and degree of confinement in wavelengths along the xz axes:
    #   each period is given by the smallest non-zero difference of the
    #      k vector components along that axis
    #   max. confinement in each direction is given by the largest
    #      difference of the k vector components along that axis
    period = np.zeros((2, 2))
    for m in range(2):   # loop thru both axes
        mindiff = 2      # difference must be < 2 for normalized k
        maxdiff = 0
        for n in range(B[0]):
            for q in range(B[0]):  # double loop thru all plane wave pairs
                # abs of the sum of the mth component of the nth and qth k vectors
                PWdiff = np.abs(PW[n, (m + 3)] - PW[q, (m + 3)])
                if (PWdiff > 0.001) and (PWdiff < mindiff):
                    # if difference non-zero yet smaller than the smallest
                    # difference thus far then
                    mindiff = PWdiff
                if PWdiff > maxdiff:
                    # if difference is larger than the largest
                    # difference thus far then
                    maxdiff = PWdiff
        period[0, m] = 1 / mindiff  # period in wavelengths along m axis
        period[1, m] = 1 / maxdiff  # confinement in wavelengths along m axis

    # calculate the complete electric field of the ideal 2D lattice:
    x = pixsize[0] * np.arange(0, numpix[0] + 1) + pos_offset[0] * period[0, 0]
    y = pixsize[1] * np.arange(0, numpix[1] + 1) + pos_offset[1] * period[0, 1]
    [X, Y] = np.meshgrid(x, y)

    # now calculate the E field at each mesh point:
    A = X.shape
    Ex = np.zeros(A)
    Ey = np.zeros(A)
    Ez = np.zeros(A)
    for q in range(B[0]):   # loop thru all plane waves
        phase = np.exp(2 * np.pi * 1j * (PW[q, 3] * X + PW[q, 4] * Y))
        Ex = Ex + PW[q, 0] * phase
        Ey = Ey + PW[q, 1] * phase
        Ez = Ez + PW[q, 2] * phase

    # expand through all quadrants:
    Extemp = np.zeros(np.array(A)*2, dtype=np.complex128)
    Eytemp = np.zeros(np.array(A)*2, dtype=np.complex128)
    Eztemp = np.zeros(np.array(A)*2, dtype=np.complex128)
    # load the original data into the first quadrant:
    Extemp[A[0]:, A[1]:] = Ex
    Eytemp[A[0]:, A[1]:] = Ey
    Eztemp[A[0]:, A[1]:] = Ez
    # now mirror along each dimension and use parities to fill other quadrants:
    # simply mirror the data since parity is always even for magnitudes:
    Extemp[:A[0], A[1]:] = np.flip(Ex, 0)
    Eytemp[:A[0], A[1]:] = np.flip(Ey, 0)
    Eztemp[:A[0], A[1]:] = np.flip(Ez, 0)
    Extemp[:, :A[1]] = np.flip(Extemp[:, A[1]:], 1)
    Eytemp[:, :A[1]] = np.flip(Eytemp[:, A[1]:], 1)
    Eztemp[:, :A[1]] = np.flip(Eztemp[:, A[1]:], 1)
    # delete the extra vector from mirroring in each dimension:
    Extemp = np.delete(Extemp, A[0], 0)
    Eytemp = np.delete(Eytemp, A[0], 0)
    Eztemp = np.delete(Eztemp, A[0], 0)
    Extemp = np.delete(Extemp, A[1], 1)
    Eytemp = np.delete(Eytemp, A[1], 1)
    Eztemp = np.delete(Eztemp, A[1], 1)
    Ex = Extemp
    Ey = Eytemp
    Ez = Eztemp
    del Extemp, Eytemp, Eztemp

    # # find the ideal 2D lattice intensity:
    # A = Ex.shape
    # EComp = np.zeros((3, A[0], A[1])).astype(np.complex128)
    # EComp[0, :, :] = Ex
    # EComp[1, :, :] = Ey
    # EComp[2, :, :] = Ez
    # ESq = EComp * np.conj(EComp)
    # ESqTot = np.squeeze(sum(ESq, 1))
    # maxval = ESqTot.max()
    # # minval = ESqTot.min()
    # ESqTot = ESqTot / maxval

    # calc and plot the ideal 2D lattice of the component of the real electric field
    #   projected onto the state of the input electric field polarization:
    if field_sign == 1:
        RealE = np.real(np.conj(Ex) * InputPol[0] + np.conj(Ey) * InputPol[1])
    else:
        RealE = -np.real(np.conj(Ex) * InputPol[0] + np.conj(Ey) * InputPol[1])

    # find the required extent of the bound lattice at the SLM based on the
    #    maximum and minimum NA at the rear pupil:
    kxmax = 2 * np.pi * (NA_outer / index)
    kxmin = 2 * np.pi * (NA_inner / index)
    kxdiff = kxmax - kxmin
    # approximate half width of the function limiting
    # the extent of the bound lattice, in media wavelengths
    lattice_full_width = np.pi / kxdiff

    # calc and plot the bound 2D lattice at the SLM:
    A = RealE.shape
    if bound == 'step':
        maxzpix = int(lattice_full_width / (2 * pixsize[0] * fill_factor))
        midpix = int(A[0] / 2)
        RealE[:(midpix - maxzpix), :] = 0
        RealE[(midpix + maxzpix)+1:, :] = 0
    elif bound == 'gauss':
        z = np.arange(-numpix[1], numpix[1]+1) * pixsize[1]
        sigma = lattice_full_width / np.sqrt(2 * np.log(2)) / fill_factor
        envelope = np.tile(np.exp(-2 * (z / sigma)**2), (A[1], 1))
        RealE = RealE * envelope.T
    else:
        raise ValueError('invalid bounding function value: ', bound)

    # now rotate the E field as needed to get the pattern in the same plane as the detection objective:
    RotatedRealE = rotate(RealE, np.rad2deg(tilt), reshape=False)
    # save the 4D SLM pattern:
    RotatedRealE = RotatedRealE / RotatedRealE.max()
    # truncate any values below the level of crop:
    RotatedRealE[np.abs(RotatedRealE) < crop] = 0
    # now create the binary phase function (0 or pi) for the SLM:
    eps = np.finfo(float).eps
    SLMPattern = np.round(np.sign(RotatedRealE + eps) / 2 + 0.5)
    SLMPattern = SLMPattern[:slm_ypix, :slm_xpix]
    SLM_offsetY = int(shift_y * mag / pixel)
    SLM_offsetX = int(shift_x * mag / pixel)
    SLMPattern = np.roll(SLMPattern, SLM_offsetY, 0)  # y shift
    SLMPattern = np.roll(SLMPattern, SLM_offsetX, 1)  # x shift

    if outdir is not None:
        outdir = os.path.abspath(os.path.expanduser(outdir))
        if os.path.isdir(outdir):
            namefmt = '{:.0f}_{}Hex_c{:.2f}_na{:.0f}-{:.0f}_naIdeal{:.0f}_y{:02d}_t{:0.3f}'
            name = namefmt.format(wave*1000, bound, crop, 100*NA_outer, 100*NA_inner,
                100*NA_ideal, shift_y, tilt)
            name = name.replace('.', 'p')
            outpath = os.path.join(outdir, name + '.png')
            imout = Image.fromarray(SLMPattern.astype(np.uint8)*255)
            imout = imout.convert('1')
            imout.save(outpath)

    if pattern_only:
        return SLMPattern

    ###########################

    # now create the binary phase function (0 or pi) for the SLM:
    # RealE = RealE / RealE.max()
    # RealE[np.abs(RealE) < crop] = 0
    # BinaryEPhase = np.sign(RealE + eps) * np.pi / 2 + np.pi / 2
    BinaryEPhase = np.sign(RotatedRealE + eps) * np.pi / 2 + np.pi / 2

    # calc the electric field at the annular mask:
    ESLM = np.exp(1j * BinaryEPhase)
    # restrict the field to a square for simplicity of code:
    midpix = int(ESLM.shape[1] / 2)
    ESLM = ESLM[:, midpix-int(ESLM.shape[0]/2):midpix+int(ESLM.shape[0]/2)+1]
    EMask = fftshift(fft2(ifftshift(ESLM)))  # complex electric field impinging on the annular mask

    # plot the intensity impinging on the annular mask:
    MaskIntensity_impinging = np.real(EMask * np.conj(EMask))  # intensity impinging on the annular mask

    # calc and plot the function for the filtering provided by the annular mask:
    B = MaskIntensity_impinging.shape
    halfpix = int(np.floor(B[0]/2))
    x = np.arange(-halfpix, halfpix + 1)
    x = x / halfpix / (2 * pixsize[0])   # match the spectral range of the electric field at the annular mask
    y = x
    [X, Y] = np.meshgrid(x, y)
    R = np.sqrt(X*X + Y*Y)
    MaxRad = NA_outer / index  # maximum annulus diameter
    MinRad = NA_inner / index  # minimum annulus diameter
    AnnularFilter = (R <= MaxRad) & (R >= MinRad)

    # calc the E field immediately after transmission through the annulus:
    EAfterMask = EMask * AnnularFilter
    # plot the intensity immediately after the annular mask:
    MaskIntensity = np.real(EAfterMask * np.conj(EAfterMask))

    # calc and plot the intensity at the sample:
    ESample = fftshift(fft2(ifftshift(EAfterMask)))
    SampleIntensity = np.real(ESample * np.conj(ESample))

    return SLMPattern, SampleIntensity, MaskIntensity


if __name__ == '__main__':
    import time
    # now = time.time()
    # a = makeSLMPattern(0.488, n_beam='fill', show=False, outdir='~/Desktop')
    # print("Time: {}".format(time.time()-now))

    now = time.time()
    a, b, c = makeSLMPattern(0.488, n_beam='fill', show=True, pattern_only=False)
    print("Time: {}".format(time.time()-now))

    # plt.figure()
    # plt.imshow(a, interpolation='nearest', cmap='gray')
    # plt.title('Binarized image to output to SLM')
    # plt.show()
