from .exceptions import OTFError
from .util import load_lib
from datetime import datetime, timedelta

import numpy as np
import re
import ctypes
import os
import logging

logger = logging.getLogger(__name__)


try:
    import pathlib as plib

    plib.Path()
except (ImportError, AttributeError):
    import pathlib2 as plib
except (ImportError, AttributeError):
    raise ImportError("no pathlib detected. For python2: pip install pathlib2")


otflib = load_lib("libradialft")

if not otflib:
    logger.error("Could not load libradialft!")
else:
    try:
        shared_makeotf = otflib.makeOTF
        shared_makeotf.restype = ctypes.c_int
        shared_makeotf.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_int,
            ctypes.c_bool,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_int,
            ctypes.c_bool,
        ]
    except AttributeError as e:
        logger.warn("Failed to properly import libradialft")
        logger.error(e)


def requireOTFlib(func, *args, **kwargs):
    def dec(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if not otflib:
                raise Exception(
                    "Could not find libradialft library! OTF generation "
                    "will not be available:"
                )
            else:
                raise e

    return dec


@requireOTFlib
def makeotf(
    psf,
    otf=None,
    lambdanm=520,
    dz=0.102,
    fixorigin=10,
    bUserBackground=False,
    background=90,
    NA=1.25,
    NIMM=1.3,
    dr=0.102,
    krmax=0,
    bDoCleanup=False,
):
    # krmax => "pixels outside this limit will be zeroed (overwriting estimated value from NA and NIMM)")
    if otf is None:
        otf = psf.replace(".tif", "_otf.tif")
    shared_makeotf(
        str.encode(psf),
        str.encode(otf),
        lambdanm,
        dz,
        fixorigin,
        bUserBackground,
        background,
        NA,
        NIMM,
        dr,
        krmax,
        bDoCleanup,
    )
    return otf


# example: 20160825_488_totPSF_mb_0p5-0p42.tif

psffile_pattern = re.compile(
    r"""
    ^(?P<date>\d{6}|\d{8})      # 6 or 8 digit date
    _(?P<wave>\d+)              # wavelength ... only digits following _ are used
    _(?P<slmpattern>[a-zA-Z_]+)  # slm pattern
    _(?P<outerNA>[0-9p.]+)      # outer NA, digits with . or p for decimal
    [-_](?P<innerNA>[0-9p.]+)   # inter NA, digits with . or p for decimal
    (?P<isotf>_otf)?.tif$""",  # optional _otf to specify that it is already an otf
    re.VERBOSE,
)


default_otf_pattern = re.compile(
    r"""
    ^(?P<wave>\d{3})
    (?P<isotf>_otf)?
    (?P<ispsf>_psf)?.tif$""",
    re.VERBOSE,
)


def dir_has_otfs(dirname):
    if os.path.isdir(str(dirname)):
        if any(
            [
                (psffile_pattern.search(t) or default_otf_pattern.search(t))
                for t in os.listdir(dirname)
            ]
        ):
            return True
    return False


def get_otf_dict(otfdir):
    """ The otf_dict is a dict with
    """
    otf_dict = {}
    otfdir = plib.Path(otfdir)

    for t in otfdir.glob("*tif"):
        M = psffile_pattern.search(str(t.name))
        if M:
            M = M.groupdict()
            wave = int(M["wave"])
            if wave not in otf_dict:
                otf_dict[wave] = {"default": None}
            mask = (
                float(M["innerNA"].replace("p", ".")),
                float(M["outerNA"].replace("p", ".")),
            )
            if mask not in otf_dict[wave]:
                otf_dict[wave][mask] = []
            if not M["isotf"]:
                matching_otf = otfdir.joinpath(t.name.replace(".tif", "_otf.tif"))
                if not matching_otf.is_file():
                    matching_otf = None
                else:
                    matching_otf = matching_otf
            else:
                matching_otf = None
            otf_dict[wave][mask].append(
                {
                    "date": datetime.strptime(M["date"], "%Y%m%d"),
                    "path": str(t),
                    "form": "otf" if M["isotf"] else "psf",
                    "slm": M["slmpattern"],
                    "otf": str(matching_otf),
                }
            )
        else:
            pathname = str(t.name)
            M = default_otf_pattern.search(pathname)
            if M:
                M = M.groupdict()
                wave = int(M["wave"])
                if wave not in otf_dict:
                    otf_dict[wave] = {}
                if not M["isotf"]:
                    newname = str(t).replace(".tif", "_otf.tif")
                    if M["ispsf"]:
                        newname = newname.replace("_psf", "")
                    pathname = newname
                    if not os.path.exists(newname):
                        makeotf(str(t), newname, lambdanm=int(wave), bDoCleanup=False)
                otf_dict[wave]["default"] = str(otfdir.joinpath(pathname))
    for wave in otf_dict.keys():
        logger.debug("OTFdict wave: {}, masks: {}".format(wave, otf_dict[wave].keys()))
    return otf_dict


def get_default_otf(wave, otfpath, approximate=True):
    origwave = wave
    otf_dict = get_otf_dict(otfpath)
    waves_with_defaults = [k for k, v in otf_dict.items() if v["default"] is not None]
    if wave not in waves_with_defaults:
        if approximate:
            for newwave in range(wave - 8, wave + 9):
                if newwave in waves_with_defaults:
                    wave = newwave
    if wave in otf_dict:
        return otf_dict[wave]["default"]
    else:
        raise OTFError("No default OTF found for wavelength {}".format(origwave))


def choose_otf(
    wave, otfpath, date=None, mask=None, direction="nearest", approximate=True
):
    """return otf with date closest to requested date.
    if OTF doesn't exist, but PSF does, generate OTF and return the path.i
    direction can be {'nearest', 'before', 'after'}, where 'before' returns an
    OTF that was collected before 'date' and 'after' returns one that was
    collected after 'date.'
    """
    if not dir_has_otfs(otfpath):
        raise OTFError("Not a valid OTF path: {}".format(otfpath))
    if not date:
        date = datetime.now()

    otf_dict = get_otf_dict(otfpath)
    otflist = []

    # if the exact wavelenght is not matched, look for similar wavelengths...
    if wave not in otf_dict:
        if approximate:
            for newwave in range(wave - 8, wave + 9):
                if newwave in otf_dict:
                    wave = newwave
                    break
        else:
            return None
    if wave not in otf_dict:
        return None

    # if the mask has been provided, use the OTFs from that mask
    if mask is not None and mask in otf_dict[wave]:
        otflist = otf_dict[wave][mask]

    # if still empty, just return the default
    if not len(otflist):
        return get_default_otf(wave, otfpath, approximate)

    if direction == "nearest":
        minIdx = np.argmin([np.abs(i["date"] - date) for i in otflist])
    elif direction == "before":
        deltas = [date - i["date"] for i in otflist]
        test = [d > timedelta(minutes=0) for d in deltas]
        minIdx = next((obj for obj in test if obj), None)
    elif direction == "after":
        deltas = [i["date"] - date for i in otflist]
        test = [d > timedelta(minutes=0) for d in deltas]
        minIdx = next((obj for obj in test if obj), None)
    else:
        raise ValueError("Unkown direction argument: {}".format(direction))

    if minIdx is None:
        return get_default_otf(wave, otfpath, approximate)

    matching_otfs = [
        i
        for i in otflist
        if i["date"] == otflist[minIdx]["date"] and i["form"] == "otf"
    ]
    if len(matching_otfs):
        return matching_otfs[0]["path"]
    else:
        matching_psfs = [
            i
            for i in otflist
            if i["date"] == otflist[minIdx]["date"] and i["form"] == "psf"
        ]
        if matching_psfs:
            # generate new OTF from PSF
            return makeotf(
                matching_psfs[0]["path"], lambdanm=int(wave), bDoCleanup=False
            )

    return get_default_otf(wave, otfpath, approximate)
