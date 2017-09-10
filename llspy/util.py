import os
import sys
import fnmatch
import warnings
import tifffile
import numpy as np
import json

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __dir__(self):
        return self.keys()


def pathHasPattern(path, pattern='*Settings.txt'):
    for file in os.listdir(path):
        if fnmatch.fnmatch(file, pattern):
            return True
    return False


def find_filepattern(path, filepattern='*.tar*'):
    for file in os.listdir(path):
        if fnmatch.fnmatch(file, filepattern):
            return os.path.join(path, file)
    return None


def imread(*args, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return tifffile.imread(*args, **kwargs)


def getfoldersize(folder, recurse=False):
    if recurse:
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(folder):
            for f in filenames:
                total_size += os.path.getsize(os.path.join(dirpath, f))
        return total_size
    else:
        return sum(os.path.getsize(os.path.join(folder, f))
                for f in os.listdir(folder))


def format_size(size):
    """Return file size as string from byte size."""
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'):
        if size < 2048:
            return "%.f %s" % (size, unit)
        size /= 1024.0


def which(program):
    """Check if program is exectuable.  Return path to bin if so"""
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    if sys.platform.startswith('win32') and not program.endswith('.exe'):
        return which(program + ".exe")
    return None


def isexecutable(fpath):
    if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
        return 1
    else:
        return 0


def walklevel(some_dir, level=1):
    some_dir = some_dir.rstrip(os.path.sep)
    assert os.path.isdir(some_dir)
    num_sep = some_dir.count(os.path.sep)
    for root, dirs, files in os.walk(some_dir):
        yield root, dirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + level <= num_sep_this:
            del dirs[:]


def get_subfolders_containing_filepattern(dirname, filepattern='*Settings.txt',
                                          exclude=['Corrected'], level=1):
    """retrieve a list of subdirectories of the input directory that contain a
    filepattern... useful for getting raw data directories for batch processing
    """
    matches = []
    for root, dirnames, filenames in walklevel(dirname, level):
        for filename in fnmatch.filter(filenames, filepattern):
            if not any([e in root for e in exclude]):
                matches.append(root)
    return matches


def pyrange_to_perlregex(it, digits=4):
    L = []
    for i in it:
        L.append(str(i).zfill(digits))
    return str("(" + "|".join(L) + ")")


def reorderstack(arr, inorder, outorder='tzcyx'):
    """rearrange order of array, used when resaving a file."""
    inorder = inorder.lower()
    for _ in range(len(outorder) - arr.ndim):
        arr = np.expand_dims(arr, 0)
    for i in outorder:
        if i not in inorder:
            inorder = i + inorder
    arr = np.transpose(arr, [inorder.find(n) for n in outorder])
    return arr


def imsave(arr, outpath, dx=1, dz=1, dt=1, unit='micron'):
    """sample wrapper for tifffile.imsave imagej=True."""
    # array must be in TZCYX order
    md = {
        'unit': unit,
        'spacing': dz,
        'finterval': dt,
        'hyperstack': 'true',
        'mode': 'composite',
        'loop': 'true',
    }
    bigT = True if arr.nbytes > 3758096384 else False  # > 3.5GB make a bigTiff
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tifffile.imsave(outpath, arr, bigtiff=bigT, imagej=True,
                        resolution=(1 / dx, 1 / dx), metadata=md)


def getAbsoluteResourcePath(relativePath):
    """ Load relative path, in an environment agnostic way"""
    import sys

    try:
        # PyInstaller stores data files in a tmp folder refered to as _MEIPASS
        basePath = sys._MEIPASS
    except Exception:
        # If not running as a PyInstaller created binary, try to find the data file as
        # an installed Python egg
        try:
            basePath = os.path.dirname(sys.modules['llspy'].__file__)
        except Exception:
            basePath = ''

        # If the egg path does not exist, assume we're running as non-packaged
        if not os.path.exists(os.path.join(basePath, relativePath)):
            basePath = 'llspy'

    path = os.path.join(basePath, relativePath)
    # If the path still doesn't exist, this function won't help you
    if not os.path.exists(path):
        return None

    return path


def shortname(path, parents=2):
    return os.path.sep.join(os.path.normpath(path).split(os.path.sep)[-parents:])


class paramEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, range):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def readHDF5(filename):
    import h5py
    f = h5py.File(filename, 'r')
    return f['data'].value


def readHDF5Frame(filename, frame):
    import h5py
    f = h5py.File(filename, 'r')
    return f['data'][frame]


def writeHDF5(filename, data):
    import h5py
    f = h5py.File(filename, 'w')
    f['data'] = data
    f.flush()
    f.close()

