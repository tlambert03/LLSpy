from . import config
from . import plib
import re
import ctypes
import sys
import os
import logging
import numpy as np
from datetime import datetime, timedelta


# get specific library by platform
if sys.platform.startswith('darwin'):
    libname = 'libradialft.dylib'
    # this seems to be necessary for pyinstaller to find it?
    try:
        ctypes.CDLL('libradialft.dylib')
    except Exception:
        pass
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
    logging.debug("Loaded libradialft: " + os.path.abspath(libname))
except OSError:
    try:
        filedir = os.path.dirname(__file__)
        libdir = os.path.abspath(os.path.join(filedir, 'lib'))
        cwd = os.getcwd()
        os.chdir(libdir)
        otflib = ctypes.CDLL(libname)
        logging.debug("Loaded libradialft: " + os.path.abspath(libname))
        os.chdir(cwd)
    except Exception:
        otflib = None

if not otflib:
    logging.warn('COULD NOT LOAD libradialft!  Confirm that FFTW is installed')
else:
    try:
        shared_makeotf = otflib.makeOTF
        shared_makeotf.restype = ctypes.c_int
        shared_makeotf.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int,
            ctypes.c_float, ctypes.c_int, ctypes.c_bool, ctypes.c_float,
            ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_int, ctypes.c_bool]
    except AttributeError as e:
        logging.warn('Failed to properly import libradialft')
        print(e)


