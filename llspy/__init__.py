try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(levelname)s:%(name)s | %(message)s")

import sys

if "--debug" in sys.argv:
    logging.basicConfig(
        level=logging.DEBUG, format="%(levelname)s:%(name)s | %(message)s"
    )
if "install" in sys.argv:
    logging.getLogger("llspy.libcudawrapper").setLevel(logging.CRITICAL)


from . import config
from . import otf
from . import arrayfun
from .llsdir import LLSdir, preview, process, RegDir
from .settingstxt import LLSsettings as Settings
from .cudabinwrapper import CUDAbin, nGPU, get_bundled_binary, CUDAbinException
from .parse import parse_filename, filter_files
from .camera import CameraROI, CameraParameters, selectiveMedianFilter
from .schema import procParams, printOptions
from .util import imread, imsave, imshow

# libcuda functions
try:
    from .libcudawrapper import deskewGPU as deskew
    from .libcudawrapper import affineGPU as affine
    from .libcudawrapper import quickDecon as decon
    from .libcudawrapper import rotateGPU as rotate
    from .libcudawrapper import quickCamcor as camcor
except Exception:
    pass
