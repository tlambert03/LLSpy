from __future__ import absolute_import, print_function

import sys
import logging
# import multiprocessing

from llspy.gui import dialogs, settings, SETTINGS, mainwindow, qtlogger, exceptions
from llspy import util, __version__
from PyQt5 import QtWidgets, QtGui
from distutils.version import StrictVersion


logger = logging.getLogger()  # set root logger
logger.setLevel(logging.DEBUG)
lhStdout = logger.handlers[0]   # grab console handler so we can delete later
ch = logging.StreamHandler()    # create new console handler
ch.setLevel(logging.ERROR)      # with desired logging level
# ch.addFilter(logging.Filter('llspy'))  # and any filters
logger.addHandler(ch)           # add it to the root logger
logger.removeHandler(lhStdout)  # and delete the original streamhandler


def test():
    import time
    APP = QtWidgets.QApplication(sys.argv)
    mainGUI = mainwindow.main_GUI()
    time.sleep(1)
    mainGUI.close()
    sys.exit(0)


def main():
        # freeze multiprocessing support for pyinstaller
        # multiprocessing.freeze_support()

        # create the APP instance
        APP = QtWidgets.QApplication(sys.argv)
        appicon = QtGui.QIcon(util.getAbsoluteResourcePath('gui/logo_dark.png'))
        APP.setWindowIcon(appicon)

        # register icon with windows
        if sys.platform.startswith('win32'):
            import ctypes
            myappid = 'llspy.LLSpy.' + __version__
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        # set up the logfile
        fh = qtlogger.LogFileHandler(maxBytes=100000, backupCount=2)
        logger.addHandler(fh)
        fh.setLevel(logging.DEBUG)
        logger.info('>' * 10 + '  LLSpy STARTUP  ' + '<' * 10)

        # instantiate the main window widget
        mainGUI = mainwindow.main_GUI()
        mainGUI.setWindowIcon(appicon)

        # instantiate the execption handler
        exceptionHandler = exceptions.ExceptionHandler()
        sys.excepthook = exceptionHandler.handler
        exceptionHandler.errorMessage.connect(mainGUI.show_error_window)

        # try to import slmgen and add to tools menu
        try:
            from slmgen import SLMdialog
            mainGUI.slmDialog = SLMdialog(mainGUI)
            mainGUI.actionSLMwindow = QtWidgets.QAction(mainGUI)
            mainGUI.actionSLMwindow.setObjectName("actionSLMwindow")
            mainGUI.menuTools.addAction(mainGUI.actionSLMwindow)
            mainGUI.actionSLMwindow.setText("SLM Pattern Generator")
            mainGUI.actionSLMwindow.triggered.connect(mainGUI.slmDialog.show)
        except ImportError:
            logger.error('Could not import slmgen. Cannot add SLM Generator to Tools menu.')

        # request permission to send error reports
        if not SETTINGS.value('error_permission_requested', False):
            box = QtWidgets.QMessageBox()
            box.setWindowTitle('Help improve LLSpy')
            box.setText('Thanks for using LLSpy.\n\nIn order to improve the '
                        "stability of LLSpy, we'd like to send automatic "
                        'error and crash logs.\n\nNo personal '
                        'information is included and the full error-reporting '
                        'code can be viewed in llspy.gui.exceptions. '
                        'Thanks for your help!\n')
            box.setIcon(QtWidgets.QMessageBox.Question)
            box.addButton(QtWidgets.QMessageBox.Ok)
            box.setDefaultButton(QtWidgets.QMessageBox.Ok)
            pref = QtWidgets.QCheckBox("Send anonymous error logs")
            box.setCheckBox(pref)

            def setOptOut(value):
                SETTINGS.value(settings.ALLOW_BUGREPORT.key, True if value else False)

            pref.stateChanged.connect(setOptOut)
            box.exec_()
            SETTINGS.setValue('error_permission_requested', True)

        # if we crashed last time, send a bug report (if allowed)
        if (SETTINGS.value('cleanExit', False) and
                SETTINGS.value(settings.ALLOW_BUGREPORT.key, True)):
            logger.warning('LLSpy failed to exit cleanly on the previous session')
            try:
                with open(qtlogger.LOGPATH, 'r') as f:
                    crashlog = f.read()
                    exceptions.client.captureMessage('LLSpyGUI Bad Exit\n\n' + crashlog)
            except Exception:
                pass

        # check for updates
        if SETTINGS.value(settings.CHECK_UPDATES.key, True):
            try:
                from binstar_client import Binstar
                client = Binstar()
                llsinfo = client.package('talley', 'llspy')
                newestVersion = llsinfo['latest_version']
                if StrictVersion(newestVersion) > StrictVersion(__version__):
                    dialogs.NewVersionDialog(newestVersion).exec_()
            except Exception as e:
                logger.error('Could not check for updates: ', str(e))

        # check to see if the cudaDeconv binary is valid, and alert if not
        try:
            from llspy import cudabinwrapper
            binary = cudabinwrapper.get_bundled_binary()
            logger.info(cudabinwrapper.CUDAbin(binary).list_gpus())
            # if not llspy.nGPU() > 0:
            #     QtWidgets.QMessageBox.warning(mainGUI, "No GPUs detected!",
            #         "cudaDeconv found no "
            #         "CUDA-capable GPUs.\n\n Preview/Processing will likely not work.",
            #         QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton)
        except Exception:
            pass
            # QtWidgets.QMessageBox.warning(
            #     mainGUI, "No binary detected!",
            #     'Unable to detect bundled cudaDeconv binary. We will not be able'
            #     ' to do much without it.\n\n'
            #     'The cudaDeconv.exe program is owned by HHMI Janelia Research Campus, '
            #     'and access to that program can be arranged via a license agreement with them. '
            #     'Please contact innovation@janelia.hhmi.org.\n\n'
            #     'More info in the documentation at llspy.readthedocs.io',
            #     QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton)

        SETTINGS.setValue('cleanExit', False)
        SETTINGS.sync()
        sys.exit(APP.exec_())


if __name__ == '__main__':
    test()