def requireOTFlib(func, *args, **kwargs):
    def dec(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if not otflib:
                raise Exception("Could not find libradialft library! OTF generation "
                                "will not be available:")
            else:
                raise e
    return dec


@requireOTFlib
def makeotf(psf, otf=None, lambdanm=520, dz=0.102, fixorigin=10,
            bUserBackground=False, background=90, NA=1.25, NIMM=1.3,
            dr=0.102, krmax=0, bDoCleanup=False):
    # krmax => "pixels outside this limit will be zeroed (overwriting estimated value from NA and NIMM)")
    if otf is None:
        otf = psf.replace('.tif', '_otf.tif')
    shared_makeotf(str.encode(psf), str.encode(otf), lambdanm, dz,
        fixorigin, bUserBackground, background, NA, NIMM, dr, krmax, bDoCleanup)
    return otf


psffile_pattern = re.compile(r"""
    ^(?P<date>\d{8})
    _(?P<wave>\d{3})
    _(?P<psftype>[a-zA-Z_]*)
    (?P<outerNA>[0-9p]+)
    -(?P<innerNA>[0-9p]+)
    (?P<isotf>_otf)?.tif$""", re.VERBOSE)


default_otf_pattern = re.compile(r"""
    ^(?P<wave>\d{3})
    (_otf.tif|.otf)$""", re.VERBOSE)


def dir_has_otfs(dirname):
    return any([psffile_pattern.search(t) or default_otf_pattern.search(t) for t in os.listdir(dirname)])


def get_otf_dict(otfdir):
    """ The otf_dict is a dict with
    """
    otf_dict = {}
    otfdir = plib.Path(otfdir)

    for t in otfdir.glob('*tif'):
        M = psffile_pattern.search(str(t.name))
        if M:
            M = M.groupdict()
            wave = int(M['wave'])
            if wave not in otf_dict:
                otf_dict[wave] = {'default': None}
            mask = (float(M['innerNA'].replace('p', '.')),
                    float(M['outerNA'].replace('p', '.')))
            if mask not in otf_dict[wave]:
                otf_dict[wave][mask] = []
            if not M['isotf']:
                matching_otf = otfdir.joinpath(t.name.replace('.tif', '_otf.tif'))
                if not matching_otf.is_file():
                    matching_otf = None
                else:
                    matching_otf = matching_otf
            else:
                matching_otf = None
            otf_dict[wave][mask].append({
                'date': datetime.strptime(M['date'], '%Y%m%d'),
                'path': str(t),
                'form': 'otf' if M['isotf'] else 'psf',
                'type': M['psftype'],
                'otf': str(matching_otf)
            })
        else:
            M = default_otf_pattern.search(str(t.name))
            if M:
                M = M.groupdict()
                wave = int(M['wave'])
                if wave not in otf_dict:
                    otf_dict[wave] = {}
                otf_dict[wave]['default'] = str(t)
    return otf_dict


def get_otf_by_date(date, wave, mask=None, otfpath=config.__OTFPATH__, direction='nearest'):
    """return otf with date closest to requested date.
    if OTF doesn't exist, but PSF does, generate OTF and return the path.i
    direction can be {'nearest', 'before', 'after'}, where 'before' returns an
    OTF that was collected before 'date' and 'after' returns one that was
    collected after 'date.'
    """
    if not os.path.isdir(str(otfpath)):
        raise ("OTF path does not exist: {}".format(otfpath))
        return None

    otf_dict = get_otf_dict(otfpath)
    otflist = []

    if wave not in otf_dict:
        # raise KeyError('Wave: {} not in otfdict: {}'.format(wave, otf_dict))
        return None

    # the mask NA has been provided, check to see if it's in the name of any of
    # files in the otf folder
    if mask is not None:
        # if so return that otflist
        if mask in otf_dict[wave]:
            otflist = otf_dict[wave][mask]
    else:
        # otherwise
        for k in otf_dict[wave].keys():
            if k != 'default':
                [otflist.append(i) for i in otf_dict[wave][k]]

    if not otflist:
        if os.path.isfile(otf_dict[wave]['default']):
            return otf_dict[wave]['default']
        else:
            return None

    if direction == 'nearest':
        minIdx = np.argmin([np.abs(i['date'] - date) for i in otflist])
    elif direction == 'before':
        deltas = [date - i['date'] for i in otflist]
        test = [d > timedelta(minutes=0) for d in deltas]
        minIdx = next((obj for obj in test if obj), None)
    elif direction == 'after':
        deltas = [i['date'] - date for i in otflist]
        test = [d > timedelta(minutes=0) for d in deltas]
        minIdx = next((obj for obj in test if obj), None)
    else:
        raise ValueError('Unkown direction argument: {}'.format(direction))

    if minIdx is None:
        if os.path.isfile(otf_dict[wave]['default']):
            return otf_dict[wave]['default']
        else:
            return None

    matching_otfs = [i for i in otflist
        if i['date'] == otflist[minIdx]['date'] and i['form'] == 'otf']
    if len(matching_otfs):
        if os.path.isfile(matching_otfs[0]['path']):
            return matching_otfs[0]['path']
        else:
            return None
    else:
        matching_psfs = [i for i in otflist
            if i['date'] == otflist[minIdx]['date'] and i['form'] == 'psf']
        if matching_psfs:
            # generate new OTF from PSF
            path = matching_psfs[0]['path']
            otf = makeotf(path, lambdanm=int(wave), bDoCleanup=False)

            if os.path.isfile(otf):
                return otf
            else:
                return None


# class OTFbin(CUDAbin):
#   """docstring for MakeOTF"""

#   def __init__(self, binPath=config.__RADIALFT__):
#       super(OTFbin, self).__init__(binPath)

#   def process(self, inpath, **options):
#       cmd = [self.path]
#       outfile = inpath.replace('.tif', '_otf.tif')
#       options.update({
#           'input-file': inpath,
#           'output-file': outfile,
#           'fixorigin': '10',
#           'nocleanup': True,
#       })
#       for o in options:
#           if self.has_option('--' + o):
#               if isinstance(options[o], bool):
#                   cmd.extend(['--' + o])
#               else:
#                   cmd.extend(['--' + o, str(options[o])])
#           else:
#               logging.warn('Warning: option not recognized, ignoring: {}'.format(o))
#       if self._run_command(cmd):
#           return outfile
