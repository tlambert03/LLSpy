import datetime
import glob
import json
import logging
import os
import pprint
import re
import shutil
import sys
import time
import warnings
from multiprocessing import Pool, cpu_count

import numpy as np
import tifffile as tf

from llspy.libcudawrapper import affineGPU, deskewGPU, quickDecon
from parse import parse as _parse

from . import arrayfun, compress, config
from . import otf as otfmodule
from . import parse, schema, util
from .camera import CameraParameters, selectiveMedianFilter
from .cudabinwrapper import CUDAbin
from .exceptions import LLSpyError, OTFError
from .settingstxt import LLSsettings

try:
    from fiducialreg.fiducialreg import CloudSet, RegFile, RegistrationError
except ImportError:
    thisDirectory = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(thisDirectory, os.pardir))
    from fiducialreg.fiducialreg import CloudSet, RegFile, RegistrationError

try:
    import pathlib as plib

    plib.Path()
except (ImportError, AttributeError):
    import pathlib2 as plib
except (ImportError, AttributeError):
    raise ImportError("no pathlib detected. For python2: pip install pathlib2")


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

np.seterr(divide="ignore", invalid="ignore")

# this is for multiprocessing with pyinstaller on windows
# https://github.com/pyinstaller/pyinstaller/wiki/Recipe-Multiprocessing
try:
    # Python 3.4+
    if sys.platform.startswith("win"):
        import multiprocessing.popen_spawn_win32 as forking
    else:
        import multiprocessing.popen_fork as forking
except ImportError:
    import multiprocessing.forking as forking

if sys.platform.startswith("win"):
    # First define a modified version of Popen.
    class _Popen(forking.Popen):
        def __init__(self, *args, **kw):
            if hasattr(sys, "frozen"):
                # We have to set original _MEIPASS2 value from sys._MEIPASS
                # to get --onefile mode working.
                os.putenv("_MEIPASS2", sys._MEIPASS)
            try:
                super().__init__(*args, **kw)
            finally:
                if hasattr(sys, "frozen"):
                    # On some platforms (e.g. AIX) 'os.unsetenv()' is not
                    # available. In those cases we cannot delete the variable
                    # but only set it to the empty string. The bootloader
                    # can handle this case.
                    if hasattr(os, "unsetenv"):
                        os.unsetenv("_MEIPASS2")
                    else:
                        os.putenv("_MEIPASS2", "")

    # Second override 'Popen' class with our modified version.
    forking.Popen = _Popen


__FPATTERN__ = "{basename}_ch{channel:d}_stack{stack:d}_{wave:d}nm_{reltime:d}msec_{abstime:d}msecAbs{}"


def correctTimepoint(
    fnames,
    camparams,
    outpath,
    medianFilter,
    trimZ,
    trimY,
    trimX,
    flashCorrectTarget="cpu",
):
    """accepts a list of filenames (fnames) that represent Z stacks that have
    been acquired in an interleaved manner (i.e. ch1z1,ch2z1,ch1z2,ch2z2...)
    """
    stacks = [util.imread(f) for f in fnames]
    outstacks = camparams.correct_stacks(
        stacks, medianFilter, (trimZ, trimY, trimX), flashCorrectTarget
    )
    outnames = [
        str(outpath.joinpath(os.path.basename(str(f).replace(".tif", "_COR.tif"))))
        for f in fnames
    ]
    for n in range(len(outstacks)):
        util.imsave(util.reorderstack(np.squeeze(outstacks[n]), "zyx"), outnames[n])


def unwrapper(tup):
    return correctTimepoint(*tup)


def filter_stack(filename, outname, dx, background, trim, medianFilter):
    stack = util.imread(filename)
    if medianFilter:
        stack, _ = selectiveMedianFilter(stack, background)
    if any([any(i) for i in trim]):
        stack = arrayfun.trimedges(stack, trim)
    util.imsave(util.reorderstack(np.squeeze(stack), "zyx"), outname, dx=dx, dz=1)


def unbundle(group):
    return filter_stack(*group)


def move_corrected(path):
    parent = os.path.dirname(path)
    for d in ["GPUdecon", "Deskewed", "CPPdecon"]:
        subd = os.path.join(path, d)
        if os.path.exists(subd):
            target = os.path.join(parent, d)
            shutil.rmtree(target, ignore_errors=True)
            t = 0
            while os.path.exists(subd):
                try:
                    shutil.move(subd, target)
                except Exception:
                    if t > 4:
                        break
                    time.sleep(0.5)
                    t += 1


def get_regObj(regCalibPath):
    """Detect whether provided path is a directory of tiffs with fiducials or
    a pre-calibrated registration file"""
    refObj = None
    if os.path.isfile(regCalibPath) and regCalibPath.endswith(
        (".reg", ".txt", ".json")
    ):
        refObj = RegFile(regCalibPath)
        if not refObj.n_tforms > 0:
            raise RegistrationError(f"No transforms found in file: {regCalibPath}")
        logger.debug("RegCalib Path detected as registration file")
    elif os.path.isdir(regCalibPath):  # path must be raw fidicial dataset
        refObj = RegDir(regCalibPath)
        if not refObj.isValid:
            mes = """
                  Not a valid registration calibration dataset: {path}\n\n
                  Registration requires a folder of multi-channel fiducial marker
                  tiff files, as well as a settings.txt file
                  """
            raise RegistrationError(mes.format(path=regCalibPath))
        logger.debug("RegCalib Path detected as fiducial dataset")
    return refObj


def register_folder(
    folder, regRefWave, regMode, regObj, voxsize=[1, 1, 1], discard=False
):
    """Register all (non-reference) wavelengths in a folder to the specified
    reference wavelength, using the provided regObj.

    voxsize must be an array of pixel sizes [dz, dy, dx]
    """
    if isinstance(regObj, str):
        regObj = get_regObj(regObj)
    folder = str(folder)

    global __FPATTERN__

    # get all tiffs in folders
    files = parse.filter_w(os.listdir(folder), regRefWave, exclusive=True)
    files = [f for f in files if (f.endswith(".tif") and "_REG" not in f)]
    for F in files:
        fname = os.path.join(folder, F)
        outname = fname.replace(".tif", f"_REG{regRefWave}.tif")
        imarray = util.imread(fname)
        imwave = parse.parse_filename(fname, "wave", pattern=__FPATTERN__)
        im_out = register_image_to_wave(
            imarray, regObj, imwave, regRefWave, mode=regMode, voxsize=voxsize
        ).astype(imarray.dtype)
        util.imsave(
            util.reorderstack(np.squeeze(im_out), "zyx"),
            outname,
            dx=voxsize[2],
            dz=voxsize[0],
        )
        if discard:
            os.remove(os.path.join(folder, F))

    # rename refwave files too
    for F in parse.filter_w(os.listdir(folder), regRefWave, exclusive=False):
        fname = os.path.join(folder, F)
        outname = fname.replace(".tif", f"_REG{regRefWave}.tif")
        os.rename(fname, outname)


def register_image_to_wave(
    img, regCalibObj, imwave=None, refwave=488, voxsize=None, mode="2step"
):
    # voxsize must be an array of pixel sizes [dz, dy, dx]

    global __FPATTERN__

    if not isinstance(regCalibObj, (RegDir, RegFile)):
        raise RegistrationError(
            "Calibration object for register_image_to_wave "
            "must be either RegDir or RegFile.  Received: %s" % str(type(regCalibObj))
        )

    if isinstance(img, np.ndarray):
        if imwave is None:
            raise ValueError(
                "Must provide wavelength when providing array " "for registration."
            )
    elif isinstance(img, str) and os.path.isfile(img):
        if imwave is None:
            try:
                imwave = parse.parse_filename(img, "wave", pattern=__FPATTERN__)
            except Exception:
                pass
            if not imwave:
                raise ValueError("Could not detect image wavelength.")
        img = util.imread(img)
    else:
        raise ValueError(
            "Input to Registration must either be a np.array " "or a path to a tif file"
        )

    tform = regCalibObj.get_tform(imwave, refwave, mode)
    inv_tform = np.linalg.inv(tform)
    return affineGPU(img, inv_tform, voxsize)


