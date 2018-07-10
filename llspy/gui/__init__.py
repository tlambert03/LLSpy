from PyQt5 import QtCore
import logging

# platform independent settings file
QtCore.QCoreApplication.setOrganizationName("llspy")
QtCore.QCoreApplication.setOrganizationDomain("llspy.com")
QtCore.QCoreApplication.setApplicationName("LLSpy")
SETTINGS  = QtCore.QSettings()
# clear with:
# killall -u talley cfprefsd

logger = logging.getLogger()  # set root logger
# lhStdout = logger.handlers[0]   # grab console handler so we can delete later
ch = logging.StreamHandler()    # create new console handler
ch.setLevel(logging.DEBUG)      # with desired logging level
ch.addFilter(logging.Filter('llspy'))  # and any filters
logger.addHandler(ch)           # add it to the root logger
# logger.removeHandler(lhStdout)  # and delete the original streamhandler
