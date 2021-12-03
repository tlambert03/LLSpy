import fnmatch
import os
import stat
import sys
import zipfile
from shutil import copyfile

HERE = os.path.abspath(os.path.dirname(__file__))
CONDA_PREFIX = os.environ.get("CONDA_PREFIX", False)

if sys.platform.startswith("darwin"):
    PLATFORM = "darwin"
elif sys.platform.startswith("win32"):
    PLATFORM = "win32"
else:
    PLATFORM = "linux"

ext = {
    "lib": {"darwin": ".dylib", "win32": ".dll", "nix": ".so"},
    "bin": {"darwin": "", "win32": ".exe", "nix": ""},
}


def pathHasPattern(path, pattern="*Settings.txt"):
    for file in os.listdir(path):
        if fnmatch.fnmatch(file, pattern):
            return True
    return False


def is_libpath(path):
    return (
        os.path.isdir(path)
        and os.path.basename(path) == "lib"
        and pathHasPattern(path, "libcudaDeconv*")
    )


def is_binpath(path):
    return (
        os.path.isdir(path)
        and os.path.basename(path) == "bin"
        and pathHasPattern(path, "cudaDeconv*")
    )


def find_libpath(path):
    if is_libpath(path):
        return path
    if os.path.exists(os.path.join(path, PLATFORM)):
        path = os.path.join(path, PLATFORM)
    elif os.path.exists(os.path.join(path, "llspy_extra", PLATFORM)):
        path = os.path.join(path, "llspy_extra", PLATFORM)
    else:
        return None
    if "lib" in os.listdir(path):
        if is_libpath(os.path.join(path, "lib")):
            return os.path.join(path, "lib")
    else:
        for dirpath, dirnames, filenames in os.walk(path):
            for P in dirnames:
                if is_libpath(P):
                    return P
    return None


def find_binpath(path):
    if is_binpath(path):
        return path
    if os.path.exists(os.path.join(path, PLATFORM)):
        path = os.path.join(path, PLATFORM)
    elif os.path.exists(os.path.join(path, "llspy_extra", PLATFORM)):
        path = os.path.join(path, "llspy_extra", PLATFORM)
    else:
        return None
    if "bin" in os.listdir(path):
        if is_binpath(os.path.join(path, "bin")):
            return os.path.join(path, "bin")
    else:
        for dirpath, dirnames, filenames in os.walk(path):
            for P in dirnames:
                if is_binpath(P):
                    return P
    return None


def install(dirpath, dryrun=False):
    dirpath = os.path.normpath(os.path.expanduser(dirpath))
    if not os.path.exists(dirpath):
        raise OSError(f"Could not find path: {dirpath}")

    if zipfile.is_zipfile(dirpath):
        import tempfile

        with tempfile.TemporaryDirectory() as tempdir:
            basename = os.path.splitext(os.path.basename(dirpath))[0]
            Z = zipfile.ZipFile(dirpath)
            Z.extractall(path=tempdir)
            extractedpath = os.path.join(tempdir, basename)
            if os.path.isdir(extractedpath):
                install(extractedpath)
            else:
                print("Failed to install llspy_extra zipfile")
        return

    libpath = find_libpath(dirpath)
    binpath = find_binpath(dirpath)

    if CONDA_PREFIX and CONDA_PREFIX != "":
        print(
            "Conda environment detected: {}".format(
                os.environ.get("CONDA_DEFAULT_ENV", "?")
            )
        )
        if PLATFORM == "win32":
            destlib = os.path.join(CONDA_PREFIX, "Library", "bin")
            destbin = os.path.join(CONDA_PREFIX, "Library", "bin")
        else:
            destlib = os.path.join(CONDA_PREFIX, "lib")
            destbin = os.path.join(CONDA_PREFIX, "bin")
    else:
        print("This installer only works in an active conda environment.")
        return

    if dryrun:
        print("DRY RUN: files that would be copied...")
    else:
        print("Installing files...")

    if libpath:
        if not os.path.exists(destlib) and not dryrun:
            os.mkdir(destlib)
        for file in os.listdir(libpath):
            if file.startswith("."):
                continue
            src = os.path.join(libpath, file)
            D = os.path.join(destlib, file)
            print(f"{os.path.basename(src):>22} --> {D}")
            if not dryrun:
                if os.path.exists(D):
                    os.remove(D)
                copyfile(src, D)

    if binpath:
        if not os.path.exists(destbin) and not dryrun:
            os.mkdir(destbin)
        for file in os.listdir(binpath):
            if file.startswith("."):
                continue
            src = os.path.join(binpath, file)
            D = os.path.join(destbin, file)
            print(f"{os.path.basename(src):>22} --> {D}")
            if not dryrun:
                if os.path.exists(D):
                    try:
                        os.remove(D)
                    except PermissionError:
                        print(
                            "Permission Error: you must manually remove or replace this file: {}".format(
                                D
                            )
                        )
                        continue
                copyfile(src, D)
                st = os.stat(D)
                os.chmod(D, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


if __name__ == "__main__":
    try:
        install(sys.argv[1])
    except IndexError:
        print("Please include path to llspy_extra in command")
