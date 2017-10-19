import numpy as np
import os
import sys
from numpy.fft import fft2, ifftshift, fftshift
from scipy.interpolate import RectBivariateSpline, RegularGridInterpolator
from numba import jit


def makeSLMPattern(wave=0.488, NA_inner=0.44, NA_outer=0.55, spacing=None,
                   n_beam='fill', crop=0.15, tilt=0, shift_x=0, shift_y=0,
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
            from PIL import Image
            namefmt = '{:.0f}_{:2d}b_s{:.2f}_c{:.2f}_na{:.0f}-{:.0f}_x{:02d}_y{:02d}_t{:0.3f}'
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

    return (slm_pattern_final, intensity_final,
            (pupil_field * np.conj(pupil_field)).real)


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import time
    now = time.time()
    a = makeSLMPattern(0.488, n_beam='fill', show=False, outdir='~/Desktop')
    print("Time: {}".format(time.time()-now))

    now = time.time()
    #a, b, c = makeSLMPattern(0.488, n_beam='fill', show=False, pattern_only=False)
    print("Time: {}".format(time.time()-now))

    # plt.figure()
    # plt.imshow(a, interpolation='nearest', cmap='gray')
    # plt.title('Binarized image to output to SLM')
    # plt.show()
