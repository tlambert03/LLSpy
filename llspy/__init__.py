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

from . import config
from . import otf
from . import arrayfun
from .llsdir import LLSdir, preview, process
from .settingstxt import LLSsettings as Settings
from .cudabinwrapper import CUDAbin
from .parse import parse_filename, filter_files
from .camera import CameraROI, CameraParameters, selectiveMedianFilter
from .schema import procParams, printOptions

#libcuda functions
try:
	from .libcudawrapper import deskewGPU as deskew
	from .libcudawrapper import affineGPU as affine
	from .libcudawrapper import quickDecon as decon
	from .libcudawrapper import rotateGPU as rotate
	from .libcudawrapper import quickCamcor as camcor
except Exception:
	pass
