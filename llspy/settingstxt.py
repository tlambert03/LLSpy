import configparser
import logging
import os
import re
import warnings
from datetime import datetime

from . import camera, util
from .exceptions import SettingsError

logger = logging.getLogger(__name__)


# repating pattern definitions used for parsing settings file
numstack_pattern = re.compile(
    r"""
    \#\sof\sstacks\s\((?P<channel>\d)\) # channel number inside parentheses
    \s:\s+(?P<numstacks_requested>\d+)  # number of stacks after the colon
    """,
    re.MULTILINE | re.VERBOSE,
)

waveform_pattern = re.compile(
    r"""
    ^(?P<waveform>.*)\sOffset,  # Waveform type, newline followed by description
    .*\((?P<channel>\d+)\)\s    # get channel number inside of parentheses
    :\s*(?P<offset>[-\d]*\.?\d*)    # float offset value after colon
    \s*(?P<interval>[-\d]*\.?\d*)   # float interval value next
    \s*(?P<numpix>\d+)          # integer number of pixels last
    """,
    re.MULTILINE | re.VERBOSE,
)

excitation_pattern = re.compile(
    r"""
    Excitation\sFilter,\s+Laser,    # Waveform type, newline followed by description
    .*\(ms\)\s\((?P<channel>\d+)\)    # get channel number inside of parentheses
    .*:\t(?P<exfilter>[^\s]*)        # excitation filter: anything but whitespace
    \t(?P<laser>\d+)           # integer laser line
    \t(?P<power>\d*\.?\d*)     # float laser power value next
    \t(?P<exposure>\d*\.?\d*)  # float exposure time last
    \t?(?P<laser2>\d*\.?\d*)?  # patch for newer version of Dan's software
    \t?(?P<power2>\d*\.?\d*)?  # patch for newer version of Dan's software
    """,
    re.MULTILINE | re.VERBOSE,
)

PIXEL_SIZE = {"C11440-22C": 6.5, "C11440": 6.5, "C13440": 6.5}