def preview(exp, tR=0, cR=None, **kwargs):
    """Process LLS experiment, without file IO.

    Args:
        exp (:obj:`str`, LLSdir): path to LLS experiment or LLSdir instance
        tR (:obj:`int`, Iterable[:obj:`int`], optional): Time points to process (zero indexed)
        cR (:obj:`int`, Iterable[:obj:`int`], optional): Channels to process (zero indexed)

        **kwargs: any keyword arguments that are recognized by the LLS `Schema list`_.

    Returns:
        :obj:`np.ndarray`: numpy array of processed data (3D-5D, depending on input)


    """
    if not isinstance(exp, LLSdir):
        if isinstance(exp, str):
            exp = LLSdir(exp)
    logger.debug(f"Preview called on {str(exp.path)}")
    logger.debug(f"Params: {exp.parameters}")

    if exp.is_compressed():
        try:
            exp.decompress_partial(tRange=tR)
        except Exception as e:
            logger.error("ERROR: could not do partial decompression...")
            logger.error(str(e))
            exp.decompress()

    if not exp.ready_to_process:
        if not exp.has_lls_tiffs:
            logger.warning(f"No TIFF files to process in {exp.path}")
            return
        # if not exp.has_settings:
        #     logger.warning('Could not find Settings.txt file in {}'.format(exp.path))
        #     return

    kwargs["tRange"] = tR
    kwargs["cRange"] = cR
    P = exp.localParams(**kwargs)

    if P.correctFlash and not hasattr(exp, "settings"):
        P.correctFlash = False
        logger.warning("Cannot perform Flash Correction without settings.txt file")

    out = []
    for timepoint in P.tRange:
        stacks = [util.imread(f) for f in exp.get_files(c=P.cRange, t=timepoint)]
        if not stacks:
            continue
        # logger.debug("shape_raw: {}".format(stacks[0].shape))
        if P.correctFlash:
            camparams = CameraParameters(P.camparamsPath)
            camparams = camparams.get_subroi(exp.settings.camera.roi)
            stacks = camparams.correct_stacks(
                stacks, trim=(P.trimZ, P.trimY, P.trimX), medianFilter=P.medianFilter
            )
        else:
            # camera correction trims edges, so if we aren't doing the camera correction
            # we need to call the edge trim on our own
            if any([any(i) for i in (P.trimZ, P.trimY, P.trimX)]):
                stacks = [
                    arrayfun.trimedges(s, (P.trimZ, P.trimY, P.trimX)) for s in stacks
                ]
            # camera correction also does background subtraction
            # so otherwise trigger it manually here
            stacks = [
                arrayfun.sub_background(s, b) for s, b in zip(stacks, P.background)
            ]

        # FIXME: background is the only thing keeping this from just **P to deconvolve
        if P.nIters > 0:
            opts = {
                "nIters": P.nIters,
                "drdata": P.drdata,
                "dzdata": P.dzdata,
                "deskew": P.deskew,
                "rotate": P.rotate,
                "width": P.width,
                "shift": P.shift,
                "background": 0,  # zero here because it's already been subtracted above
            }
            for i, d in enumerate(zip(stacks, P.otfs)):
                stk, otf = d
                stacks[i] = quickDecon(stk, otf, **opts)
        else:
            # deconvolution does deskewing and cropping, so we do it here if we're
            #
            if P.deskew:
                stacks = [deskewGPU(s, P.dzdata, P.drdata, P.deskew) for s in stacks]
            stacks = [arrayfun.cropX(s, P.width, P.shift) for s in stacks]

        # FIXME: this is going to be slow until we cache the tform Matrix results
        if P.doReg:
            if P.regCalibPath is None:
                logger.error(
                    "Skipping Registration: no Calibration Object path provided"
                )
            else:
                refObj = get_regObj(P.regCalibPath)
                if isinstance(refObj, (RegDir, RegFile)) and refObj.isValid:
                    voxsize = [
                        exp.parameters.dzFinal,
                        exp.parameters.dx,
                        exp.parameters.dx,
                    ]
                    for i, d in enumerate(zip(stacks, P.wavelength)):
                        stk, wave = d
                        if not wave == P.regRefWave:  # don't reg the reference channel
                            stacks[i] = register_image_to_wave(
                                stk,
                                refObj,
                                imwave=wave,
                                refwave=P.regRefWave,
                                mode=P.regMode,
                                voxsize=voxsize,
                            )
                else:
                    logger.error(
                        "Registration Calibration dir not valid"
                        "{}".format(P.regCalibPath)
                    )

        out.append(np.stack(stacks, 0))

    if out:
        combined = np.stack(out, 0) if len(out) > 1 else out[0]
        logger.debug(f"Preview finished. Output array shape = {combined.shape}")
        return combined
    else:
        logger.warning("Preview returned an empty array")
        return None


def process(exp, binary=None, **kwargs):
    """Process LLS experiment with cudaDeconv, output results to file.

    Args:
        exp (:obj:`str`, LLSdir): path to LLS experiment or LLSdir instance
        binary (:obj:`str`, optional): specify path to cudaDeconv binary, otherwise
            gets default bundled binary (if present).

        **kwargs: any keyword arguments that are recognized by the LLS `Schema list`_.

    Returns:
        None:  Files are written to disk.
    """

    if not isinstance(exp, LLSdir):
        if isinstance(exp, str):
            exp = LLSdir(exp)
    logger.debug(f"Process called on {str(exp.path)}")
    logger.debug(f"Params: {exp.parameters}")

    if exp.is_compressed():
        exp.decompress()

    if not exp.ready_to_process:
        if not exp.has_lls_tiffs:
            logger.warning(f"No TIFF files to process in {exp.path}")
        if not exp.parameters.isReady():
            logger.warning(f"Parameters are not valid: {exp.path}")
        return

    P = exp.localParams(**kwargs)

    if binary is None:
        binary = CUDAbin()

    if P.correctFlash:
        exp.path = exp.correct_flash(**P)
    elif P.medianFilter or any([any(i) for i in (P.trimX, P.trimY, P.trimZ)]):
        exp.path = exp.median_and_trim(**P)

    if P.nIters > 0 or P.saveDeskewedRaw or P.rotate:
        for chan in P.cRange:
            opts = {
                "background": P.background[chan] if not P.correctFlash else 0,
                "drdata": P.drdata,
                "dzdata": P.dzdata,
                "wavelength": float(P.wavelength[chan]) / 1000,
                "deskew": P.deskew,
                "saveDeskewedRaw": P.saveDeskewedRaw,
                "MIP": P.MIP,
                "rMIP": P.rMIP,
                "uint16": P.uint16,
                "bleachCorrection": P.bleachCorrection,
                "RL": P.nIters,
                "rotate": P.rotate,
                "width": P.width,
                "shift": P.shift,
                # 'quiet': bool(quiet),
                # 'verbose': bool(verbose),
            }

            # filter by channel and trange
            if (
                len(list(P.tRange)) == exp.parameters.nt
            ):  # processing all the timepoints
                filepattern = f"ch{chan}_"
            else:
                filepattern = "ch{}_stack{}".format(
                    chan, util.pyrange_to_perlregex(P.tRange)
                )

            binary.process(str(exp.path), filepattern, P.otfs[chan], **opts)

        # if verbose:
        #   logger.info(response.output.decode('utf-8'))

    # FIXME: this is just a messy first try...
    if P.doReg:
        exp.register(P.regRefWave, P.regMode, P.regCalibPath, P.deleteUnregistered)

    if P.mergeMIPs:
        exp.mergemips()

    # if P.mergeMIPsraw:
    #   if exp.path.joinpath('Deskewed').is_dir():
    #       exp.mergemips('Deskewed')

    # if we did camera correction, move the resulting processed folders to
    # the parent folder, and optionally delete the corrected folder
    if P.moveCorrected and exp.path.name == "Corrected":
        move_corrected(str(exp.path))
        exp.path = exp.path.parent

    if not P.keepCorrected:
        shutil.rmtree(str(exp.path.joinpath("Corrected")), ignore_errors=True)

    if P.compressRaw:
        exp.compress()

    if P.writeLog:
        outname = str(exp.path.joinpath(f"{exp.basename}_{config.__OUTPUTLOG__}"))
        with open(outname, "w") as outfile:
            json.dump(P, outfile, cls=util.paramEncoder)

    logger.debug("Process func finished.")
    return


