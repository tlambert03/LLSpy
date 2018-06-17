#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function, division

import json
import os
import os.path as osp
import numpy as np
import logging
import llspy
from llspy.gui import (workers, camcalibgui, implist, img_dialog, dialogs,
                       qtlogger, folderqueue, regtab, actions, exceptions)
from llspy.gui.helpers import (newWorkerThread, shortname, string_to_iterable,
                               guisave, guirestore)
from llspy import util
from fiducialreg.fiducialreg import RegFile, RegistrationError
from PyQt5 import QtCore, QtGui, uic
from PyQt5 import QtWidgets as QtW


logger = logging.getLogger()  # set root logger
logger.setLevel(logging.DEBUG)
# lhStdout = logger.handlers[0]   # grab console handler so we can delete later
ch = logging.StreamHandler()    # create new console handler
ch.setLevel(logging.ERROR)      # with desired logging level
# ch.addFilter(logging.Filter('llspy'))  # and any filters
logger.addHandler(ch)           # add it to the root logger
# logger.removeHandler(lhStdout)  # and delete the original streamhandler

_SPIMAGINE_IMPORTED = False

# import sys
# sys.path.append(osp.join(osp.abspath(__file__), os.pardir, os.pardir))

Ui_Main_GUI = uic.loadUiType(osp.join(os.path.dirname(__file__), 'main_gui.ui'))[0]
# form_class = uic.loadUiType('./llspy/gui/main_gui.ui')[0]  # for debugging

# platform independent settings file
QtCore.QCoreApplication.setOrganizationName("llspy")
QtCore.QCoreApplication.setOrganizationDomain("llspy.com")
sessionSettings = QtCore.QSettings("llspy", "llspyGUI")
defaultSettings = QtCore.QSettings("llspy", 'llspyDefaults')
# programDefaults are provided in guiDefaults.ini as a reasonable starting place
# this line finds the relative path depending on whether we're running in a
# pyinstaller bundle or live.
defaultINI = util.getAbsoluteResourcePath('gui/guiDefaults.ini')
programDefaults = QtCore.QSettings(defaultINI, QtCore.QSettings.IniFormat)

if not sessionSettings.value('disableSpimagineCheckBox', False, type=bool):
    try:
        # raise ImportError("skipping")
        with util.HiddenPrints():
            from spimagine import DataModel, NumpyData
            from spimagine.gui.mainwidget import MainWidget as spimagineWidget
            _SPIMAGINE_IMPORTED = True
    except ImportError as e:
        print(e)
        logger.error("could not import spimagine!  falling back to matplotlib")


def progress_gradient(start='#484DE7', finish='#787DFF'):
    a = """
    QProgressBar {
        border: 1px solid grey;
        border-radius: 3px;
        height: 20px;
        margin: 0px 0px 0px 5px;
    }

    QProgressBar::chunk:horizontal {
      background: qlineargradient(x1: 0, y1: 0.5, x2: 1, y2: 0.5,
                                  stop: 0 %s, stop: 1 %s);
    }
    """
    return a % (start, finish)


