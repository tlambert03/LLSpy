import os
import configparser

try:
    import pathlib as plib

    plib.Path()
except (ImportError, AttributeError):
    import pathlib2 as plib
except (ImportError, AttributeError):
    raise ImportError("no pathlib detected. For python2: pip install pathlib2")


thisDirectory = os.path.dirname(os.path.abspath(__file__))
parentDirectory = os.path.abspath(os.path.join(thisDirectory, os.pardir))

__CONFIGFILE__ = os.path.expanduser("~/.llspy")

defaults = {
    "cudadeconv": "cudaDeconv",
    "radialft": "radialft",
    "camera_parameters": os.path.abspath(
        os.path.join(thisDirectory, "FlashParams.tif")
    ),
    "otf_path": "/Users/talley/Dropbox (HMS)/CBMF/lattice_sample_data/lls_PSFs/",
    "output_log": "ProcessingLog.txt",
}

config = configparser.ConfigParser()
config["DEFAULT"] = defaults

config["OTFs"] = {}
for o in [488, 560, 592, 640]:
    config["OTFs"][str(o)] = os.path.join(
        config["DEFAULT"]["otf_path"], str(o) + "_otf.tif"
    )

config.read(__CONFIGFILE__)


def write(fname):
    with open(fname, "w") as configfile:
        config.write(configfile)


def _get_param(name, type, section="DEFAULT"):
    if type == bool:
        return config[section].getboolean(name)
    else:
        return type(config[section].get(name))


__CUDADECON__ = _get_param("cudadeconv", str)
__RADIALFT__ = _get_param("radialft", str)
__CAMPARAMS__ = _get_param("camera_parameters", str)
__OTFPATH__ = plib.Path(_get_param("otf_path", str))
__OUTPUTLOG__ = _get_param("output_log", str)
