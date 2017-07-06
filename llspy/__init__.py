from .version import __version__

import logging
logging.basicConfig(format='%(levelname)s:%(name)s | %(message)s')
logger = logging.getLogger(__name__)

try:
	import pathlib as plib
	plib.Path().expanduser()
except (ImportError, AttributeError):
	import pathlib2 as plib
except (ImportError, AttributeError):
	raise ImportError('no pathlib detected. For python2: pip install pathlib2')

from llspy.config import config

from llspy.core.llsdir import LLSdir
from llspy.core.settingstxt import LLSsettings as Settxt
from llspy.core.cudabinwrapper import CUDAbin
from llspy.core.parse import parse_filename

from llspy.samples import samples

from llspy.camera.camera import CameraROI, CameraParameters, correctInsensitivePixels

from llspy import image