def mergemips(folder, axis, write=True, dx=1, dt=1, delete=True, fpattern=None):
    """combine folder of MIPs into a single multi-channel time stack.
    return dict with keys= axes(x,y,z) and values = numpy array
    """
    if not fpattern:
        global __FPATTERN__
        fpattern = __FPATTERN__
    folder = plib.Path(folder)
    if not folder.is_dir():
        raise OSError(f"MIP folder does not exist: {str(folder)}")

    try:
        filelist = []
        tiffs = []
        channelCounts = []
        c = 0
        while True:
            channelFiles = sorted(folder.glob(f"*ch{c}_*MIP_{axis}.tif"))
            if not len(channelFiles):
                break  # no MIPs in this channel
                # this assumes that there are no gaps in the channels (i.e. ch1, ch3 but not 2)
            for file in channelFiles:
                tiffs.append(tf.imread(str(file)))
                filelist.append(file)
            channelCounts.append(len(channelFiles))
            c += 1
        if not len(filelist):
            return None  # there were no MIPs for this axis
        if c > 0:
            nt = np.max(channelCounts)

            if len(set(channelCounts)) > 1:
                raise ValueError(
                    "Cannot merge MIPS with different number of "
                    "timepoints per channel"
                )
            if len(tiffs) != c * nt:
                raise ValueError("Number of images does not equal nC * nT")

            stack = np.stack(tiffs)
            stack = stack.reshape((c, 1, nt, stack.shape[-2], stack.shape[-1]))  # TZCYX
            stack = np.transpose(stack, (2, 1, 0, 3, 4))

        if write:
            # FIXME: this is getting ugly
            basename = parse.parse_filename(
                str(filelist[0]), "basename", pattern=fpattern
            )
            cor = "_COR" if "_COR" in str(filelist[0]) else ""
            axis = str(filelist[0]).split("MIP_")[1][0]
            _, ext = os.path.splitext(filelist[0])
            if "decon" in str(folder).lower():
                miptype = "_decon_"
            elif "deskewed" in str(folder).lower():
                miptype = "_deskewed_"
            else:
                miptype = "_"
            outname = basename + cor + miptype + "comboMIP_" + axis + ext
            util.imsave(stack, str(folder.joinpath(outname)), dx=dx, dt=dt)

        if delete:
            [file.unlink() for file in filelist if "comboMIP" not in str(file)]

        return stack

    except ValueError as e:
        logger.error(f"ERROR: failed to merge MIPs from {str(folder)}: ")
        logger.error(f"{e}")


class CoreParams(dict):
    """dot.notation access to dictionary attributes"""

    def __init__(self, *args, **kwargs):
        self["samplescan"] = False
        self["dzFinal"] = 0
        self["dz"] = 0
        self["angle"] = None

        super().__init__(*args, **kwargs)

    def __getattr__(self, name):
        return self.get(name)

    def __setattr__(self, name, value):
        return self.__setitem__(name, value)

    def __setitem__(self, name, value):
        super().__setitem__(name, value)
        if name == "angle" and value is not None:
            if value == 0:
                super().__setitem__("samplescan", False)
            else:
                super().__setitem__("samplescan", True)
        if name == "samplescan":
            if not value:
                super().__setitem__("angle", 0)
        if name in ("dz", "angle"):
            self._updatedZfinal()

    def _updatedZfinal(self):
        if self["samplescan"] and self["angle"]:
            self["dzFinal"] = np.abs(self["dz"] * np.sin(self["angle"] * np.pi / 180))
        else:
            self["dzFinal"] = self["dz"]

    def isReady(self):
        if self["dz"] > 0 and hasattr(self, "dx"):
            return True
        return False

    def update(self, dic):
        for key, value in dic.items():
            if key == "samplescan":
                pass
            else:
                self[key] = value
        # set samplescan last
        if "samplescan" in dic:
            self["samplescan"] = dic["samplescan"]
            self._updatedZfinal()

    def __dir__(self):
        return self.keys()


