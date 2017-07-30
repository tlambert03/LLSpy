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
from llspy.core.llsdir import LLSdir, preview, process
from llspy.core import otf
from llspy.core.settingstxt import LLSsettings as Settxt
from llspy.core.cudabinwrapper import CUDAbin
from llspy.core.parse import parse_filename, filter_files
from llspy.samples import samples
from llspy.camera.camera import CameraROI, CameraParameters, correctInsensitivePixels
from llspy import image
from llspy.core.schema import procParams, printOptions

#libcuda functions
try:
	from llspy.core.libcudawrapper import deskewGPU as deskew
	from llspy.core.libcudawrapper import affineGPU as affine
	from llspy.core.libcudawrapper import quickDecon as decon
	from llspy.core.libcudawrapper import rotateGPU as rotate
	from llspy.core.libcudawrapper import quickCamcor as camcor
except Exception:
	pass
