import numpy as np
from matplotlib import pyplot as plt
from scipy.ndimage.interpolation import rotate

f = 0.866025403784438
PW_input = np.array([[1, 0, 0, 0, -1, 0],
            [0.5, f, 0, f, -0.5, 0],
            [0.5, -f, 0, f, 0.5, 0],
            [1, 0, 0, 0, 1, 0],
            [0.5, f, 0, -f, 0.5, 0],
            [0.5, -f, 0, -f, -0.5, 0]])
PW = PW_input
wave = 0.488
pos_offset = [0, 0]
Pix_size = 13.665
Mag = 167.364
y_offset = 0
SLM_offset = int(y_offset * Mag / Pix_size)
xyPol = [0, 1]
NAmax = 0.6
NAideal = 0.55
NAmin = 0.505
tilt_angle = 0.07
field_sign = 1
bounding_function = 'gauss'
fill_factor = 0.75
crop_factor = 0.15
# xz_det_PSF = xz_PSF_488_NA1p1

# define the plot dimensions for the lattice:
SLMPixSize = Pix_size / Mag  # SLM pixel size when projected to the sample, in microns
numpix = [640, 512]  # TODO: come back to this
pixsize = np.array([SLMPixSize, SLMPixSize]) / (wave / 1.33)

# calc the cone angle for the wavevectors of the ideal 2D lattice
# which is written to the SLM:
# NAideal = min(max(NAideal, NAmin), NAmax)
index = 1.33  # refractive index of the imaging medium
ConeAng = np.arcsin(NAideal/index)  # cone angle of illumination in radians

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
kzmax = 2 * np.pi * np.sqrt(1 - (NAmin/index)**2)
kzmin = 2 * np.pi * np.sqrt(1 - (NAmax/index)**2)
kzdiff = kzmax - kzmin
yextent = np.pi / kzdiff  # approximate extent of the lattice in y, in media wavelengths

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
kxmax = 2 * np.pi * (NAmax / index)
kxmin = 2 * np.pi * (NAmin / index)
kxdiff = kxmax - kxmin
# approximate half width of the function limiting
# the extent of the bound lattice, in media wavelengths
lattice_full_width = np.pi / kxdiff

# calc and plot the bound 2D lattice at the SLM:
A = RealE.shape
if bounding_function == 'step':
    maxzpix = int(lattice_full_width / (2 * pixsize[0] * fill_factor))
    midpix = int(A[0] / 2)
    RealE[:(midpix - maxzpix), :] = 0
    RealE[(midpix + maxzpix)+1:, :] = 0
elif bounding_function == 'gauss':
    z = np.arange(-numpix[1], numpix[1]+1) * pixsize[1]
    sigma = lattice_full_width / np.sqrt(2 * np.log(2)) / fill_factor
    envelope = np.tile(np.exp(-2 * (z / sigma)**2), (A[1], 1))
    RealE = RealE * envelope.T
else:
    raise ValueError('invalid bounding function value: ', bounding_function)

# now rotate the E field as needed to get the pattern in the same plane as the detection objective:
RotatedRealE = rotate(RealE, np.rad2deg(tilt_angle), reshape=False)
# save the 4D SLM pattern:
RotatedRealE = RotatedRealE / RotatedRealE.max()
# truncate any values below the level of crop_factor:
RotatedRealE[np.abs(RotatedRealE) < crop_factor] = 0
# now create the binary phase function (0 or pi) for the SLM:
eps = np.finfo(float).eps
SLMPattern = np.round(np.sign(RotatedRealE + eps) / 2 + 0.5)
SLMPattern = SLMPattern[:1024, :1280]
SLMPattern = np.roll(SLMPattern, SLM_offset, 0)  # y shift
