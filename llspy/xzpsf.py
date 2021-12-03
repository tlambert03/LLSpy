#! /usr/bin/env python

import fnmatch
import os
import re
import warnings

import numpy as np
import tifffile as tf
from scipy.ndimage.filters import gaussian_filter


def main(infile, nx, nz, sig=1, pad=12):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            indat = tf.imread(infile)
    except OSError:
        print("File %s does not exist or is no readable.\n Quit" % infile)
        return

    mip = indat.max(0)
    mipblur = gaussian_filter(mip, sig)
    maxy, maxx = np.argwhere(mipblur == mipblur.max())[0]
    print(f"bead detected at ({maxx},{maxy})")

    beadslice = indat[:, maxy - pad : maxy + pad, maxx - pad : maxx + pad].astype(
        np.float
    )
    background = indat[:, :, 2].mean(1)
    beadsums = beadslice.sum((1, 2)) - (
        4 * pad * pad * background
    )  # subtract background
    xzpsf = np.reshape(beadsums, (int(nz), int(nx))).astype(np.float32)
    tf.imsave(infile.replace(".tif", "xzPSF_x%d_y%d.tif" % (maxx, maxy)), xzpsf)
    return xzpsf


# this functionality is duplicated from settingstxt.py to allow this file
# to function independently of the rest of the package
def get_nXnZ(settings):
    with open(settings, encoding="utf-8") as f:
        raw_text = f.read()

    waveform_pattern = re.compile(
        r"""
        ^(?P<waveform>.*)\sOffset,	# Waveform type, newline followed by description
        .*\((?P<channel>\d+)\)\s	# get channel number inside of parentheses
        :\s*(?P<offset>[-\d]*\.?\d*)	# float offset value after colon
        \s*(?P<interval>[-\d]*\.?\d*)	# float interval value next
        \s*(?P<numpix>\d+)			# integer number of pixels last
        """,
        re.MULTILINE | re.VERBOSE,
    )

    acq_mode = re.search("Acq Mode\\s*:\\s*(.*)\n", raw_text).group(1)
    if not acq_mode == "XZ PSF":
        warnings.warn("Settings.txt acquisition mode was NOT XZ PSF")

    waveforms = [m.groupdict() for m in waveform_pattern.finditer(raw_text)]

    channel = {}
    for item in waveforms:
        cnum = int(item.pop("channel"))
        if cnum not in channel:
            channel[cnum] = {}
        wavename = item.pop("waveform")
        channel[cnum][wavename] = item

    nx = int(channel[0]["X Galvo"]["numpix"])
    nz = int(channel[0]["Z Galvo"]["numpix"])
    return (nx, nz)


def find_settext(path, filepattern="*Settings.txt"):
    for file in os.listdir(path):
        if fnmatch.fnmatch(file, filepattern):
            return os.path.join(path, file)
    return None


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    arg = parser.add_argument
    arg("path", help="file or folder to process")
    arg(
        "-x",
        "--nx",
        type=int,
        default=None,
        help="number of X pixels (default is to autodetect from settings.txt)",
    )
    arg(
        "-z",
        "--nz",
        type=int,
        default=None,
        help="number of Z pixels (default is to autodetect from settings.txt)",
    )
    arg(
        "-s",
        "--settings",
        type=str,
        default=None,
        help="optional path to settings.txt (default is to autodetect)",
    )
    arg(
        "-a",
        "--sigma",
        type=float,
        default=1,
        help="sigma for gaussian filter during bead detection, (default=1)",
    )
    arg(
        "-p",
        "--pad",
        type=int,
        default=4,
        help="number of pixels on either side of maximum to include in beadsum,"
        " (default=4)",
    )

    args = parser.parse_args()

    path = os.path.abspath(args.path)
    sig = int(args.sigma)
    pad = int(args.pad)

    if not (args.nx and args.nz):
        if os.path.isdir(path):
            settext = find_settext(path)
        elif os.path.isfile(path):
            settext = find_settext(os.path.dirname(path))

        if settext is not None:
            nx, nz = get_nXnZ(settext)
            print(f"nX: {nx}, nZ: {nz}, detected from settings.txt")
        else:
            print("Could not find settings file, must input values")
            nx = int(input("number of X pixels = "))
            nz = int(input("number of Z pixels = "))
    else:
        nx = int(args.nx)
        nz = int(args.nz)

    if nx <= 0 or nz <= 0:
        raise ValueError("Must provide nX and nZ > 0")

        # if a directory is provided, do it to each file
    if os.path.isdir(path):
        for file in os.listdir(path):
            if fnmatch.fnmatch(file, "*.tif") and "xzPSF" not in file:
                print(f"processing {file}: ", end="")
                try:
                    main(os.path.join(path, file), nx, nz, sig=sig, pad=pad)
                except Exception as e:
                    print(f"ERROR: {e} ... skipping")

    elif os.path.isfile(path):
        main(path, nx, nz, sig=sig, pad=pad)
    else:
        raise OSError("Path must be an existing file or directory")
