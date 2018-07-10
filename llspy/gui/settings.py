import logging
import inspect
import sys
from .helpers import getter_setter_onchange
from PyQt5 import QtCore
from collections import namedtuple

logger = logging.getLogger(__name__)

SETTINGS  = QtCore.QSettings()

SetTup = namedtuple('Setting', ['key', 'default', 'description'])

CONFIRM_ON_QUIT = SetTup('prefs/confirm_on_quit', True, 'Confirm when quitting with unprocessed items')
ALLOW_NO_SETTXT = SetTup('prefs/allow_no_settxt', True, 'Allow folders without settings.txt')
WARN_ITERS = SetTup('prefs/warn_iters', True, 'Ask whether to rename files when folder with "Iter_" is added')
SKIP_PROCESSED = SetTup('prefs/skip_processed', False, 'Skip folders that have already been processed')
SAVE_MIPS = SetTup('prefs/save_mips', False, 'Save any MIPs when reducing data folder to raw state')
# DISABLE_SPIMAGINE = SetTup('prefs/disable_spimagine', False, 'Disable spimagine viewer (in case of conflicts)')
CHECK_UPDATES = SetTup('prefs/check_updates', True, 'Check anaconda cloud for updates on startup')
ALLOW_BUGREPORT = SetTup('pref/allow_bugreport', True, "Allow anonymous bug reports with errors")

this = sys.modules[__name__]
SETTUPS = {k: v for k, v in this.__dict__.items() if isinstance(v, SetTup)}
for settup in SETTUPS.values():
    if not SETTINGS.contains(settup.key):
        SETTINGS.setValue(settup.key, settup.default)


def guisave(widget, qsettings):
    logger.info("Saving settings: {}".format(qsettings.fileName()))
    # Save geometry
    selfName = widget.objectName()
    qsettings.beginGroup('mainwindow')
    qsettings.setValue(selfName + '_size', widget.size())
    qsettings.setValue(selfName + '_pos', widget.pos())
    for name, obj in inspect.getmembers(widget):
        # if type(obj) is QComboBox:  # this works similar to isinstance, but missed some field... not sure why?
        get, _, _ = getter_setter_onchange(obj)
        value = get() if get else None
        if value is not None:
            qsettings.setValue(name, value)
    qsettings.endGroup()


def guirestore(widget, qsettings, default):
    logger.info("Restoring settings: {}".format(qsettings.fileName()))
    # Restore geometry
    selfName = widget.objectName()
    qsettings.beginGroup('mainwindow')
    try:
        widget.resize(qsettings.value(selfName + '_size', QtCore.QSize(500, 500)))
        widget.move(qsettings.value(selfName + '_pos', QtCore.QPoint(60, 60)))
    except Exception:
        pass
    for name, obj in inspect.getmembers(widget):
        try:
            _, setter, _ = getter_setter_onchange(obj)
            value = qsettings.value(name, default.value(name))
            setter(value) if value not in (None, '') else None
        except Exception:
            logger.warn('Unable to restore settings for object: {}'.format(name))
    qsettings.endGroup()