class LLSdir:
    """Main class to encapsulate an LLS experiment.

    Detects parameters of an LLS experiment from a folder of files.  Parses
    Settings.txt file for acquisition parameters, and uses list of tiffs to
    determine nT, nC, etc.  Can call primary processing functions: preview and
    process.

    Args:
        path (:obj:`str`): path to LLS experiment
        ditch_partial (:obj:`bool`, optional): whether to discard tiff files that
            are smaller than the rest (and probably partially acquired)

    Usage:
        >>> E = llspy.LLSdir('path/to/experiment_directory')
        # it parses the settings file into a dict:
        >>> E.settings
        {'acq_mode': 'Z stack',
         'basename': 'cell1_Settings.txt',
         'camera': {'cam2name': '"Disabled"',
                    'cycle': '0.01130',
                    'cycleHz': '88.47 Hz',
                    'exp': '0.01002',
            ...
        }
        # many important attributes are in the parameters dict
        >>> E.parameters
        {'angle': 31.5,
         'dx': 0.1019,
         'dz': 0.5,
         'nc': 2,
         'nt': 10,
         'nz': 65,
         'samplescan': True,
          ...
        }
        # and provides methods for processing the data
        >>> E.autoprocess()
        # the autoprocess method accepts many options as keyword aruguments
        # a full list with descriptions can be seen here:
        >>> llspy.printOptions()
        >>> E.compress(compression='lbzip2')  # compress the raw data
        >>> E.decompress()  # decompress files for re-processing
        >>> E.freeze()  # delete processed data and compress raw data
    """

    def __init__(self, path, fname_pattern=None, ditch_partial=True):
        global __FPATTERN__
        if fname_pattern and isinstance(fname_pattern, str):
            self.fname_pattern = fname_pattern
        else:
            self.fname_pattern = __FPATTERN__
        self.fname_pattern += "{}"

        self.path = plib.Path(path)
        self.ditch_partial = ditch_partial
        self.settings_files = self.get_settings_files()
        self.has_settings = bool(len(self.settings_files))
        if not self.path.is_dir():
            return
        self.basename = self.path.name
        self.date = None
        self.parameters = CoreParams()
        self.tiff = util.dotdict()
        if self.has_settings:
            if len(self.settings_files) > 1:
                logger.warning("Multiple Settings.txt files detected...")
            self.settings = LLSsettings(self.settings_files[0])
            self.date = self.settings.date
            self.parameters.update(self.settings.parameters)
        # if no settings were found, there is probably no dz/dx/angle info
        # check here and then look for a previously processed proclog.txt
        if self.parameters.dz == 0:
            proclog = util.find_filepattern(str(self.path), "*" + config.__OUTPUTLOG__)
            try:
                if proclog and os.path.isfile(proclog):
                    with open(proclog) as f:
                        procdict = json.load(f)
                    if procdict:
                        if "dzdata" in procdict:
                            self.parameters.dz = procdict["dzdata"]
                        if "drdata" in procdict:
                            self.parameters.dx = procdict["drdata"]
                        if "deskew" in procdict:
                            self.parameters.angle = procdict["deskew"]
            except Exception as e:
                logger.warning(f"Exception reading {proclog}: {e}")

        if self.has_lls_tiffs:
            self._register_tiffs()

    @property
    def isValid(self):
        """Returns true if the path is a directory and has a settings.txt file."""
        if self.path.is_dir() and self.has_settings:
            return True
        else:
            return False

    @property
    def ready_to_process(self):
        """Returns true if the path is a directory, has a settings.txt file and valid LLS tiffs."""
        if self.path.is_dir():
            if self.has_lls_tiffs and self.parameters.isReady():
                return True
        return False

    @property
    def has_lls_tiffs(self):
        """Returns true if the folder has any tiffs mathing the filename regex."""
        if self.path.is_dir():
            return parse.contains_filepattern(self.path, self.fname_pattern)
        return False

    @property
    def age(self):
        """Returns true if the path is a directory and has a settings.txt file."""
        if hasattr(self, "date"):
            delta = datetime.datetime.now() - self.date
            return delta.days

    def get_settings_files(self):
        return [str(s) for s in self.path.glob("*Settings.txt")]

    def _register_tiffs(self):
        if self._get_all_tiffs():
            if self.ditch_partial:
                self.ditch_partial_tiffs()
            else:
                self.tiff.raw = self.tiff.all
            self.detect_parameters()
            self.read_tiff_header()

    def _get_all_tiffs(self):
        """a list of every tiff file in the top level folder (all raw tiffs)"""
        all_tiffs = sorted(
            x for x in self.path.glob("*.tif") if _parse(self.fname_pattern, str(x))
        )
        if not all_tiffs:
            logger.warning("No raw/uncompressed Tiff files detected in folder")
            return 0
        self.tiff.numtiffs = len(all_tiffs)
        # self.tiff.bytes can be used to get size of raw data: np.sum(self.tiff.bytes)
        self.tiff.bytes = [f.stat().st_size for f in all_tiffs]
        self.tiff.size_raw = round(np.median(self.tiff.bytes), 2)
        self.tiff.all = [str(f) for f in all_tiffs]
        return self.tiff.numtiffs

    def ditch_partial_tiffs(self):
        """yields self.tiff.raw: a list of tiffs that match in file size.
        this excludes partially acquired files that can screw up various steps
        perhaps a better (but slower?) approach would be to look at the tiff
        header for each file?
        """
        self.tiff.raw = []
        if self.parameters.nx and self.parameters.ny:
            thresh = (self.parameters.nx * self.parameters.ny) * 2
        else:
            thresh = 10000
        for idx, f in enumerate(self.tiff.all):
            if abs(self.tiff.bytes[idx] - self.tiff.size_raw) < thresh:
                self.tiff.raw.append(str(f))
            else:
                logger.warning(f"discarding small file:  {f}")
        self.tiff.rejected = list(set(self.tiff.raw).difference(set(self.tiff.all)))
        if len(self.tiff.all) and not len(self.tiff.raw):
            raise LLSpyError(
                "LLSpy attempts to exclude partially acquired files "
                "from processing.  In this case, there are no files left! "
                "Please check data structure assumptions in the docs. "
            )

    def detect_parameters(self):
        self.tiff.count = []  # per channel list of number of tiffs
        self.parameters.interval = []
        self.parameters.channels = {}
        stacknum = re.compile(r"stack(\d{4})")
        self.parameters.tset = list(
            {int(t.group(1)) for t in [stacknum.search(s) for s in self.tiff.raw] if t}
        )

        self.tiff.count = [0] * 20  # stupid
        temp = [0] * 20
        Ns = [
            parse.parse_filename(str(f), pattern=self.fname_pattern)
            for f in self.tiff.raw
        ]
        for N in Ns:
            if "channel" not in N:
                raise LLSpyError("filepattern must specify a channel")
            self.tiff.count[N["channel"]] += 1
            if "wave" not in N:
                raise LLSpyError("filepattern must specify a wave")
            self.parameters.channels[N["channel"]] = N["wave"]

            if "abstime" in N:
                if self.tiff.count[N["channel"]] == 1:
                    temp[N["channel"]] = N["abstime"]
                if self.tiff.count[N["channel"]] == 2:
                    temp[N["channel"]] = N["abstime"] - temp[N["channel"]]

        self.tiff.count = [n for n in self.tiff.count if n != 0]
        self.parameters.nc = len(self.tiff.count)
        self.parameters.interval = [n / 1000 for n in temp if n != 0]

        if len(set(self.tiff.count)) > 1:
            # different count for each channel ... decimated stacks?
            self.parameters.decimated = True
        else:
            self.parameters.decimated = False

        try:
            self.parameters.duration = max(
                (a - 1) * b for a, b in zip(self.tiff.count, self.parameters.interval)
            )
        except Exception:
            self.parameters.duration = []

    def read_tiff_header(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with tf.TiffFile(self.tiff.raw[0]) as firstTiff:
                self.parameters.shape = firstTiff.series[0].shape
                try:
                    self.tiff.bit_depth = getattr(firstTiff.pages[0], "bitspersample")
                except AttributeError:
                    try:
                        self.tiff.bit_depth = getattr(
                            firstTiff.pages[0], "bits_per_sample"
                        )
                    except AttributeError:
                        self.tiff.bit_depth = 16
        (
            self.parameters.nz,
            self.parameters.ny,
            self.parameters.nx,
        ) = self.parameters.shape

    def is_compressed(self, subdir=None):
        if not subdir:
            path = str(self.path)
        elif self.path.joinpath(subdir).is_dir():
            path = str(self.path.joinpath(subdir))
        else:
            raise ValueError(f"Subdirectory does not exists: {subdir}")

        exts = tuple(compress.EXTENTIONS.keys())
        zips = [f for f in os.listdir(path) if f.endswith(exts)]
        return bool(len(zips))

    def has_been_processed(self):
        return util.pathHasPattern(str(self.path), "*" + config.__OUTPUTLOG__)

    def is_corrected(self):
        corpath = self.path.joinpath("Corrected")
        if corpath.exists():
            if len(list(corpath.glob("*COR*"))) < len(self.tiff.raw):
                # partial correction
                logger.warning("Corrected path exists but files incomplete")
                return False
            else:
                return True
        else:
            return False

    def compress(self, subfolder=".", compression=None):
        logger.info("compressing %s..." % str(self.path.joinpath(subfolder)))
        return compress.compress(
            str(self.path.joinpath(subfolder)), compression=compression
        )

    def decompress(self, subfolder=".", **kwargs):
        o = compress.decompress(str(self.path.joinpath(subfolder)))
        self._register_tiffs()
        return o

    def decompress_partial(self, subfolder=".", tRange=None):
        """attempt to extract a subset of the tarball,  tRange=None will yield t=0"""
        compress.decompress_partial(str(self.path.joinpath(subfolder)), tRange)
        self._register_tiffs()

    def reduce_to_raw(self, keepmip=True, verbose=True):
        """
        need to consider the case of sepmips
        """
        if verbose:
            logger.info("reducing %s..." % str(self.path.name))

        subfolders = ["GPUdecon", "CPPdecon", "Deskewed", "Corrected"]

        if keepmip:
            miplist = list(self.path.glob("**/*_MIP_*.tif"))
            if len(miplist):
                if not self.path.joinpath("MIPs").exists():
                    not self.path.joinpath("MIPs").mkdir()
                for mipfile in miplist:
                    mipfile.rename(self.path.joinpath("MIPs", mipfile.name))
        else:
            subfolders.append("MIPs")

        for folder in subfolders:
            if self.path.joinpath(folder).exists():
                try:
                    if verbose:
                        logger.info("\tdeleting %s..." % folder)
                    shutil.rmtree(str(self.path.joinpath(folder)))
                except Exception as e:
                    logger.error(
                        "unable to remove directory: {}".format(
                            self.path.joinpath(folder)
                        )
                    )
                    logger.error(e)
                    return 0
        try:
            i = self.path.glob("*" + config.__OUTPUTLOG__)
            for n in i:
                n.unlink()
        except Exception:
            pass
        return 1

    def freeze(self, verbose=True, keepmip=True, **kwargs):
        """Freeze folder for long term storage.

        Delete's all deskewed and deconvolved data
        (with the execption of MIPs unless requested),
        then compresses raw files into compressed tarball
        """
        if verbose:
            logger.info(f"freezing {self.path.name} ...")
        if self.reduce_to_raw(verbose=verbose, keepmip=keepmip, **kwargs):
            if self.compress(**kwargs):
                return 1

    def localParams(self, recalc=False, **kwargs):
        """Returns a validated dict of processing parameters that are specific
        to this LLSdir instance.

        Accepts any keyword arguments that are recognized by the LLS `Schema list`_.

        >>> E.localParams(nIters=0, bRotate=True, bleachCorrection=True)
        {'MIP': (0, 0, 1), 'autoCropSigma': 2.0, 'bRotate': True,
        'background': [100, 98], 'bleachCorrection': True,
        'cRange': range(0, 2), 'camparamsPath': None, 'compressRaw': False,
        'compressionType': 'lbzip2', 'correctFlash': False,
        'cropMode': 'none', 'cropPad': 50, 'deskew': 31.5, 'doReg': False,
        'drdata': 0.1019, 'dzFinal': 0.1567, 'dzdata': 0.3,
        'flashCorrectTarget': 'cpu', 'keepCorrected': False,
        'medianFilter': False, 'mergeMIPs': True, 'mergeMIPsraw': True,
        'mincount': 10, 'moveCorrected': True, 'napodize': 15,
        'nIters': 0, 'nzblend': 0, 'otfDir': None, 'rMIP': (0, 0, 0),
        'regCalibPath': None, 'regMode': '2step', 'regRefWave': 488,
        'reprocess': False, 'rotate': 31.5, 'saveDecon': True,
        'saveDeskewedRaw': False, 'shift': 0, 'tRange': [0],
        'trimX': (0, 0), 'trimY': (0, 0), 'trimZ': (0, 0), 'uint16': True,
        'uint16raw': True, 'verbose': 0, 'wavelength': [488, 560],
        'width': 0, 'writeLog': True}
        """
        # allow for 'lazy' storage of previously calculated value
        if "_localParams" in dir(self) and not recalc:
            if all([self._localParams[k] == v for k, v in kwargs.items()]):
                return self._localParams
        _schema = schema.procParams(kwargs)
        assert (
            sum(_schema.trimY) < self.parameters.ny
        ), "TrimY sum must be less than number of Y pixels"
        assert (
            sum(_schema.trimX) < self.parameters.nx
        ), "TrimX sum must be less than number of X pixels"
        assert (
            sum(_schema.trimZ) < self.parameters.nz
        ), "TrimZ sum must be less than number of Z pixels"

        if _schema.cRange is None:
            # _schema.cRange = range(self.parameters.nc)
            _schema.cRange = list(self.parameters.channels.keys())
        else:
            outrange = []
            for chan in _schema.cRange:
                if chan in self.parameters.channels.keys():
                    outrange.append(chan)
                else:
                    logger.warning(f"Channel {chan} not present in datset! Excluding.")
            if np.max(list(_schema.cRange)) > (self.parameters.nc - 1):
                logger.warning(
                    "cRange was larger than number of Channels! Excluding C > {}".format(
                        self.parameters.nc - 1
                    )
                )
            _schema.cRange = outrange

        if _schema.tRange is None:
            _schema.tRange = self.parameters.tset
        else:
            logger.debug(f"preview tRange = {_schema.tRange}")
            maxT = max(self.parameters.tset)
            minT = min(self.parameters.tset)
            logger.debug("preview maxT = %d" % maxT)
            logger.debug("preview minT = %d" % minT)
            _schema.tRange = sorted(n for n in _schema.tRange if minT <= n <= maxT)
            if not _schema.tRange or len(_schema.tRange) == 0:
                _schema.tRange = [minT]
            if max(list(_schema.tRange)) > maxT:
                logger.warning(
                    "max tRange was greater than the last timepoint. Excluding T > {}".format(
                        maxT
                    )
                )
            if min(list(_schema.tRange)) < minT:
                logger.warning(
                    "min tRange was less than the first timepoint. Excluding < {}".format(
                        minT
                    )
                )

        assert len(_schema.tRange), "No valid timepoints!"
        assert len(_schema.cRange), "No valid channels requested"
        # note: background should be forced to 0 if it is getting corrected
        # in the camera correction step
        if _schema.background < 0 and self.has_lls_tiffs:
            _schema.background = self.get_background(_schema.cRange)
        else:
            _schema.background = [_schema.background] * len(list(_schema.cRange))

        if _schema.cropMode == "auto":
            wd = self.get_feature_width(
                pad=_schema.cropPad, t=np.min(list(_schema.tRange))
            )
            _schema.width = wd["width"]
            _schema.shift = wd["offset"]
        elif _schema.cropMode == "none":
            _schema.width = 0
            _schema.shift = 0
        else:  # manual mode
            # use defaults
            _schema.width = _schema.width
            _schema.shift = _schema.shift
        # TODO: add constrainst to make sure that width/2 +/- shift is within bounds
        assert 0 <= _schema.width / 2

        # add check for RegDIR
        # RD = RegDir(P.regCalibPath)
        # RD = self.path.parent.joinpath('tspeck')
        _schema.drdata = self.parameters.dx
        _schema.dzdata = self.parameters.dz
        _schema.wavelength = [self.parameters.channels[c] for c in _schema.cRange]
        _schema.dzFinal = self.parameters.dzFinal
        _schema.deskew = self.parameters.angle
        if not self.parameters.samplescan:
            _schema.rMIP = (0, 0, 0)
            _schema.saveDeskewedRaw = False

        # FIXME:
        # shouldn't have to get OTF if not deconvolving... though cudaDeconv
        # may have an issue with this...
        # in fact, if not deconvolving, we should simply use libcudaDeconv
        # and not use the full cudaDeconv binary
        if _schema.nIters > 0 or (_schema.deskew > 0 and _schema.saveDeskewedRaw):
            _schema.otfs = []
            for c in _schema.cRange:
                wave = self.parameters.channels[c]
                _schema.otfs.append(self.get_otf(wave, otfpath=_schema.otfDir))
            if not len(_schema.otfs):
                raise OTFError(
                    "Deconvolution requested but no OTF available.  Check OTF path"
                )
            if not len(_schema.otfs) == len(list(_schema.cRange)):
                raise OTFError("Could not find OTF for every channel in OTFdir.")

        if _schema.bRotate:
            _schema.rotate = (
                _schema.rotate if _schema.rotate is not None else self.parameters.angle
            )
            if _schema.rotateRev:
                _schema.rotate *= -1
        else:
            _schema.rotate = 0

        self._localParams = util.dotdict(schema.__localSchema__(_schema))
        return self._localParams

    def autoprocess(self, **kwargs):
        """Calls the :obj:`process` function on the LLSdir instance.

        kwargs can be any keywords that are recognized by the LLS `Schema list`_.
        """
        return process(self, **kwargs)

    def preview(self, tR=0, cR=None, **kwargs):
        return preview(self, tR=tR, cR=cR, **kwargs)

    def mergemips(self, subdir=None, delete=True):
        """look for MIP files in subdirectory, compress into single hyperstack
        and write file to disk"""
        if subdir is not None:
            if self.path.joinpath(subdir).is_dir():
                subdir = self.path.joinpath(subdir)
            else:
                logger.error("Could not find subdir: %s" % subdir)
                return
        else:
            subdir = self.path

        # the "**" pattern means this directory and all subdirectories, recursively
        for MIPdir in subdir.glob("**/MIPs/"):
            # get dict with keys= axes(x,y,z) and values = numpy array
            try:
                interval = self.parameters.interval[0]
            except IndexError:
                interval = 0
            for axis in ["z", "y", "x"]:
                mergemips(
                    MIPdir,
                    axis,
                    dx=self.parameters.dx,
                    dt=interval,
                    fpattern=self.fname_pattern,
                )

    def process(self, filepattern, otf, indir=None, binary=None, **opts):
        if binary is None:
            binary = CUDAbin()

        if indir is None:
            indir = str(self.path)
        output = binary.process(indir, filepattern, otf, **opts)
        return output

    def get_t(self, t):
        return parse.filter_t(self.tiff.raw, t)

    def get_c(self, c):
        return parse.filter_c(self.tiff.raw, c)

    def get_w(self, w):
        return parse.filter_w(self.tiff.raw, w)

    def get_reltime(self, rt):
        return parse.filter_reltime(self.tiff.raw, rt)

    def get_files(self, **kwargs):
        return parse.filter_files(self.tiff.raw, **kwargs)

    def get_otf(self, wave, otfpath=config.__OTFPATH__):
        """intelligently pick OTF from archive directory based on date and mask
        settings."""
        if otfpath is None or not os.path.isdir(otfpath):
            return None

        if not otfmodule.dir_has_otfs(otfpath):
            raise OTFError(f"OTF directory has no OTFs! -> {otfpath}")

        mask = None
        if hasattr(self, "settings") and hasattr(self.settings, "mask"):
            innerNA = self.settings.mask.innerNA
            outerNA = self.settings.mask.outerNA
            mask = (innerNA, outerNA)

        otf = otfmodule.choose_otf(wave, otfpath, self.date, mask)
        if not otf or not os.path.isfile(otf):
            if mask:
                raise OTFError(
                    "Could not find OTF for "
                    "wave {}, mask {}-{} in path: {}".format(
                        wave, outerNA, innerNA, otfpath
                    )
                )
            else:
                raise OTFError(
                    "Could not find OTF for "
                    "wave {} in path: {}".format(wave, otfpath)
                )
        return otf

    def get_feature_width(self, t=0, **kwargs):
        # defaults background=100, pad=100, sigma=2
        w = {}
        w.update(arrayfun.feature_width(self, t=t, **kwargs))
        # self.parameters.content_width = w['width']
        # self.parameters.content_offset = w['offset']
        # self.parameters.deskewed_nx = w['newX']
        return w

    # TODO: should calculate background of provided folder (e.g. Corrected)
    def get_background(self, cRange=None, **kwargs):
        if cRange is None:
            cRange = list(self.parameters.channels.keys())
        if not self.has_lls_tiffs:
            logger.error("Cannot calculate background on folder with no Tiffs")
            return
        # defaults background and=100, pad=100, sigma=2
        bgrd = []
        for c in cRange:
            i = util.imread(self.get_files(c=c)[0]).squeeze()
            bgrd.append(arrayfun.detect_background(i))
        # self.parameters.background = bgrd
        return bgrd

    def median_and_trim(
        self,
        tRange=None,
        cRange=None,
        medianFilter=True,
        background=None,
        trimZ=(0, 0),
        trimY=(0, 0),
        trimX=(0, 0),
        **kwargs,
    ):

        trim = (trimZ, trimY, trimX)

        outpath = self.path.joinpath("Corrected")
        if not outpath.is_dir():
            outpath.mkdir()

        if tRange is None:
            tRange = self.parameters.tset

        filenames = [self.get_files(c=chan, t=tRange) for chan in cRange]
        filenames = [f for f in filenames if len(f)]  # dicard empties

        if background is None:
            B = self.get_background()
            background = [B[i] for i in cRange]
        assert len(background) == len(list(cRange))

        g = []
        for c, flist in enumerate(filenames):
            for f in flist:
                bgrd = background[c]
                outname = str(outpath.joinpath(os.path.basename(f)))
                if medianFilter:
                    outname = outname.replace(".tif", "_COR.tif")
                g.append((f, outname, self.parameters.dx, bgrd, trim, medianFilter))

        if sys.version_info >= (3, 4):
            with Pool(processes=cpu_count()) as pool:
                pool.map(unbundle, g)
        else:
            pool = Pool(processes=cpu_count())
            pool.map(unbundle, g)
            pool.close()
            pool.join()

        return outpath

    def correct_flash(
        self,
        tRange=None,
        camparamsPath=None,
        flashCorrectTarget="parallel",
        medianFilter=False,
        trimZ=(0, 0),
        trimY=(0, 0),
        trimX=(0, 0),
        **kwargs,
    ):
        """Correct flash artifact, writing files to Corrected dir."""
        if not self.has_settings:
            raise LLSpyError("Cannot correct Flash pixels without settings.txt file")
        if not isinstance(camparamsPath, CameraParameters):
            if isinstance(camparamsPath, str):
                camparams = CameraParameters(camparamsPath)
            else:
                # FIXME: Janky py2/3 hack
                try:
                    if isinstance(camparamsPath, str):
                        camparams = CameraParameters(camparamsPath)
                except Exception:
                    camparams = CameraParameters()
        logger.debug(f"Correcting Flash artifact with camparam {camparams.basename}")

        if not np.all(camparams.roi == self.settings.camera.roi):
            try:
                camparams = camparams.get_subroi(self.settings.camera.roi)
            except Exception:
                raise ValueError("ROI in parameters does not match data ROI")

        outpath = self.path.joinpath("Corrected")
        if not outpath.is_dir():
            outpath.mkdir()

        if tRange is None:
            tRange = self.parameters.tset
        timegroups = [self.get_t(t) for t in tRange]

        # FIXME: this is a temporary bug fix to correct for the fact that
        # LLSdirs acquired in script editor (Iter_0, etc...) don't correctly
        # detect the number of timepoints
        timegroups = [t for t in timegroups if len(t)]

        if flashCorrectTarget == "parallel":
            # numthreads = cpu_count()
            # procs = []
            # for t in timegroups:
            #   args = (t, camparams, outpath, medianFilter)
            #   procs.append(Process(flashCorrectTarget=correctTimepoint, args=args))
            # while len(procs):
            #   proccessGroup = procs[0:numthreads]
            #   procs[0:numthreads] = []
            #   [p.start() for p in proccessGroup]
            #   [p.join() for p in proccessGroup]

            g = [
                (t, camparams, outpath, medianFilter, trimZ, trimY, trimX)
                for t in timegroups
            ]
            if sys.version_info >= (3, 4):
                with Pool(processes=cpu_count()) as pool:
                    pool.map(unwrapper, g)
            else:
                pool = Pool(processes=cpu_count())
                pool.map(unwrapper, g)
                pool.close()
                pool.join()

        elif flashCorrectTarget == "cpu":
            for t in timegroups:
                correctTimepoint(
                    t, camparams, outpath, medianFilter, trimZ, trimY, trimX
                )
        elif flashCorrectTarget == "cuda" or flashCorrectTarget == "gpu":
            camparams.init_CUDAcamcor(
                (
                    self.parameters.nz * self.parameters.nc,
                    self.parameters.ny,
                    self.parameters.nx,
                )
            )
            for t in timegroups:
                correctTimepoint(
                    t, camparams, outpath, medianFilter, trimZ, trimY, trimX, "cuda"
                )
        else:
            for t in timegroups:
                correctTimepoint(
                    t, camparams, outpath, medianFilter, trimZ, trimY, trimX
                )
        return outpath

    def register(self, regRefWave, regMode, regCalibPath, discard=False):
        if self.parameters.nc < 2:
            logger.error("Cannot register single channel dataset")
            return

        regObj = get_regObj(regCalibPath)
        if isinstance(regObj, (RegDir, RegFile)) and regObj.isValid:
            voxsize = [self.parameters.dzFinal, self.parameters.dx, self.parameters.dx]
            subdirs = [
                x
                for x in self.path.iterdir()
                if x.is_dir() and x.name in ("GPUdecon", "Deskewed")
            ]
            for D in subdirs:
                register_folder(
                    D, regRefWave, regMode, regObj, voxsize, discard=discard
                )
        else:
            logger.error(
                "Registration Calibration path not valid" "{}".format(regCalibPath)
            )

    def toJSON(self):
        import json

        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def __str__(self):
        out = {}
        if hasattr(self, "bytes"):
            out.update({"raw data size": util.format_size(np.mean(self.tiff.bytes))})
        for k, v in self.__dict__.items():
            if k not in {"all_tiffs", "date", "settings_files"}:
                out.update({k: v})
        return pprint.pformat(out)


# TODO: cache cloud result after reading files and filtering once
class RegDir(LLSdir):
    """Special type of LLSdir that holds image registraion data like
    tetraspeck beads

    If threshold is integer value, it will be used as minimum intensity
    for detected beads... otherwise mincount # beads will be required.
    mincount default is set in fiducialreg.get_thresh()
    """

    def __init__(
        self, path, t=None, mincount=None, threshold=None, usejson=True, **kwargs
    ):
        super().__init__(path, **kwargs)
        if self.path is not None:
            if self.path.joinpath("cloud.json").is_file() and usejson:
                with open(str(self.path.joinpath("cloud.json"))) as json_data:
                    self = self.fromJSON(json.load(json_data))
        self.t = t
        self.mincount = mincount
        self.threshold = threshold
        if self.has_lls_tiffs and t is None:
            self.t = min(self.parameters.tset)
        if self.isValid:
            self.data = self.getdata()
            self.waves = [
                parse.parse_filename(f, "wave", pattern=self.fname_pattern)
                for f in self.get_t(self.t)
            ]
            self.channels = [
                parse.parse_filename(f, "channel", pattern=self.fname_pattern)
                for f in self.get_t(self.t)
            ]
            self.deskew = self.parameters.samplescan

    @property
    def isValid(self):
        if self.t is not None:
            return bool(len(self.get_t(self.t)))
        return False

    def getdata(self):
        return [util.imread(f) for f in self.get_t(self.t)]

    def has_data(self):
        return all([isinstance(a, np.ndarray) for a in self.data])

    def toJSON(self):
        D = self.__dict__.copy()
        D["_cloudset"] = D["_cloudset"].toJSON()
        D["path"] = str(D["path"])
        # FIXME: make LLSsettings object serializeable
        D.pop("settings", None)
        # D['settings']['camera']['roi'] = self.settings.camera.roi.tolist()
        # D['settings']['date'] = self.settings.date.isoformat()
        D["date"] = D["date"].isoformat()
        D.pop("data", None)
        D.pop("deskewed", None)
        return json.dumps(D)

    def fromJSON(self, Jstring):
        D = json.loads(Jstring)
        for k, v in D.items():
            setattr(self, k, v)
        super().__init__(D["path"])
        self._cloudset = CloudSet().fromJSON(D["_cloudset"])
        return self

    def _deskewed(self, dz=None, dx=None, angle=None):
        if "deskewed" in dir(self):
            return self.deskewed
        else:
            dx = dx if dx else self.parameters.dx
            dz = dz if dz else self.parameters.dz
            angle = angle if angle else self.parameters.angle
            if (not dx) or (not dz) or (not angle):
                raise ValueError("Cannot deskew without dx, dz & angle")

            self.deskewed = [deskewGPU(i, dz, dx, angle) for i in self.data]
            return self.deskewed

    def cloudset(self, redo=False, tojson=False):
        """actually generates the fiducial cloud"""
        if "_cloudset" in dir(self) and not redo:
            return self._cloudset
        self._cloudset = CloudSet(
            self._deskewed() if self.deskew else self.data,
            labels=self.waves,
            dx=self.parameters.dx,
            dz=self.parameters.dzFinal,
            mincount=self.mincount,
            threshold=self.threshold,
        )
        if tojson:
            with open(str(self.path.joinpath("cloud.json")), "w") as outfile:
                json.dump(self.toJSON(), outfile)
        return self._cloudset

    def cloudset_has_data(self):
        return self.cloudset().has_data()

    def reload_data(self):
        self.cloudset(redo=True)

    def write_reg_file(self, outdir, filename=None, refs=None, **kwargs):
        """write all of the tforms for this cloudset to file"""

        if not os.path.isdir(outdir):
            raise FileNotFoundError(f"Directory does not exist: {outdir}")

        class npEncoder(json.JSONEncoder):
            def fixedString(self, obj):
                numel = len(obj)
                form = "[" + ",".join(["{:14.10f}"] * numel) + "]"
                return form.format(*obj)

            def default(self, obj):
                if isinstance(obj, np.ndarray):
                    if all(isinstance(i, np.ndarray) for i in obj):
                        nestedList = obj.tolist()
                        result = [self.fixedString(l) for l in nestedList]
                        return result
                    else:
                        return obj.tolist()
                return json.JSONEncoder.default(self, obj)

        tforms = self.cloudset().get_all_tforms(refs=refs, **kwargs)
        outdict = {
            "path": str(self.path),
            "dx": self.parameters.dx,
            "dz": self.parameters.dzFinal,
            "z_motion": self.parameters.z_motion,
            # 'refs': refs,
            # 'moving': list(set([t['moving'] for t in tforms])),
            # 'modes': list(set([t['mode'] for t in tforms])),
            "tforms": tforms,
        }
        try:
            outdict["date"] = (self.date.strftime("%Y/%m/%d-%H:%M"),)
        except AttributeError:
            pass
        outstring = json.dumps(outdict, cls=npEncoder, indent=2)
        outstring = outstring.replace('"[', " [").replace(']"', "]")

        if filename is None or not isinstance(filename, str):
            filename = "LLSreg_{}_{}.reg".format(
                self.date.strftime("%y%m%d"), "".join("r" + str(w) for w in refs)
            )
        outfile = os.path.join(outdir, filename)
        with open(outfile, "w") as file:
            file.write(outstring)

        return (outfile, outstring)

    def get_tform(self, movingWave, refWave=488, mode="2step"):
        return self.cloudset().tform(movingWave, refWave, mode)


def rename_iters(folder, splitpositions=True):
    """
    Rename files in a folder acquired with LLS multi-position script.

    Assumes every time points is labeled Iter_n.

    This assumes that each position was acquired every iteration
    and that only a single scan is performed per position per iteration
    (i.e. it assumes that everything is a "stack0000")

    example, filename (if it's the second position in a scipted FOR loop):
        filename_Iter_2_ch1_stack0000_560nm_0000000msec_0006443235msecAbs.tif
    gets changes to:
        filename_pos01_ch1_stack0002_560nm_0023480msec_0006443235msecAbs.tif

    if splitpositions==True:
        files from different positions will be placed into subdirectories
    """

    filelist = glob.glob(os.path.join(folder, "*Iter*stack*"))
    if not filelist:
        raise LLSpyError(f"No *Iter*stack* files found in {folder}")
    try:
        iterset = {int(f.split("Iter_")[1].split("_")[0]) for f in filelist}
        chanset = {int(f.split("_ch")[1].split("_")[0]) for f in filelist}
    except ValueError:
        raise LLSpyError(
            "Failed to parse filenames to detect number of Iter_ files."
            "If this folder only has a single Iteration (not Iter_0, etc...), "
            "it may be best not to try rename_iters..."
        )
    except Exception:
        raise LLSpyError("Failed to parse filenames to detect number of Iter_ files")

    returndirs = []
    iterdict = {}
    nFilesPerChannel = []
    for it in iterset:
        iterdict[it] = {}
        iterdict[it]["setfile"] = util.find_filepattern(
            folder, "*Iter_%s_*Settings.txt" % it
        )
        # all the files from this Iter group
        g = [f for f in filelist if "Iter_%s_" % it in f]
        # tuple of nFiles in each channel in this group
        nFilesPerChannel.append(
            tuple(len([f for f in g if "ch%d" % d in f]) for d in chanset)
        )
    nFPCset = set(
        nFilesPerChannel
    )  # e.g. {(4,4)}, if all positions had 4 timepoints and 2 channels
    if len(nFPCset) > 1:
        raise LLSpyError(
            "rename_iters function requires that each iteration has "
            "the same number of tiffs"
        )
    nPosSet = set(nFPCset.pop())  # e.g. {4}
    if len(nPosSet) > 1:
        raise LLSpyError(
            "rename_iters function requires that all channels "
            "have the same number of tiffs"
        )
    nPositions = nPosSet.pop()  # e.g. 4

    changelist = []
    for it in iterset:
        settingsFile = iterdict[it]["setfile"]
        if not settingsFile:
            continue
        if nPositions > 1:
            newname = re.sub(
                r"Iter_\d+", "pos%02d" % it, os.path.basename(settingsFile)
            )
        else:
            newname = re.sub(
                r"Iter_\d+", "stack%04d" % it, os.path.basename(settingsFile)
            )
        os.rename(settingsFile, os.path.join(folder, newname))
        changelist.append((settingsFile, os.path.join(folder, newname)))
    for chan in chanset:
        t0 = [0] * nPositions
        for i in iterset:
            flist = sorted(
                f for f in filelist if "ch%s" % chan in f and "Iter_%s_" % i in f
            )
            for pos in range(nPositions):
                base = os.path.basename(flist[pos])
                if i == 0:
                    t0[pos] = int(base.split("msecAbs")[0].split("_")[-1])
                newname = base.replace("stack0000", "stack%04d" % i)
                deltaT = int(base.split("msecAbs")[0].split("_")[-1]) - t0[pos]
                newname = newname.replace("0000000msec_", "%07dmsec_" % deltaT)
                if nPositions > 1:
                    newname = re.sub(r"Iter_\d+", "pos%02d" % pos, newname)
                else:
                    newname = re.sub(r"_Iter_\d+", "", newname)
                logger.info(f"renaming {base} --> {newname}")
                os.rename(flist[pos], os.path.join(folder, newname))
                changelist.append((flist[pos], os.path.join(folder, newname)))
    if splitpositions and nPositions > 1:
        # files from different positions will be placed into subdirectories
        pos = 0
        while True:
            movelist = glob.glob(os.path.join(folder, "*pos%02d*" % pos))
            if not len(movelist):
                break
            basename = os.path.basename(movelist[0]).split("_pos")[0]
            posfolder = os.path.join(folder, basename + "_pos%02d" % pos)
            if not os.path.exists(posfolder):
                os.mkdir(posfolder)
                returndirs.append(posfolder)
                changelist.append((None, posfolder))
            for f in movelist:
                os.rename(f, os.path.join(posfolder, os.path.basename(f)))
                changelist.append((f, os.path.join(posfolder, os.path.basename(f))))
            pos += 1
    else:
        returndirs.append(folder)
    if len(changelist):
        with open(os.path.join(folder, "renaming_log.txt"), "w") as f:
            json.dump(changelist, f)

    return returndirs


def undo_rename_iters(path, deletelog=True):
    logfile = path
    if os.path.isdir(path):
        logfile = util.find_filepattern(path, "renaming_log.txt")
    if not logfile or not os.path.isfile(logfile):
        logger.error("Could not find renaming_log to undo_rename_iters")
        return
    with open(logfile) as f:
        changelist = json.load(f)
    deletionlist = []
    for item in reversed(changelist):
        src = item[1]
        dest = item[0]
        if not dest:
            deletionlist.append(src)
            continue
        logger.info(f"renaming {src} --> {dest}")
        try:
            os.rename(src, dest)
        except FileNotFoundError as e:
            logger.error(e)
    for item in deletionlist:
        try:
            if os.path.isdir(item):
                os.rmdir(item)
            elif os.path.isfile(item):
                os.remove(item)
        except OSError as e:
            logger.error(e)
    if deletelog:
        os.remove(logfile)


def concatenate_folders(folderlist, raw=True, decon=True, deskew=True):
    """combine a list of folders into a single LLS folder.

    renames stack numbers and relative timestamp in filenames
    to concatenate folders as if they were taken in a single longer timelapse
    useful when an experiment was stopped and restarted
    (for instance, to change the offset)
    """

    # get timestamp of stack0000 for all folders
    stackzeros = []
    for folder in folderlist:
        try:
            firstfile = glob.glob(os.path.join(folder, "*ch0*stack0000*"))[0]
            basename = os.path.basename(firstfile).split("_ch0")[0]
            stackzeros.append([folder, firstfile, basename])
        except Exception:
            pass
    # sort by absolute timestamp
    tzeros = sorted(
        [int(t[1].split("msecAbs")[0].split("_")[-1]), t[0], t[2]] for t in stackzeros
    )

    # get relative time offset
    for t in tzeros:
        t.append(t[0] - tzeros[0][0])
        # example tzeros
        # [[23742190, '/top_folder/cell4', 'cell4', 0],
        #  [24583591, '/top_folder/cell4b', 'cell4b', 841401],
        #  [24610148, '/top_folder/cell4e', 'cell4e', 867958],
        #  [24901726, '/top_folder/cell4d', 'cell4d',1159536]]
    t0path = tzeros[0][1]
    basename = tzeros[0][2]

    channelcounts = [0] * 6
    for fi in sorted(os.listdir(t0path)):
        if fi.endswith(".tif"):
            chan = int(fi.split("_ch")[1].split("_")[0])
            channelcounts[chan] += 1
    tzeros[0].append(list(channelcounts))

    for t in tzeros[1:]:
        filelist = sorted(os.listdir(t[1]))
        tbase = t[2]
        deltaT = t[3]
        thisfoldercounts = [0] * 6
        for fi in filelist:
            if fi.endswith(".tif"):
                chan = int(fi.split("_ch")[1].split("_")[0])
                reltime = int(fi.split("msec_")[0].split("_")[-1])
                # change relative timestamp
                newname = re.sub(r"\d+msec_", "%07dmsec_" % int(reltime + deltaT), fi)
                newname = newname.replace(tbase, basename)
                # change stack number
                newname = re.sub(
                    r"_stack\d+", "_stack%04d" % channelcounts[chan], newname
                )
                os.rename(os.path.join(t[1], fi), os.path.join(t0path, newname))
                channelcounts[chan] += 1
                thisfoldercounts[chan] += 1
            else:
                os.rename(os.path.join(t[1], fi), os.path.join(t0path, fi))
        t.append(thisfoldercounts)
        os.rmdir(t[1])

    with open(os.path.join(t0path, "concatenationRecord.txt"), "w") as outfile:
        json.dump(tzeros, outfile)
