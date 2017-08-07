import ctypes

# can't seem to not have this in there for pyinstaller...
try:
	otflib = ctypes.CDLL('libradialft.dylib')
except Exception:
	pass

# get specific library by platform
if sys.platform.startswith('darwin'):
	libname = 'libradialft.dylib'
elif sys.platform.startswith('win32'):
	libname = 'libradialft.dll'
else:
	libname = 'libradialft.so'

# by defatul ctypes uses ctypes.util.find_library() which will search
# the LD_LIBRARY_PATH or DYLD_LIBRARY_PATH for the library name
# this method is preferable for bundling the app with pyinstaller
# however, for ease of development, we fall back on the local libraries
# in llspy/lib

try:
	otflib = ctypes.CDLL(libname)
except OSError:
	curdir = os.path.dirname(__file__)
	sharelib = os.path.abspath(os.path.join(curdir, '..', 'lib', libname))
	otflib = ctypes.CDLL(sharelib)

shared_makeotf = otflib.makeOTF
shared_makeotf.restype = ctypes.c_int
shared_makeotf.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int,
	ctypes.c_float, ctypes.c_int, ctypes.c_bool, ctypes.c_float,
	ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_int]

def makeotf(psf, otf=None, lambdanm=520, dz=0.102, interpkr=10,
	bUserBackground=False, background=90, NA=1.25, NIMM=1.3,
	dr=0.102, krmax=0):

	if otf is None:
		otf = psf.replace('.tif','_otf.tif')
	return shared_makeotf(str.encode(psf), str.encode(otf), lambdanm, dz,
		interpkr, bUserBackground, background, NA, NIMM, dr, krmax)

