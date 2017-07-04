import os
from configparser import ConfigParser

configdir = os.path.dirname(os.path.abspath(__file__))
pardir = os.path.abspath(os.path.join(configdir, os.pardir))

__CONFIGFILE__ = os.path.expanduser("~/.llspy")

parser = ConfigParser()
parser.read(__CONFIGFILE__)


defaults = {
	'cudadeconv': '/usr/local/bin/cudaDeconv',
	'camera_parameters': os.path.abspath(os.path.join(pardir, "FlashParams.tif")),
	'otf_path': '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_PSFs',
	'output_log': 'ProcessingLog.txt',
}


def _get_param(name, type):
    return type(parser['DEFAULTS'].get(name, defaults[name]))


__CUDADECON__ = _get_param("cudadeconv", str)
__CAMPARAMS__ = _get_param("camera_parameters", str)
__OTFPATH__ = _get_param("otf_path", str)
__OUTPUTLOG__ = _get_param("output_log", str)
