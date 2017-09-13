import os
import sys
import stat
import fnmatch
from shutil import copyfile


def pathHasPattern(path, pattern='*Settings.txt'):
    for file in os.listdir(path):
        if fnmatch.fnmatch(file, pattern):
            return True
    return False


def is_libpath(path):
    return (os.path.isdir(path) and
            os.path.basename(path) == 'lib' and
            pathHasPattern(path, 'libcudaDeconv*') and
            pathHasPattern(path, 'libradialft*'))


def is_binpath(path):
    return (os.path.isdir(path) and
            os.path.basename(path) == 'bin' and
            pathHasPattern(path, 'cudaDeconv*'))


def find_libpath(path):
    if is_libpath(path):
        return path
    elif 'lib' in os.listdir(path):
        if is_libpath(os.path.join(path, 'lib')):
            return os.path.join(path, 'lib')
    else:
        for dirpath, dirnames, filenames in os.walk(path):
            for P in dirnames:
                if is_libpath(P):
                    return P
    return None


def find_binpath(path):
    if is_binpath(path):
        return path
    elif 'bin' in os.listdir(path):
        if is_binpath(os.path.join(path, 'bin')):
            return os.path.join(path, 'bin')
    else:
        for dirpath, dirnames, filenames in os.walk(path):
            for P in dirnames:
                if is_binpath(P):
                    return P
    return None


def install(dirpath):
    dirpath = os.path.normpath(os.path.expanduser(dirpath))
    if not os.path.exists(dirpath):
        raise IOError('Could not find path: {}'.format(dirpath))

    ext = {
        'lib': {
            'darwin': '.dylib',
            'win32': '.dll',
            'nix': '.so'
        },
        'bin': {
            'darwin': '.app',
            'win32': '.exe',
            'nix': ''
        }
    }

    if sys.platform.startswith('darwin'):
        PLATFORM = 'darwin'
    elif sys.platform.startswith('win32'):
        PLATFORM = 'win32'
    else:
        PLATFORM = 'nix'

    thispath = os.path.abspath(os.path.dirname(__file__))
    libpath = find_libpath(dirpath)
    binpath = find_binpath(dirpath)

    if libpath:
        dest = os.path.join(thispath, 'lib')
        if not os.path.exists(dest):
            os.mkdir(dest)
        for file in ['libcudaDeconv', 'libradialft']:
            fname = file + ext['lib'][PLATFORM]
            src = os.path.join(libpath, fname)
            if os.path.isfile(src):
                print('Copying {} --> {}'.format(src, os.path.join(dest, fname)))
                copyfile(src, os.path.join(dest, fname))

    if binpath:
        dest = os.path.join(thispath, 'bin')
        if not os.path.exists(dest):
            os.mkdir(dest)
        for file in ['cudaDeconv', 'otfviewer', 'radialft']:
            fname = file + ext['bin'][PLATFORM]
            src = os.path.join(binpath, fname)
            if os.path.isfile(src):
                D = os.path.join(dest, fname)
                print('Copying {} --> {}'.format(src, D))
                copyfile(src, D)
                st = os.stat(D)
                os.chmod(D, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


if __name__ == '__main__':
    try:
        install(sys.argv[1])
    except IndexError:
        print("Please include installation path in command")
