from llspy import schema
from PyQt5 import QtCore
import traceback
import llspy
import sys
import platform
import re
import os
import uuid
from raven import Client, fetch_git_sha, fetch_package_version, breadcrumbs

_OPTOUT = False


tags = {}
env = 'development'
if hasattr(sys, '_MEIPASS'):
    env = 'pyinstaller'
elif 'CONDA_PREFIX' in os.environ:
    env = 'conda'

try:
    tags['revision'] = fetch_git_sha(os.path.dirname(
                    os.path.dirname(sys.modules['llspy'].__file__)))[:12]
except Exception:
    pass

if sys.platform.startswith('darwin'):
    tags['os'] = 'OSX_{}'.format(platform.mac_ver()[0])
elif sys.platform.startswith('win32'):
    tags['os'] = 'Windows_{}'.format(platform.win32_ver()[1])
else:
    tags['os'] = '{}'.format(platform.linux_distribution()[0])

try:  # lots of overhead just to get GPU version?
    import gputools
    tags['gpu'] = gputools.get_device().device.platform.name + '_' + gputools.get_device().device.name
except Exception:
    pass

tags['pyqt'] = QtCore.QT_VERSION_STR
for p in ('numpy', 'pyopencl', 'pyopengl', 'spimagine', 'gputools'):
    try:
        tags[p] = fetch_package_version(p)
    except Exception:
        pass


client = Client('https://95509a56f3a745cea2cd1d782d547916:e0dfd1659afc4eec83169b7c9bf66e33@sentry.io/221111',
                release=llspy.__version__,
                include_paths=['llspy', 'spimagine', 'gputools'],
                environment=env,
                tags=tags)
client.context.merge({'user':
   {
    # 'username': 'talley',
    'id': uuid.getnode(),
    # 'email': 'example@example.com',
    # 'ip_address':11.111.111.111}
   }
})
breadcrumbs.ignore_logger('OpenGL.GL.shaders')
breadcrumbs.ignore_logger('PIL.PngImagePlugin')

def camel2spaces(string):
    return re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-R,T-Z](?=[a-z]))', r' \1', string)


class LLSpyError(Exception):
    """Base class for exceptions in this module."""

    def __init__(self, msg=None, detail=''):
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


class ExceptionHandler(QtCore.QObject):
    """General class to handle all raise exception errors in the GUI"""

    # error message, title, more info, detail (e.g. traceback)
    errorMessage = QtCore.pyqtSignal(str, str, str, str)

    def __init__(self):
        super(ExceptionHandler, self).__init__()

    def handler(self, etype, value, tb):
        err_info = (etype, value, tb)
        if isinstance(value, LLSpyError):
            self.handleLLSpyError(*err_info)
        elif etype.__module__ == 'voluptuous.error':
            self.handleSchemaError(*err_info)
        else:  # uncaught exceptions go to sentry
            if not _OPTOUT:
                print("sending bug report")
                client.captureException(err_info)
            self.errorMessage.emit(str(value), '', '', '')
            print("!" * 50)
            traceback.print_exception(*err_info)

    def handleLLSpyError(self, etype, value, tb):
        tbstring = "".join(traceback.format_exception(etype, value, tb))
        title = camel2spaces(etype.__name__).strip(' Error')
        self.errorMessage.emit(value.msg, title, value.detail, tbstring)

    def handleSchemaError(self, etype, value, tb):
        # when app raises uncaught exception, print info
        # traceback.print_exc()
        if etype.__module__ == 'voluptuous.error':
            msgSplit = str(value).split('for dictionary value @ data')
            customMsg = msgSplit[0].strip()
            if len(customMsg) and customMsg != 'not a valid value':
                self.errorMessage.emit(customMsg, 'Validation Error', '', '')
            else:
                errorKey = msgSplit[1].split("'")[1]
                gotValue = msgSplit[1].split("'")[3]
                schemaDefaults = schema.__defaults__
                itemDescription = schemaDefaults[errorKey][1]
                report = "Not a valid value for: {}\n\n".format(errorKey)
                report += "({})".format(itemDescription)
                self.errorMessage.emit(report, "Got value: {}".format(gotValue), '', '', '')