#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function, division

import os
import os.path as osp
import logging
from llspy.gui import (camcalibgui, implist, dialogs, qtlogger, folderqueue,
                       regtab, actions, exceptions, preview)
from llspy.gui.helpers import guisave, guirestore, progress_gradient
# from fiducialreg.fiducialreg import RegFile, RegistrationError
from PyQt5 import QtCore, QtGui, uic
from PyQt5 import QtWidgets as QtW
from llspy.gui.settings import sessionSettings, programDefaults

logger = logging.getLogger()  # set root logger
# logger.setLevel(logging.DEBUG)
lhStdout = logger.handlers[0]   # grab console handler so we can delete later
ch = logging.StreamHandler()    # create new console handler
ch.setLevel(logging.ERROR)      # with desired logging level
# ch.addFilter(logging.Filter('llspy'))  # and any filters
logger.addHandler(ch)           # add it to the root logger
logger.removeHandler(lhStdout)  # and delete the original streamhandler


Ui_Main_GUI = uic.loadUiType(osp.join(os.path.dirname(__file__), 'main_gui.ui'))[0]
# form_class = uic.loadUiType('./llspy/gui/main_gui.ui')[0]  # for debugging


class main_GUI(QtW.QMainWindow, Ui_Main_GUI, regtab.RegistrationTab,
               actions.LLSpyActions, preview.HasPreview):
    """docstring for main_GUI"""

    def __init__(self, parent=None):
        super(main_GUI, self).__init__(parent)
        self.setupUi(self)  # method inherited from form_class to init UI
        self.setWindowTitle("LLSpy :: Lattice Light Sheet Processing")
        regtab.RegistrationTab.__init__(self)

        self.LLSItemThreads = []
        self.compressionThreads = []
        self.argQueue = []  # holds all argument lists that will be sent to threads
        self.aborted = False  # current abort status
        self.spimwins = []
        self._eta = 0

        # delete and reintroduce custom folderqueue.LLSDragDropTable and imp window
        self.listbox.setParent(None)
        self.listbox = folderqueue.LLSDragDropTable(self)
        self.listbox.status_update.connect(self.statusBar.showMessage)
        self.listbox.item_starting.connect(self.initProgress)
        self.listbox.step_finished.connect(self.incrementProgress)
        self.listbox.work_finished.connect(self.onProcessFinished)
        self.listbox.eta_update.connect(self.set_eta)
        self.processSplitter.insertWidget(0, self.listbox)
        self.impListWidget.setParent(None)
        self.impContainer = implist.ImpListContainer()
        self.impListWidget = self.impContainer.list
        self.processSplitter.addWidget(self.impContainer)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateClock)

        handler = qtlogger.NotificationHandler()
        handler.emitSignal.connect(self.log.append)
        logger.addHandler(handler)

        self.camcorDialog = camcalibgui.CamCalibDialog()
        self.genFlashParams.clicked.connect(self.camcorDialog.show)
        self.actionCamera_Calibration.triggered.connect(self.camcorDialog.show)

        # connect buttons
        self.previewButton.clicked.connect(self.onPreview)
        self.processButton.clicked.connect(self.onProcess)
        self.errorOptOutCheckBox.stateChanged.connect(self.toggleOptOut)

        # def toggleActiveGPU(val):
        #     gpunum = int(self.sender().objectName().strip('useGPU_'))
        #     app = QtCore.QCoreApplication.instance()
        #     if not hasattr(app, 'gpuset'):
        #         app.gpuset = set()
        #     if val:
        #         app.gpuset.add(gpunum)
        #         logger.debug("GPU {} added to gpuset.".format(gpunum))
        #     else:
        #         if gpunum in app.gpuset:
        #             app.gpuset.remove(gpunum)
        #             logger.debug("GPU {} removed from gpuset.".format(gpunum))
        #     logger.debug("GPUset now: {}".format(app.gpuset))

        # add GPU checkboxes and add
        # try:
        #     app = QtCore.QCoreApplication.instance()
        #     if not hasattr(app, 'gpuset'):
        #         app.gpuset = set()
        #     gpulist = llspy.cudabinwrapper.gpulist()
        #     if len(gpulist):
        #         for i, gpu in enumerate(gpulist):
        #             box = QtW.QCheckBox(self.tab_config)
        #             box.setChecked(True)
        #             box.setObjectName('useGPU_{}'.format(i))
        #             box.setText(gpu.strip('GeForce'))
        #             box.stateChanged.connect(toggleActiveGPU)
        #             app.gpuset.add(i)
        #             self.gpuGroupBoxLayout.addWidget(box)
        #     else:
        #         label = QtW.QLabel(self.tab_config)
        #         label.setText('No CUDA-capabled GPUs detected')
        #         self.gpuGroupBoxLayout.addWidget(label)

        # except llspy.cudabinwrapper.CUDAbinException as e:
        #     logger.warn(e)
        #     pass

        # connect actions

        # set validators for cRange and tRange fields
        ctrangeRX = QtCore.QRegExp(r"(\d[\d-]*,?)*")  # could be better
        ctrangeValidator = QtGui.QRegExpValidator(ctrangeRX)
        self.processCRangeLineEdit.setValidator(ctrangeValidator)
        self.processTRangeLineEdit.setValidator(ctrangeValidator)
        self.previewCRangeLineEdit.setValidator(ctrangeValidator)
        self.previewTRangeLineEdit.setValidator(ctrangeValidator)

        self.disableSpimagineCheckBox.clicked.connect(
            lambda:
            QtW.QMessageBox.information(
                self, 'Restart Required',
                "Please quit and restart LLSpy for changes to take effect",
                QtW.QMessageBox.Ok))

        # connect worker signals and slots

        self.RegCalib_channelRefModeCombo.clear()
        self.RegCalib_channelRefCombo.clear()

        # Restore settings from previous session and show ready status
        guirestore(self, sessionSettings, programDefaults)

        self.RegCalibPathLineEdit.setText('')
        self.RegFilePath.setText('')

        self.clock.display("00:00:00")
        self.statusBar.showMessage('Ready')

        if not preview._SPIMAGINE_IMPORTED:
            self.prevBackendMatplotlibRadio.setChecked(True)
            self.prevBackendSpimagineRadio.setDisabled(True)
            self.prevBackendSpimagineRadio.setText("spimagine [unavailable]")

        self.show()
        self.raise_()

    # @QtCore.pyqtSlot(str)
    # def loadRegObject(self, path):
    #     if path in (None, ''):
    #         return
    #     if not os.path.exists(path):
    #         self.RegProcessPathLineEdit.setText('')
    #         return
    #     try:
    #         RO = llspy.llsdir.get_regObj(path)
    #     except json.decoder.JSONDecodeError as e:
    #         self.RegProcessPathLineEdit.setText('')
    #         raise exceptions.RegistrationError("Failed to parse registration file", str(e))
    #     except RegistrationError as e:
    #         self.RegProcessPathLineEdit.setText('')
    #         raise exceptions.RegistrationError('Failed to load registration calibration data', str(e))
    #     finally:
    #         self.RegProcessChannelRefModeCombo.clear()
    #         self.RegProcessChannelRefCombo.clear()

    #     self.RegProcessChannelRefCombo.addItems([str(r) for r in RO.waves])
    #     modeorder = ['2step', 'translation', 'rigid', 'similarity', 'affine',
    #                  'cpd_affine', 'cpd_rigid', 'cpd_similarity', 'cpd_2step']
    #     # RegDirs allow all modes, RegFiles only allow modes that were calculated
    #     # at the time of file creation
    #     if isinstance(RO, llspy.RegDir):
    #         modes = [m.title().replace('Cpd', 'CPD') for m in modeorder]
    #     elif isinstance(RO, RegFile):
    #         modes = [m.lower() for m in RO.modes]
    #         modes = [m.title().replace('Cpd', 'CPD') for m in modeorder if m in modes]
    #     self.RegProcessChannelRefModeCombo.addItems(modes)

    # def setFiducialData(self):
    #     path = QtW.QFileDialog.getExistingDirectory(
    #         self, 'Set Registration Calibration Directory',
    #         '', QtW.QFileDialog.ShowDirsOnly)
    #     if path is None or path == '':
    #         return
    #     else:
    #         self.RegProcessPathLineEdit.setText(path)

    # def loadProcessRegFile(self, file=None):
    #     if not file:
    #         file = QtW.QFileDialog.getOpenFileName(
    #             self, 'Choose registration file ', os.path.expanduser('~'),
    #             "Text Files (*.reg *.txt *.json)")[0]
    #         if file is None or file is '':
    #             return
    #     self.RegProcessPathLineEdit.setText(file)

    def initProgress(self, maxval):
        """ set progress bar to zero and intialize with maxval """
        self.progressBar.setStyleSheet(progress_gradient())
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(maxval)

    def incrementProgress(self):
        """ bump up the progress bar by one step """
        self.progressBar.setValue(self.progressBar.value() + 1)

    @QtCore.pyqtSlot(int, int, int)  # return code, numdone, numsk
    def onProcessFinished(self, retcode, numfinished, numskipped):
        """ called when listbox queue is completely finished or aborted """
        self.enableProcessButton()
        self.timer.stop()
        self.clock.display("00:00:00")
        if not retcode:  # means aborted
            self.statusBar.showMessage('Aborted')
            self.progressBar.setStyleSheet(progress_gradient('#FF8C00', '#FFA500'))
            return

        summary = 'Successfully Processed {} Items!'.format(numfinished)
        if numskipped:
            summary += ' ({} items were skipped due to errors)'.format(numskipped)
            self.progressBar.setStyleSheet(progress_gradient('#F22', '#F66'))
        else:
            self.progressBar.setStyleSheet(progress_gradient('#0B0', '#4B4'))
        self.statusBar.showMessage(summary)

    def onProcess(self):
        # prevent additional button clicks which processing
        self.disableProcessButton()
        self.listbox.startProcessing(self.impListWidget.getImpList())
        # start a timer in the main GUI to measure item processing time
        self.timer.start(1000)

    @QtCore.pyqtSlot(int)
    def set_eta(self, value):
        self._eta = value

    def updateClock(self):
        self._eta -= 1000
        if self._eta > 0:
            _d = QtCore.QTime(0, 0).addMSecs(self._eta).toString()
            self.clock.display(_d)

    def disableProcessButton(self):
        # turn Process button into a Cancel button and udpate menu items
        self.processButton.clicked.disconnect()
        self.processButton.setText('CANCEL')
        self.processButton.clicked.connect(self.sendAbort)
        self.processButton.setEnabled(True)
        self.actionRun.setDisabled(True)
        self.actionAbort.setEnabled(True)

    def sendAbort(self):
        self.listbox.abort_workers()
        self.processButton.setText('ABORTING...')
        self.processButton.setDisabled(True)

    def enableProcessButton(self):
        # change Process button back to "Process" and udpate menu items
        self.processButton.clicked.disconnect()
        self.processButton.clicked.connect(self.onProcess)
        self.processButton.setText('Process')
        self.processButton.setEnabled(True)
        self.actionRun.setEnabled(True)
        self.actionAbort.setDisabled(True)

    def toggleOptOut(self, value):
        exceptions._OPTOUT = True if value else False

    @QtCore.pyqtSlot(str, str, str, str)
    def show_error_window(self, errMsg, title=None, info=None, detail=None):
        self.msgBox = QtW.QMessageBox()
        if title is None or title is '':
            title = "LLSpy Error"
        self.msgBox.setWindowTitle(title)

        # self.msgBox.setTextFormat(QtCore.Qt.RichText)
        self.msgBox.setIcon(QtW.QMessageBox.Warning)
        self.msgBox.setText(errMsg)
        if info is not None and info is not '':
            self.msgBox.setInformativeText(info + '\n')
        if detail is not None and detail is not '':
            self.msgBox.setDetailedText(detail)
        self.msgBox.exec_()

    def closeEvent(self, event):
        ''' triggered when close button is clicked on main window '''
        if self.listbox.rowCount() and self.confirmOnQuitCheckBox.isChecked():
            msgbox = dialogs.MemorableMessageBox(
                'confirmOnQuit',
                "Always quit without confirmation",
                QtW.QMessageBox.Question,
                'Unprocessed items!',
                'You have unprocessed items.  Are you sure you want to quit?',
                QtW.QMessageBox.Yes | QtW.QMessageBox.No,
            )
            msgbox.setDefaultButton(msgbox.No)
            if msgbox.exec_() != msgbox.Yes:
                return

        # if currently processing, need to shut down threads...
        if self.listbox.inProcess:
            self.sendAbort()
            self.listbox.work_finished.connect(self.quitProgram)
            event.ignore()
        else:
            self.quitProgram()

    def quitProgram(self, save=True):
        if save:
            guisave(self, sessionSettings)
        sessionSettings.setValue('cleanExit', True)
        sessionSettings.sync()
        QtW.QApplication.quit()


if __name__ == '__main__':

    import sys

    APP = QtW.QApplication([])
    main = main_GUI()

    # instantiate the execption handler
    exceptionHandler = exceptions.ExceptionHandler()
    sys.excepthook = exceptionHandler.handler
    exceptionHandler.errorMessage.connect(main.show_error_window)

    main.show()
    sys.exit(APP.exec_())