class main_GUI(QtW.QMainWindow, Ui_Main_GUI, regtab.RegistrationTab,
               actions.LLSpyActions):
    """docstring for main_GUI"""

    sig_abort_LLSworkers = QtCore.pyqtSignal()
    sig_processing_done = QtCore.pyqtSignal()

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

        # delete and reintroduce custom folderqueue.LLSDragDropTable and imp window
        self.listbox.setParent(None)
        self.listbox = folderqueue.LLSDragDropTable(self)
        self.listbox.status_update.connect(self.statusBar.showMessage)
        self.listbox.item_starting.connect(self.initProgress)
        self.listbox.step_finished.connect(self.incrementProgress)
        self.listbox.work_finished.connect(self.summarizeWork)
        self.processSplitter.insertWidget(0, self.listbox)
        self.impListWidget.setParent(None)
        self.impContainer = implist.ImpListContainer()
        self.impListWidget = self.impContainer.list
        self.processSplitter.addWidget(self.impContainer)

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

        self.sig_processing_done.connect(self.on_proc_finished)
        self.RegCalib_channelRefModeCombo.clear()
        self.RegCalib_channelRefCombo.clear()

        # Restore settings from previous session and show ready status
        guirestore(self, sessionSettings, programDefaults)

        self.RegCalibPathLineEdit.setText('')
        self.RegFilePath.setText('')

        self.clock.display("00:00:00")
        self.statusBar.showMessage('Ready')

        if not _SPIMAGINE_IMPORTED:
            self.prevBackendMatplotlibRadio.setChecked(True)
            self.prevBackendSpimagineRadio.setDisabled(True)
            self.prevBackendSpimagineRadio.setText("spimagine [unavailable]")

        self.show()
        self.raise_()

    @QtCore.pyqtSlot(str)
    def loadRegObject(self, path):
        if path in (None, ''):
            return
        if not os.path.exists(path):
            self.RegProcessPathLineEdit.setText('')
            return
        try:
            RO = llspy.llsdir.get_regObj(path)
        except json.decoder.JSONDecodeError as e:
            self.RegProcessPathLineEdit.setText('')
            raise exceptions.RegistrationError("Failed to parse registration file", str(e))
        except RegistrationError as e:
            self.RegProcessPathLineEdit.setText('')
            raise exceptions.RegistrationError('Failed to load registration calibration data', str(e))
        finally:
            self.RegProcessChannelRefModeCombo.clear()
            self.RegProcessChannelRefCombo.clear()

        self.RegProcessChannelRefCombo.addItems([str(r) for r in RO.waves])
        modeorder = ['2step', 'translation', 'rigid', 'similarity', 'affine',
                     'cpd_affine', 'cpd_rigid', 'cpd_similarity', 'cpd_2step']
        # RegDirs allow all modes, RegFiles only allow modes that were calculated
        # at the time of file creation
        if isinstance(RO, llspy.RegDir):
            modes = [m.title().replace('Cpd', 'CPD') for m in modeorder]
        elif isinstance(RO, RegFile):
            modes = [m.lower() for m in RO.modes]
            modes = [m.title().replace('Cpd', 'CPD') for m in modeorder if m in modes]
        self.RegProcessChannelRefModeCombo.addItems(modes)

    def setFiducialData(self):
        path = QtW.QFileDialog.getExistingDirectory(
            self, 'Set Registration Calibration Directory',
            '', QtW.QFileDialog.ShowDirsOnly)
        if path is None or path == '':
            return
        else:
            self.RegProcessPathLineEdit.setText(path)

    def loadProcessRegFile(self, file=None):
        if not file:
            file = QtW.QFileDialog.getOpenFileName(
                self, 'Choose registration file ', os.path.expanduser('~'),
                "Text Files (*.reg *.txt *.json)")[0]
            if file is None or file is '':
                return
        self.RegProcessPathLineEdit.setText(file)

    def initProgress(self, maxval):
        self.progressBar.setStyleSheet(progress_gradient())
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(maxval)

    def incrementProgress(self):
        # with no values, simply increment progressbar
        self.progressBar.setValue(self.progressBar.value() + 1)

    @QtCore.pyqtSlot(int, int, int)  # return code, numdone, numsk
    def summarizeWork(self, retcode, numfinished, numskipped):
        self.enableProcessButton()
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

    def onPreview(self):
        self.previewButton.setDisabled(True)
        self.previewButton.setText('Working...')
        if self.listbox.rowCount() == 0:
            QtW.QMessageBox.warning(
                self, "Nothing Added!",
                'Nothing to preview! Drop LLS experiment folders into the list',
                QtW.QMessageBox.Ok, QtW.QMessageBox.NoButton)
            self.previewButton.setEnabled(True)
            self.previewButton.setText('Preview')
            return

        # if there's only one item on the list show it
        if self.listbox.rowCount() == 1:
            firstRowSelected = 0
        # otherwise, prompt the user to select one
        else:
            selectedRows = self.listbox.selectionModel().selectedRows()
            if not len(selectedRows):
                QtW.QMessageBox.warning(
                    self, "Nothing Selected!",
                    "Please select an item (row) from the table to preview",
                    QtW.QMessageBox.Ok, QtW.QMessageBox.NoButton)
                self.previewButton.setEnabled(True)
                self.previewButton.setText('Preview')
                return
            else:
                # if they select multiple, chose the first one
                firstRowSelected = selectedRows[0].row()

        procTRangetext = self.previewTRangeLineEdit.text()
        procCRangetext = self.previewCRangeLineEdit.text()

        try:
            self.lastopts = self.getValidatedOptions()
        except Exception:
            self.previewButton.setEnabled(True)
            self.previewButton.setText('Preview')
            raise

        if procTRangetext:
            tRange = string_to_iterable(procTRangetext)
        else:
            tRange = [0]

        if procCRangetext:
            cRange = string_to_iterable(procCRangetext)
            if (self.lastopts['correctFlash'] and
                    sessionSettings.value('warnCameraCorPreview', True, type=bool)):
                box = QtW.QMessageBox()
                box.setWindowTitle('Note')
                box.setText(
                    "You have selected to preview a subset of channels, but "
                    "have also selected Flash camera correction.  Note that the camera "
                    "correction requires all channels to be enabled.  Preview will not "
                    "reflect accurate camera correction.")
                box.setIcon(QtW.QMessageBox.Warning)
                box.addButton(QtW.QMessageBox.Ok)
                box.setDefaultButton(QtW.QMessageBox.Ok)
                pref = QtW.QCheckBox("Don't remind me.")
                box.setCheckBox(pref)

                def dontRemind(value):
                    if value:
                        sessionSettings.setValue('warnCameraCorPreview', False)
                    else:
                        sessionSettings.setValue('warnCameraCorPreview', True)
                    sessionSettings.sync()

                pref.stateChanged.connect(dontRemind)
                box.exec_()
        else:
            cRange = None  # means all channels

        self.previewPath = self.listbox.getPathByIndex(firstRowSelected)
        obj = self.listbox.getLLSObjectByPath(self.previewPath)

        if not obj.parameters.isReady():
            self.previewButton.setEnabled(True)
            self.previewButton.setText('Preview')
            raise exceptions.InvalidSettingsError(
                "Parameters are incomplete for this item. "
                "Please add any missing/higlighted parameters.")

        if not os.path.exists(self.previewPath):
            self.statusBar.showMessage(
                'Skipping! path no longer exists: {}'.format(self.previewPath), 5000)
            self.statusBar.showMessage(
                'Skipping! path no longer exists: {}'.format(self.previewPath), 5000)
            self.listbox.removePath(self.previewPath)
            self.previewButton.setEnabled(True)
            self.previewButton.setText('Preview')
            return

        w, thread = newWorkerThread(
            workers.TimePointWorker, obj, tRange, cRange, self.lastopts,
            workerConnect={
                'previewReady': self.displayPreview,
                'updateCrop': self.updateCrop,
            },
            start=True)

        w.finished.connect(lambda: self.previewButton.setEnabled(True))
        w.finished.connect(lambda: self.previewButton.setText('Preview'))
        self.previewthreads = (w, thread)

    @QtCore.pyqtSlot(int, int)
    def updateCrop(self, width, offset):
        self.cropWidthSpinBox.setValue(width)
        self.cropShiftSpinBox.setValue(offset)

    @QtCore.pyqtSlot(np.ndarray, float, float, dict)
    def displayPreview(self, array, dx, dz, params=None):
        if self.prevBackendSpimagineRadio.isChecked() and _SPIMAGINE_IMPORTED:

            if np.squeeze(array).ndim > 4:
                arrays = [array[:, i] for i in range(array.shape[1])]
            else:
                arrays = [np.squeeze(array)]

            for arr in arrays:

                datamax = arr.max()
                datamin = arr.min()
                dataRange = datamax - datamin
                vmin_init = datamin - dataRange * 0.02
                vmax_init = datamax * 0.75

                win = spimagineWidget()
                win.setAttribute(QtCore.Qt.WA_DeleteOnClose)
                win.setModel(DataModel(NumpyData(arr)))
                win.setWindowTitle(shortname(self.previewPath))
                win.transform.setStackUnits(dx, dx, dz)
                win.transform.setGamma(0.9)
                win.transform.setMax(vmax_init)
                win.transform.setMin(vmin_init)
                win.transform.setZoom(1.3)

                # enable slice view by default
                win.sliceWidget.checkSlice.setCheckState(2)
                win.sliceWidget.glSliceWidget.interp = False
                win.checkSliceView.setChecked(True)
                win.sliceWidget.sliderSlice.setValue(int(arr.shape[-3] / 2))

                # win.impListView.add_image_processor(myImp())
                # win.impListView.add_image_processor(imageprocessor.LucyRichProcessor())
                win.setLoopBounce(False)
                win.settingsView.playInterval.setText('100')

                win.resize(1500, 900)
                win.show()
                win.raise_()

                # mainwidget doesn't know what order the colormaps are in
                colormaps = win.volSettingsView.colormaps
                win.volSettingsView.colorCombo.setCurrentIndex(colormaps.index('inferno'))
                win.sliceWidget.glSliceWidget.set_colormap('grays')

                # could have it rotating by default
                # win.rotate()

                self.spimwins.append(win)

        else:
            # FIXME:  pyplot should not be imported in pyqt
            # use https://matplotlib.org/2.0.0/api/backend_qt5agg_api.html

            win = img_dialog.ImgDialog(array, info=params, title=shortname(self.previewPath))
            self.spimwins.append(win)

    def onProcess(self):
        # prevent additional button clicks which processing
        self.disableProcessButton()
        self.listbox.startProcessing(self.impListWidget.getImpList())
        # start a timer in the main GUI to measure item processing time
        self.timer = QtCore.QTime()
        self.timer.restart()

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

    @QtCore.pyqtSlot()
    def on_proc_finished(self):
        # reinit statusbar and clock
        self.statusBar.showMessage('Ready')
        self.clock.display("00:00:00")
        self.aborted = False
        logger.info("Processing Finished")
        self.enableProcessButton()

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
            msgbox = dialogs.confirm_quit()
            if msgbox.exec_() != msgbox.Yes:
                event.ignore()
                return

        # if currently processing, need to shut down threads...
        if self.listbox.inProcess:
            self.listbox.abort_workers()
            self.work_finished.connect(self.quitProgram)
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
