try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"
import logging
import sys

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(levelname)s:%(name)s | %(message)s")


if "--debug" in sys.argv:
    logging.basicConfig(
        level=logging.DEBUG, format="%(levelname)s:%(name)s | %(message)s"
    )
if "install" in sys.argv:
    logging.getLogger("llspy.libcudawrapper").setLevel(logging.CRITICAL)


# libcuda functions
try:
    pass
except Exception:
    pass