class LLSsettings:
    """Class for parsing and storing info from LLS Settings.txt.

    Args:
        fname (:obj:`str`): path to settings.txt file

    Attributes:
        path: path to settings.txt file
        basename: basename of settings file
        date: :obj:`datetime` instance representing date of acquisition
        acq_mode: Lattice Scope acquisition mode (i.e. Z-stack)
        software_version: Lattice Scope software version
        cycle_lasers: laser cycling mode, e.g. 'per Z'
        z_motion: stage or objective scan
        channel: dict with waveform params for each channel
        camera: dict with camera settings
        SPIMproject: configparser object with full SPIMproject.ini data
        sheet_angle: light sheet angle
        mag: magnification in settings file
        pixel_size: calculated based on mag and dict of camera photodiode sizes
        parameters: most important parameters extracted from settings file
        raw_text: full settings.txt text string
    """

    def __init__(self, fname):
        self.path = os.path.abspath(fname)
        self.basename = os.path.basename(fname)
        if self.read():
            self.parse()

    def printDate(self):
        print(self.date.strftime("%x %X %p"))

    def read(self):
        # io.open grants py2/3 compatibility
        try:
            with open(self.path, encoding="utf-8") as f:
                self.raw_text = f.read()
            return 1
        except OSError:
            warnings.warn(f"Settings file not found at {self.path}")
            return 0
        except Exception:
            return 0

    def __repr__(self):
        from pprint import pformat

        sb = {
            k: v
            for k, v in self.__dict__.items()
            if k not in {"raw_text", "SPIMproject"}
        }
        return pformat(sb)

    def getSection(self, heading):
        secHeading = "\\*\\*\\*\\*\\*\\s+{}.*?\n\\*\\*\\*\\*"
        match = re.search(secHeading.format(heading), self.raw_text, re.DOTALL)
        if match is not None:
            # return match.group()
            return match.group().split("*****")[-1].strip("*").strip()
        else:
            return None

    def parse(self):
        """parse the settings file."""

        # the settings file is seperated into sections by "*****"
        # settingsSplit = re.split('[*]{5}.*\n', self.raw_text)
        # general_settings = settingsSplit[1]
        # waveform_settings = settingsSplit[2]     # the top part with the experiment
        # camera_settings = settingsSplit[3]
        # timing_settings = settingsSplit[4]
        # ini_settings = settingsSplit[5]  # the bottom .ini part

        general_settings = self.getSection("General")
        waveform_settings = self.getSection("Waveform")
        camera_settings = self.getSection("Camera")
        if not all([general_settings, waveform_settings, camera_settings]):
            raise SettingsError(
                "Could not parse at least one of the required"
                " sections of the Settings file"
            )
        ini_settings = self.raw_text.split("***** ***** *****")[-1]

        # parse the top part (general settings)
        datestring = re.search("Date\\s*:\\s*(.*)\n", general_settings).group(1)
        dateformats = ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %I:%M:%S", "%m/%d/%Y %H:%M:%S")
        self.date = None
        for fmt in dateformats:
            try:
                self.date = datetime.strptime(datestring, fmt)
            except ValueError:
                continue
        if self.date is None:
            logger.error(
                "Error, could not parse datestring {} with any of formats {}".format(
                    datestring, dateformats
                )
            )

        # print that with dateobject.strftime('%x %X %p')

        self.acq_mode = re.search("Acq Mode\\s*:\\s*(.*)\n", general_settings).group(1)
        self.software_version = re.search(
            r"Version\s*:\s*v ([\d*.?]+)", general_settings
        ).group(1)
        self.cycle_lasers = re.search(
            "Cycle lasers\\s*:\\s*(.*)(?:$|\n)", waveform_settings
        ).group(1)
        self.z_motion = re.search(
            "Z motion\\s*:\\s*(.*)(?:$|\n)", waveform_settings
        ).group(1)

        # find repating patterns in settings file
        waveforms = [
            m.groupdict() for m in waveform_pattern.finditer(waveform_settings)
        ]
        excitations = [
            m.groupdict() for m in excitation_pattern.finditer(waveform_settings)
        ]
        numstacks = [
            m.groupdict() for m in numstack_pattern.finditer(waveform_settings)
        ]

        # organize into channel dict
        self.channel = {}
        for item in waveforms:
            cnum = int(item.pop("channel"))
            if cnum not in self.channel:
                self.channel[cnum] = util.dotdict()
            wavename = item.pop("waveform")
            self.channel[cnum][wavename] = item
        for L in [excitations, numstacks]:
            for item in L:
                cnum = int(item.pop("channel"))
                if cnum not in self.channel:
                    self.channel[cnum] = {}
                self.channel[cnum].update(item)
        del excitations
        del numstacks
        del waveforms

        # parse the camera part
        cp = configparser.ConfigParser(strict=False)
        cp.read_string("[Camera Settings]\n" + camera_settings)
        # self.camera = cp[cp.sections()[0]]
        cp = cp[cp.sections()[0]]
        self.camera = util.dotdict()
        self.camera.model = cp.get("model")
        self.camera.serial = cp.get("serial")
        self.camera.exp = cp.get("exp(s)")
        self.camera.cycle = cp.get("cycle(s)")
        self.camera.cycleHz = cp.get("cycle(hz)")
        self.camera.roi = camera.CameraROI(
            [int(i) for i in re.findall(r"\d+", cp.get("roi"))]
        )
        self.camera.pixel = PIXEL_SIZE[self.camera.model.split("-")[0]]

        # parse the timing part
        # cp = configparser.ConfigParser(strict=False)
        # cp.read_string('[Timing Settings]\n' + timing_settings)
        # self.timing = cp[cp.sections()[0]]

        # parse the ini part
        cp = configparser.ConfigParser(strict=False)
        cp.optionxform = str  # leave case in keys
        cp.read_string(ini_settings)
        self.SPIMproject = cp
        # read it (for example)
        # cp.getfloat('Sample stage',
        #               'Angle between stage and bessel beam (deg)')
        self.sheet_angle = self.SPIMproject.getfloat(
            "Sample stage", "Angle between stage and bessel beam (deg)"
        )
        self.mag = self.SPIMproject.getfloat("Detection optics", "Magnification")
        self.camera.name = self.SPIMproject.get("General", "Camera type", fallback="")
        self.camera.trigger_mode = self.SPIMproject.get("General", "Cam Trigger mode")
        if self.SPIMproject.has_option("General", "CAM 1 Twin cam mode?"):
            _tcm = self.SPIMproject.get("General", "CAM 1 Twin cam mode?")
        else:
            _tcm = self.SPIMproject.get("General", "Twin cam mode?", fallback="False")
        self.camera.twincam = _tcm in ["TRUE", "True", 1, "YES", "Yes"]
        try:
            self.camera.cam2name = self.SPIMproject.get("General", "2nd Camera type")
        except Exception:
            self.camera.cam2name = "Disabled"
        self.pixel_size = round(self.camera.pixel / self.mag, 4)

        # not everyone will have added Annular mask to their settings ini
        for n in ["Mask", "Annular Mask", "Annulus"]:
            if self.SPIMproject.has_section(n):
                self.mask = util.dotdict()
                for k, v in self.SPIMproject["Annular Mask"].items():
                    self.mask[k] = float(v)

        # these will be overriden by the LLSDir file detection, but write anyway

        self.parameters = util.dotdict()
        self.parameters.update(
            {
                "dx": self.pixel_size,
                "z_motion": self.z_motion,
                "samplescan": self.is_sample_scan(),
                "angle": self.sheet_angle,
                "nc": len(self.channel),
                "nt": int(self.channel[0]["numstacks_requested"]),
                "nx": self.camera.roi.height,  # camera is usually rotated 90deg
                "ny": self.camera.roi.width,  # camera is usually rotated 90deg
                "wavelength": [int(v["laser"]) for k, v in self.channel.items()],
            }
        )
        if self.is_sample_scan():
            xstage = None
            if "S PZT" in self.channel[0]:
                xstage = "S PZT"
            elif "X Stage" in self.channel[0]:
                xstage = "X Stage"
            else:
                logger.error("Could not find either 'S PZT' or 'X stage' in waveforms")
            if xstage:
                self.parameters.dz = abs(float(self.channel[0][xstage]["interval"]))
                self.parameters.nz = int(self.channel[0][xstage]["numpix"])

        else:
            self.parameters.dz = abs(float(self.channel[0]["Z PZT"]["interval"]))
            self.parameters.nz = int(self.channel[0]["Z PZT"]["numpix"])

    def is_sample_scan(self):
        if hasattr(self, "z_motion"):
            return bool(self.z_motion.lower() in ("sample piezo", "x stage"))
        return None

    def write(self, outpath):
        """Write the raw text back to settings.txt file"""
        with open(outpath, "w") as outfile:
            outfile.write(self.raw_text)

    def write_ini(self, outpath):
        """Write just the SPIMProject.ini portion to file.

        The file written by this function should match the SPIMProject.ini file
        that was used to acquire the data.
        """
        with open(outpath, "w") as outfile:
            self.SPIMproject.write(outfile)
