from __future__ import absolute_import, print_function

try:
    import llspy
except ImportError:
    import os
    import sys

    thisDirectory = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(thisDirectory, os.pardir, os.pardir))
    import llspy

import llspy.gui.exceptions as err
from llspy.gui.qtlogger import LogFileHandler
from llspy.gui.mainwindow import main_GUI, sessionSettings

from PyQt5 import QtWidgets, QtGui

import os
import sys
import multiprocessing
import time
import json
from distutils.version import StrictVersion

try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen


import logging

logger = logging.getLogger()  # set root logger
logger.setLevel(logging.DEBUG)
lhStdout = logger.handlers[0]  # grab console handler so we can delete later
ch = logging.StreamHandler()  # create new console handler
ch.setLevel(logging.ERROR)  # with desired logging level
# ch.addFilter(logging.Filter('llspy'))  # and any filters
logger.addHandler(ch)  # add it to the root logger
logger.removeHandler(lhStdout)  # and delete the original streamhandler


def test():
    APP = QtWidgets.QApplication(sys.argv)
    mainGUI = main_GUI()
    # instantiate the execption handler
    time.sleep(0.1)
    mainGUI.close()
    sys.exit(0)


def main():
    # freeze multiprocessing support for pyinstaller
    multiprocessing.freeze_support()
    # create the APP instance
    APP = QtWidgets.QApplication(sys.argv)
    appicon = QtGui.QIcon(llspy.util.getAbsoluteResourcePath("gui/logo_dark.png"))
    APP.setWindowIcon(appicon)
    # register icon with windows
    if sys.platform.startswith("win32"):
        import ctypes

        myappid = "llspy.LLSpy." + llspy.__version__
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    firstRun = False if len(sessionSettings.childKeys()) else True

    # set up the logfile
    fh = LogFileHandler(maxBytes=100000, backupCount=2)
    logger.addHandler(fh)
    fh.setLevel(logging.DEBUG)
    logger.info(">" * 10 + "  LLSpy STARTUP  " + "<" * 10)

    # instantiate the main window widget
    mainGUI = main_GUI()
    mainGUI.setWindowIcon(appicon)

    # try to import slmgen and add to tools menu
    try:
        from slmgen import SLMdialog

        mainGUI.slmDialog = SLMdialog(mainGUI)
        mainGUI.actionSLMwindow = QtWidgets.QAction(mainGUI)
        mainGUI.actionSLMwindow.setObjectName("actionSLMwindow")
        mainGUI.menuTools.addAction(mainGUI.actionSLMwindow)
        mainGUI.actionSLMwindow.setText("SLM Pattern Generator")
        # mainGUI.slmPatternGeneratorButton.clicked.connect(mainGUI.slmDialog.show)
        mainGUI.actionSLMwindow.triggered.connect(mainGUI.slmDialog.show)
    except ImportError as e:
        logger.error("Could not import slmgen. Cannot add SLM Generator to Tools menu.")

    if firstRun:
        box = QtWidgets.QMessageBox()
        box.setWindowTitle("Help improve LLSpy")
        box.setText(
            "Thanks for using LLSpy.\n\nIn order to improve the stability of LLSpy, uncaught "
            "exceptions are automatically sent to sentry.io\n\nNo personal "
            "information is included in this report.  The error-reporting "
            "code can be seen in llspy.gui.exceptions.  If want to disable"
            "automatic error reporting, you may opt out below.\n"
        )
        box.setIcon(QtWidgets.QMessageBox.Information)
        box.addButton(QtWidgets.QMessageBox.Ok)
        box.setDefaultButton(QtWidgets.QMessageBox.Ok)
        pref = QtWidgets.QCheckBox("Opt out of automatic error reporting.")
        box.setCheckBox(pref)

        def setOptOut(value):
            err._OPTOUT = True if value else False
            mainGUI.errorOptOutCheckBox.setChecked(True)

        pref.stateChanged.connect(setOptOut)
        box.exec_()

    # instantiate the execption handler
    exceptionHandler = err.ExceptionHandler()
    sys.excepthook = exceptionHandler.handler
    exceptionHandler.errorMessage.connect(mainGUI.show_error_window)

    # if we crashed last time, send a bug report (if allowed)
    if not firstRun and not sessionSettings.value("cleanExit", type=bool):
        from click import get_app_dir

        logger.error("LLSpy failed to exit cleanly on the previous session")
        if not err._OPTOUT:
            _LOGPATH = os.path.join(get_app_dir("LLSpy"), "llspygui.log")
            try:
                with open(_LOGPATH, "r") as f:
                    crashlog = f.read()
                    err.client.captureMessage("LLSpyGUI Bad Exit\n\n" + crashlog)
            except Exception:
                pass

    # check to see if the cudaDeconv binary is valid, and alert if not
    try:
        binary = llspy.cudabinwrapper.get_bundled_binary()
        logger.info(llspy.cudabinwrapper.CUDAbin(binary).list_gpus())
        # if not llspy.nGPU() > 0:
        #     QtWidgets.QMessageBox.warning(mainGUI, "No GPUs detected!",
        #         "cudaDeconv found no "
        #         "CUDA-capable GPUs.\n\n Preview/Processing will likely not work.",
        #         QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton)
    except llspy.CUDAbinException:
        QtWidgets.QMessageBox.warning(
            mainGUI,
            "No binary detected!",
            "Unable to detect bundled cudaDeconv binary. We will not be able"
            " to do much without it.\n\n"
            "As of version 0.4.2, cudaDeconv should now be included in LLSpy.  "
            'Try installing via "conda update -c talley llspylibs"',
            QtWidgets.QMessageBox.Ok,
            QtWidgets.QMessageBox.NoButton,
        )

    projectURL = "https://api.github.com/repos/tlambert03/LLSpy/releases/latest"
    try:
        newestVersion = json.loads(urlopen(projectURL).read().decode("utf-8"))[
            "tag_name"
        ]
        if StrictVersion(newestVersion) > StrictVersion(llspy.__version__):
            QtWidgets.QMessageBox.information(
                mainGUI,
                "Newer Version Available!",
                "Update available: v%s\n\nYou are using v%s\n\nIf you are using "
                'anaconda, you may update by typing "conda update -c talley llspy" '
                "at the anaconda prompt" % (newestVersion, llspy.__version__),
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.NoButton,
            )
    except Exception:
        pass

    #         try:
    #             llspy.libcudawrapper.cudaLib.Affine_interface_RA
    #         except AttributeError:
    #             msg = '''
    # LLSpy v0.3.0 added some registration features that require an \
    # update to your libcudaDeconv.{} library.  Without it you may \
    # experience crashes or unexpected behavior.\n\nPlease grab the newest \
    # version in the llspy_extra folder in the dropbox and install in \
    # the usual way:\nlls install /path/to/llspy_extra
    # '''
    #             if sys.platform.startswith('win32'):
    #                 libext = 'dll'
    #             elif sys.platform.startswith('darwin'):
    #                 libext = 'dylib'
    #             else:
    #                 libext = 'so'
    #             QtWidgets.QMessageBox.warning(mainGUI, "Outdated libcudaDeconv Library!",
    #                 msg.format(libext),
    #                 QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton)

    # ######################## TESTING
    # def tester():
    #     pass

    # mainGUI.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Shift+E"), mainGUI)
    # mainGUI.shortcut.activated.connect(tester)
    # #############################

    sessionSettings.setValue("cleanExit", False)
    sessionSettings.sync()
    sys.exit(APP.exec_())


if __name__ == "__main__":
    main()
