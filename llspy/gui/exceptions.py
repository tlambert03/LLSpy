from llspy import schema
from llspy.cudabinwrapper import gpulist, CUDAbinException
from qtpy import QtCore, QT_VERSION
import sentry_sdk
from sentry_sdk.integrations.logging import ignore_logger
import traceback
import llspy
import sys
import platform
import re
import os
import uuid
import logging

logger = logging.getLogger(__name__)

try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen

_OPTOUT = False

tags = {}
env = "development"
if hasattr(sys, "_MEIPASS"):
    env = "pyinstaller"
elif "CONDA_PREFIX" in os.environ:
    env = "conda"


def fetch_package_version(dist_name):
    """
    >>> fetch_package_version('sentry')
    """
    try:
        # Importing pkg_resources can be slow, so only import it
        # if we need it.
        import pkg_resources
    except ImportError:
        # pkg_resource is not available on Google App Engine
        raise NotImplementedError(
            "pkg_resources is not available " "on this Python install"
        )
    dist = pkg_resources.get_distribution(dist_name)
    return dist.version


def fetch_git_sha(path, head=None):
    """
    >>> fetch_git_sha(os.path.dirname(__file__))
    """
    if not head:
        head_path = os.path.join(path, ".git", "HEAD")
        if not os.path.exists(head_path):
            raise Exception("Cannot identify HEAD for git repository at %s" % (path,))

        with open(head_path, "r") as fp:
            head = str(fp.read()).strip()

        if head.startswith("ref: "):
            head = head[5:]
            revision_file = os.path.join(path, ".git", *head.split("/"))
        else:
            return head
    else:
        revision_file = os.path.join(path, ".git", "refs", "heads", head)

    if not os.path.exists(revision_file):
        if not os.path.exists(os.path.join(path, ".git")):
            raise Exception(
                "%s does not seem to be the root of a git repository" % (path,)
            )

        packed_file = os.path.join(path, ".git", "packed-refs")
        if os.path.exists(packed_file):
            with open(packed_file) as fh:
                for line in fh:
                    line = line.rstrip()
                    if line and line[:1] not in ("#", "^"):
                        try:
                            revision, ref = line.split(" ", 1)
                        except ValueError:
                            continue
                        if ref == head:
                            return str(revision)

        raise Exception('Unable to find ref to head "%s" in repository' % (head,))

    with open(revision_file) as fh:
        return str(fh.read()).strip()


try:
    tags["revision"] = fetch_git_sha(
        os.path.dirname(os.path.dirname(sys.modules["llspy"].__file__))
    )[:12]
except Exception:
    pass

if sys.platform.startswith("darwin"):
    tags["os"] = "OSX_{}".format(platform.mac_ver()[0])
elif sys.platform.startswith("win32"):
    tags["os"] = "Windows_{}".format(platform.win32_ver()[1])
else:
    tags["os"] = "{}".format(platform.linux_distribution()[0])

try:
    tags["gpu"] = ", ".join(gpulist())
except CUDAbinException:
    tags["gpu"] = "no_cudabin"
    logger.error("CUDAbinException: Could not get gpulist")

tags["pyqt"] = QT_VERSION
for p in ("numpy", "pyopencl", "pyopengl", "spimagine", "napari", "gputools", "llspy"):
    try:
        tags[p] = fetch_package_version(p)
    except Exception:
        pass

ip = ""
try:
    ip = re.search('"([0-9.]*)"', str(urlopen("http://ip.jsontest.com/").read())).group(
        1
    )
except Exception:
    pass

sentry_sdk.init(
    "https://95509a56f3a745cea2cd1d782d547916:e0dfd1659afc4eec83169b7c9bf66e33@sentry.io/221111",
    release=llspy.__version__,
    in_app_include=["llspy", "spimagine", "gputools"],
    environment=env,
)
with sentry_sdk.configure_scope() as scope:
    scope.user = {"id": uuid.getnode(), "ip_address": ip}
    for key, value in tags.items():
        scope.set_tag(key, value)

ignore_logger("OpenGL.GL.shaders")
ignore_logger("PIL.PngImagePlugin")


def camel2spaces(string):
    return re.sub(r"((?<=[a-z])[A-Z]|(?<!\A)[A-R,T-Z](?=[a-z]))", r" \1", string)


class LLSpyError(Exception):
    """Base class for exceptions in this module."""

    def __init__(self, msg=None, detail=""):
        if msg is None:
            msg = "An unexpected error occured in LLSpy"
        super(LLSpyError, self).__init__(msg)
        self.msg = msg
        self.detail = detail


class InvalidSettingsError(LLSpyError):
    """Exception raised when something is not set correctly in the GUI."""

    pass


class MissingBinaryError(LLSpyError):
    """Unable to find executable or shared library dependency."""

    pass


class RegistrationError(LLSpyError):
    """Unable to find executable or shared library dependency."""

    pass


class ExceptionHandler(QtCore.QObject):
    """General class to handle all raise exception errors in the GUI"""

    # error message, title, more info, detail (e.g. traceback)
    errorMessage = QtCore.Signal(str, str, str, str)

    def __init__(self):
        super(ExceptionHandler, self).__init__()

    def handler(self, etype, value, tb):
        err_info = (etype, value, tb)
        if isinstance(value, LLSpyError):
            self.handleLLSpyError(*err_info)
        elif etype.__module__ == "voluptuous.error":
            self.handleSchemaError(*err_info)
        elif "0xe06d7363" in str(value).lower():
            self.handleCUDA_CL_Error(*err_info)
        else:  # uncaught exceptions go to sentry
            if not _OPTOUT:
                logger.debug("Sending bug report")
                client.captureException(err_info)
            self.errorMessage.emit(str(value), "", "", "")
            print("!" * 50)
            traceback.print_exception(*err_info)

    def handleLLSpyError(self, etype, value, tb):
        tbstring = "".join(traceback.format_exception(etype, value, tb))
        title = camel2spaces(etype.__name__).strip(" Error")
        self.errorMessage.emit(value.msg, title, value.detail, tbstring)

    def handleSchemaError(self, etype, value, tb):
        # when app raises uncaught exception, print info
        # traceback.print_exc()
        if etype.__module__ == "voluptuous.error":
            msgSplit = str(value).split("for dictionary value @ data")
            customMsg = msgSplit[0].strip()
            if len(customMsg) and customMsg != "not a valid value":
                self.errorMessage.emit(customMsg, "Validation Error", "", "")
            else:
                errorKey = msgSplit[1].split("'")[1]
                gotValue = msgSplit[1].split("'")[3]
                schemaDefaults = schema.__defaults__
                itemDescription = schemaDefaults[errorKey][1]
                report = "Not a valid value for: {}\n\n".format(errorKey)
                report += "({})".format(itemDescription)
                self.errorMessage.emit(
                    report, "Got value: {}".format(gotValue), "", "", ""
                )

    def handleCUDA_CL_Error(self, etype, value, tb):
        if not _OPTOUT:
            logger.debug("Sending bug report")
            client.captureException((etype, value, tb))
        tbstring = "".join(traceback.format_exception(etype, value, tb))
        self.errorMessage.emit(
            "Sorry, it looks like CUDA and OpenCL are not "
            "getting along on your system",
            "CUDA/OpenCL clash",
            "If you continue to get this error, please "
            'click the "disable Spimagine" checkbox in the config tab '
            "and restart LLSpy.  To report this bug or get updates on a fix, "
            "please go to https://github.com/tlambert03/LLSpy/issues/2 and "
            "include your system configuration in any reports.  Thanks!",
            tbstring,
        )
