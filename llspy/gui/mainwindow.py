#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function, division

import llspy
import llspy.gui.exceptions as err
from llspy.gui import workers
from llspy.gui.camcalibgui import CamCalibDialog
from llspy.gui.implist import ImpListContainer
from llspy.gui.helpers import (newWorkerThread, shortname, string_to_iterable,
                               guisave, guirestore, reveal)
from llspy.gui.img_dialog import ImgDialog
from llspy.gui.qtlogger import NotificationHandler
from llspy.gui.folderqueue import LLSDragDropTable
from llspy.gui.regtab import RegistrationTab
from llspy import util
from llspy.processplan import ProcessPlan
from fiducialreg.fiducialreg import RegFile, RegistrationError

from PyQt5 import QtCore, QtGui, uic
from PyQt5 import QtWidgets as QtW

import json
import os
import os.path as osp
import numpy as np
import logging

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


class main_GUI(QtW.QMainWindow, Ui_Main_GUI, RegistrationTab):
    """docstring for main_GUI"""

    sig_abort_LLSworkers = QtCore.pyqtSignal()
    sig_item_finished = QtCore.pyqtSignal()
    sig_processing_done = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(main_GUI, self).__init__(parent)
        self.setupUi(self)  # method inherited from form_class to init UI
        self.setWindowTitle("LLSpy :: Lattice Light Sheet Processing")
        RegistrationTab.__init__(self)

        self.LLSItemThreads = []
        self.compressionThreads = []
        self.argQueue = []  # holds all argument lists that will be sent to threads
        self.aborted = False  # current abort status
        self.inProcess = False
        self.spimwins = []

        # delete and reintroduce custom LLSDragDropTable and imp window
        self.listbox.setParent(None)
        self.listbox = LLSDragDropTable(self)
        self.processSplitter.insertWidget(0, self.listbox)
        self.impListWidget.setParent(None)
        self.impContainer = ImpListContainer()
        self.impListWidget = self.impContainer.list
        self.processSplitter.addWidget(self.impContainer)

        handler = NotificationHandler()
        handler.emitSignal.connect(self.log.append)
        logger.addHandler(handler)

        self.camcorDialog = CamCalibDialog()
        self.genFlashParams.clicked.connect(self.camcorDialog.show)
        self.actionCamera_Calibration.triggered.connect(self.camcorDialog.show)

        # connect buttons
        self.previewButton.clicked.connect(self.onPreview)
        self.processButton.clicked.connect(self.onProcess)
        self.errorOptOutCheckBox.stateChanged.connect(self.toggleOptOut)

        def toggleActiveGPU(val):
            gpunum = int(self.sender().objectName().strip('useGPU_'))
            app = QtCore.QCoreApplication.instance()
            if not hasattr(app, 'gpuset'):
                app.gpuset = set()
            if val:
                app.gpuset.add(gpunum)
                logger.debug("GPU {} added to gpuset.".format(gpunum))
            else:
                if gpunum in app.gpuset:
                    app.gpuset.remove(gpunum)
                    logger.debug("GPU {} removed from gpuset.".format(gpunum))
            logger.debug("GPUset now: {}".format(app.gpuset))

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
        self.actionReveal.triggered.connect(self.revealSelected)
        self.actionMerge_MIPs_from_folder.triggered.connect(self.mergeMIPtool)
        self.actionOpen_LLSdir.triggered.connect(self.openLLSdir)
        self.actionRun.triggered.connect(self.onProcess)
        self.actionAbort.triggered.connect(self.abort_workers)
        self.actionClose_All_Previews.triggered.connect(self.close_all_previews)
        self.actionPreview.triggered.connect(self.onPreview)
        self.actionSave_Settings_as_Default.triggered.connect(
            self.saveCurrentAsDefault)
        self.actionLoad_Default_Settings.triggered.connect(
            self.loadDefaultSettings)
        self.actionReduce_to_Raw.triggered.connect(self.reduceSelected)
        self.actionFreeze.triggered.connect(self.freezeSelected)
        self.actionCompress_Folder.triggered.connect(self.compressSelected)
        self.actionDecompress_Folder.triggered.connect(self.decompressSelected)
        self.actionConcatenate.triggered.connect(self.concatenateSelected)
        self.actionRename_Scripted.triggered.connect(self.renameSelected)
        self.actionUndo_Rename_Iters.triggered.connect(self.undoRenameSelected)
        self.actionAbout_LLSpy.triggered.connect(self.showAboutWindow)
        self.actionHelp.triggered.connect(self.showHelpWindow)

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
        self.sig_item_finished.connect(self.on_item_finished)
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
            raise err.RegistrationError("Failed to parse registration file", str(e))
        except RegistrationError as e:
            self.RegProcessPathLineEdit.setText('')
            raise err.RegistrationError('Failed to load registration calibration data', str(e))
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

    def saveCurrentAsDefault(self):
        if len(defaultSettings.childKeys()):
            reply = QtW.QMessageBox.question(
                self, 'Save Settings',
                "Overwrite existing default GUI settings?",
                QtW.QMessageBox.Yes | QtW.QMessageBox.No,
                QtW.QMessageBox.No)
            if reply != QtW.QMessageBox.Yes:
                return
        guisave(self, defaultSettings)

    def loadProgramDefaults(self):
        guirestore(self, QtCore.QSettings(), programDefaults)

    def loadDefaultSettings(self):
        if not len(defaultSettings.childKeys()):
            reply = QtW.QMessageBox.information(
                self, 'Load Settings',
                "Default settings have not yet been saved.  Use Save Settings")
            if reply != QtW.QMessageBox.Yes:
                return
        guirestore(self, defaultSettings, programDefaults)

    def openLLSdir(self):
        path = QtW.QFileDialog.getExistingDirectory(
            self, 'Choose LLSdir to add to list',
            '', QtW.QFileDialog.ShowDirsOnly)
        if path is not None:
            self.listbox.addPath(path)

    def incrementProgress(self):
        # with no values, simply increment progressbar
        self.progressBar.setValue(self.progressBar.value() + 1)

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
            raise err.InvalidSettingsError(
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

            win = ImgDialog(array, info=params, title=shortname(self.previewPath))
            self.spimwins.append(win)

    @QtCore.pyqtSlot()
    def close_all_previews(self):
        if hasattr(self, 'spimwins'):
            for win in self.spimwins:
                try:
                    win.closeMe()
                except Exception:
                    try:
                        win.close()
                    except Exception:
                        pass
        self.spimwins = []

    def onProcess(self):
        # prevent additional button clicks which processing
        self.disableProcessButton()
        self.listbox.skipped_items = set()

        if self.listbox.rowCount() == 0:
            QtW.QMessageBox.warning(
                self, "Nothing Added!",
                'Nothing to process! Drag and drop folders into the list',
                QtW.QMessageBox.Ok, QtW.QMessageBox.NoButton)
            self.enableProcessButton()
            return

        # store current options for this processing run.  TODO: Unecessary?
        try:
            pass
        except Exception:
            self.enableProcessButton()
            raise

        if not self.inProcess:  # for now, only one item allowed processing at a time
            self.inProcess = True
            self.process_next_item()
        else:
            logger.warning('Ignoring request to process, already processing...')

    def process_next_item(self):
        # get path from first row and create a new LLSdir object
        numskipped = len(self.listbox.skipped_items)
        self.currentItem = self.listbox.item(numskipped, 1).text()
        self.currentPath = self.listbox.getPathByIndex(numskipped)
        obj = self.listbox.getLLSObjectByPath(self.currentPath)

        def skip():
            self.listbox.removePath(self.currentPath)
            self.look_for_next_item()
            return

        if not os.path.exists(self.currentPath):
            msg = 'Skipping! path no longer exists: {}'.format(self.currentPath)
            logger.info(msg)
            self.statusBar.showMessage(msg, 5000)
            skip()
            return

        # check if already processed
        # if util.pathHasPattern(self.currentPath, '*' + llspy.config.__OUTPUTLOG__):
        #     if not self.reprocessCheckBox.isChecked():
        #         msg = 'Skipping! Path already processed: {}'.format(self.currentPath)
        #         logger.info(msg)
        #         self.statusBar.showMessage(msg, 5000)
        #         skip()
        #         return

        self.plan = ProcessPlan(obj, self.impListWidget.getImpList())
        try:
            self.plan.plan()  # do sanity check here
        except self.plan.PlanWarning as e:
            msg = QtW.QMessageBox()
            msg.setIcon(QtW.QMessageBox.Information)
            msg.setText(str(e) + '\n\nContinue anyway?')
            msg.setStandardButtons(QtW.QMessageBox.Ok | QtW.QMessageBox.Cancel)
            if msg.exec_() == QtW.QMessageBox.Ok:
                self.plan.plan(skip_warnings=True)
            else:
                return
        except self.plan.PlanError:
            raise

        self.plan.execute()
        # if not len(QtCore.QCoreApplication.instance().gpuset):
        #     self.on_proc_finished()
        #     raise err.InvalidSettingsError("No GPUs selected. Check Config Tab")

        # self.statusBar.showMessage('Starting processing on {} ...'.format(shortname(self.currentPath)))
        # LLSworker, thread = newWorkerThread(
        #     workers.LLSitemWorker,
        #     obj, idx, opts, workerConnect={
        #         'finished': self.on_item_finished,
        #         'status_update': self.statusBar.showMessage,
        #         'progressMaxVal': self.progressBar.setMaximum,
        #         'progressValue': self.progressBar.setValue,
        #         'progressUp': self.incrementProgress,
        #         'clockUpdate': self.clock.display,
        #         'error': self.abort_workers,
        #         'skipped': self.skip_item,
        #         # 'error': self.errorstring  # implement error signal?
        #     })

        # self.LLSItemThreads.append((thread, LLSworker))

        # # connect mainGUI abort LLSworker signal to the new LLSworker
        # self.sig_abort_LLSworkers.connect(LLSworker.abort)

        # prepare and start LLSworker:
        # thread.started.connect(LLSworker.work)
        # thread.start()  # this will emit 'started' and start thread's event loop

        # recolor the first row to indicate processing
        self.listbox.setRowBackgroudColor(numskipped, QtGui.QColor(0, 0, 255, 30))
        self.listbox.clearSelection()
        # start a timer in the main GUI to measure item processing time
        self.timer = QtCore.QTime()
        self.timer.restart()

    def disableProcessButton(self):
        # turn Process button into a Cancel button and udpate menu items
        self.processButton.clicked.disconnect()
        self.processButton.setText('CANCEL')
        self.processButton.clicked.connect(self.abort_workers)
        self.processButton.setEnabled(True)
        self.actionRun.setDisabled(True)
        self.actionAbort.setEnabled(True)

    def enableProcessButton(self):
        # change Process button back to "Process" and udpate menu items
        self.processButton.clicked.disconnect()
        self.processButton.clicked.connect(self.onProcess)
        self.processButton.setText('Process')
        self.actionRun.setEnabled(True)
        self.actionAbort.setDisabled(True)
        self.inProcess = False

    @QtCore.pyqtSlot()
    def on_proc_finished(self):
        # reinit statusbar and clock
        self.statusBar.showMessage('Ready')
        self.clock.display("00:00:00")
        self.inProcess = False
        self.aborted = False
        logger.info("Processing Finished")
        self.enableProcessButton()

    @QtCore.pyqtSlot()
    def on_item_finished(self):
        if len(self.LLSItemThreads):
            thread, worker = self.LLSItemThreads.pop(0)
            thread.quit()
            thread.wait()
        self.clock.display("00:00:00")
        self.progressBar.setValue(0)
        if self.aborted:
            self.sig_processing_done.emit()
        else:
            try:
                itemTime = QtCore.QTime(0, 0).addMSecs(self.timer.elapsed()).toString()
                logger.info(">" * 4 + " Item {} finished in {} ".format(
                    self.currentItem, itemTime) + "<" * 4)
            except AttributeError:
                pass
            self.listbox.removePath(self.currentPath)
            self.currentPath = None
            self.currentItem = None
            self.look_for_next_item()

    @QtCore.pyqtSlot(str)
    def skip_item(self, path):
        if len(self.LLSItemThreads):
            thread, worker = self.LLSItemThreads.pop(0)
            thread.quit()
            thread.wait()
        self.listbox.setRowBackgroudColor(len(self.listbox.skipped_items), '#FFFFFF')
        self.listbox.skipped_items.add(path)
        self.look_for_next_item()

    @QtCore.pyqtSlot()
    def abort_workers(self):
        self.statusBar.showMessage('Aborting ...')
        logger.info('Message sent to abort ...')
        if len(self.LLSItemThreads):
            self.aborted = True
            self.sig_abort_LLSworkers.emit()
            for row in range(self.listbox.rowCount()):
                self.listbox.setRowBackgroudColor(row, '#FFFFFF')
            # self.processButton.setDisabled(True) # will be reenabled when workers done
        else:
            self.sig_processing_done.emit()

    def look_for_next_item(self):
        if self.listbox.rowCount() > len(self.listbox.skipped_items):
            self.process_next_item()
        else:
            if self.listbox.rowCount() <= len(self.listbox.skipped_items):
                self.sig_processing_done.emit()
                for row in range(self.listbox.rowCount()):
                    self.listbox.setRowBackgroudColor(row, '#FFFFFF')

    def reduceSelected(self):
        for item in self.listbox.selectedPaths():
            llspy.LLSdir(item).reduce_to_raw(keepmip=self.saveMIPsDuringReduceCheckBox.isChecked())

    def freezeSelected(self):
        for item in self.listbox.selectedPaths():
            llspy.LLSdir(item).reduce_to_raw(keepmip=self.saveMIPsDuringReduceCheckBox.isChecked())
            self.compressItem(item)

    def compressSelected(self):
        [self.compressItem(item) for item in self.listbox.selectedPaths()]

    def compressItem(self, item):
        def has_tiff(path):
            for f in os.listdir(path):
                if f.endswith('.tif'):
                    return True
            return False

        # figure out what type of folder this is
        if not has_tiff(item):
            self.statusBar.showMessage(
                'No tiffs to compress in ' + shortname(item), 4000)
            return

        worker, thread = newWorkerThread(
            workers.CompressionWorker, item, 'compress',
            self.compressTypeCombo.currentText(),
            workerConnect={
                'status_update': self.statusBar.showMessage,
                'finished': lambda: self.statusBar.showMessage('Compression finished', 4000)
            },
            start=True)
        self.compressionThreads.append((worker, thread))

    def decompressSelected(self):
        for item in self.listbox.selectedPaths():
            if not util.find_filepattern(item, '*.tar*'):
                self.statusBar.showMessage(
                    'No .tar file found in ' + shortname(item), 4000)
                continue

            def onfinish():
                self.listbox.llsObjects[item]._register_tiffs()
                self.statusBar.showMessage('Decompression finished', 4000)

            worker, thread = newWorkerThread(
                workers.CompressionWorker, item, 'decompress',
                self.compressTypeCombo.currentText(),
                workerConnect={
                    'status_update': self.statusBar.showMessage,
                    'finished': onfinish
                },
                start=True)
            self.compressionThreads.append((worker, thread))

    def revealSelected(self):
        selectedPaths = self.listbox.selectedPaths()
        if len(selectedPaths):
            for p in selectedPaths:
                if os.path.exists(p):
                    reveal(p)

    def concatenateSelected(self):
        selectedPaths = self.listbox.selectedPaths()
        if len(selectedPaths) > 1:
            llspy.llsdir.concatenate_folders(selectedPaths)
            [self.listbox.removePath(p) for p in selectedPaths]
            [self.listbox.addPath(p) for p in selectedPaths]

    def undoRenameSelected(self):

        box = QtW.QMessageBox()
        box.setWindowTitle('Undo Renaming')
        box.setText("Do you want to undo all renaming that has occured in this session?, or chose a directory?")
        box.setIcon(QtW.QMessageBox.Question)
        box.addButton(QtW.QMessageBox.Cancel)
        box.addButton("Undo Everything", QtW.QMessageBox.YesRole)
        box.addButton("Choose Specific Directory", QtW.QMessageBox.ActionRole)
        box.setDefaultButton(QtW.QMessageBox.Cancel)
        reply = box.exec_()

        if reply > 1000:  # cancel hit
            return
        elif reply == 1:  # action role  hit
            path = QtW.QFileDialog.getExistingDirectory(
                self, 'Choose Directory to Undo',
                os.path.expanduser('~'), QtW.QFileDialog.ShowDirsOnly)
            if path:
                paths = [path]
            else:
                paths = []
        elif reply == 0:  # yes role  hit
            if not hasattr(self.listbox, 'renamedPaths') or not self.listbox.renamedPaths:
                return
            paths = self.listbox.renamedPaths

        for P in paths:
            for root, subd, file in os.walk(P):
                self.listbox.removePath(root)
                for d in subd:
                    self.listbox.removePath(os.path.join(root, d))
            llspy.llsdir.undo_rename_iters(P)
        self.listbox.renamedPaths = []

    def renameSelected(self):
        if not hasattr(self.listbox, 'renamedPaths'):
            self.listbox.renamedPaths = []
        for item in self.listbox.selectedPaths():
            llspy.llsdir.rename_iters(item)
            self.listbox.renamedPaths.append(item)
            self.listbox.removePath(item)
            [self.listbox.addPath(osp.join(item, p)) for p in os.listdir(item)]

    def mergeMIPtool(self):

        if len(self.listbox.selectedPaths()):
            for obj in self.listbox.selectedObjects():
                obj.mergemips()
        else:
            path = QtW.QFileDialog.getExistingDirectory(
                self, 'Choose Directory with MIPs to merge',
                os.path.expanduser('~'), QtW.QFileDialog.ShowDirsOnly)
            if path:
                for axis in ['z', 'y', 'x']:
                    llspy.llsdir.mergemips(path, axis, dx=0.102, delete=True)

    def toggleOptOut(self, value):
        err._OPTOUT = True if value else False

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

    def showAboutWindow(self):
        import datetime
        now = datetime.datetime.now()
        QtW.QMessageBox.about(self, 'LLSpy',
            """LLSpy v.{}\n
Copyright ©  {}, President and Fellows of Harvard College.  All rights reserved.\n\n
Developed by Talley Lambert\n\n
The cudaDeconv deconvolution program is owned and licensed by HHMI, Janelia Research Campus.  Please contact innovation@janlia.hhmi.org for access.""".format(llspy.__version__, now.year))

    def showHelpWindow(self):
        QtW.QMessageBox.about(self, 'LLSpy', 'Please see documentation at llspy.readthedocs.io')

    def closeEvent(self, event):
        ''' triggered when close button is clicked on main window '''
        if self.listbox.rowCount() and self.confirmOnQuitCheckBox.isChecked():
            box = QtW.QMessageBox()
            box.setWindowTitle('Unprocessed items!')
            box.setText("You have unprocessed items.  Are you sure you want to quit?")
            box.setIcon(QtW.QMessageBox.Warning)
            box.addButton(QtW.QMessageBox.Yes)
            box.addButton(QtW.QMessageBox.No)
            box.setDefaultButton(QtW.QMessageBox.Yes)
            pref = QtW.QCheckBox("Always quit without confirmation")
            box.setCheckBox(pref)

            pref.stateChanged.connect(
                lambda value:
                self.confirmOnQuitCheckBox.setChecked(False) if value else
                self.confirmOnQuitCheckBox.setChecked(True))

            reply = box.exec_()
            # reply = box.question(self, 'Unprocessed items!',
            #     "You have unprocessed items.  Are you sure you want to quit?",
            #     QtW.QMessageBox.Yes | QtW.QMessageBox.No,
            #     QtW.QMessageBox.Yes)
            if reply != QtW.QMessageBox.Yes:
                event.ignore()
                return

        # if currently processing, need to shut down threads...
        if self.inProcess:
            self.abort_workers()
            self.sig_processing_done.connect(self.quitProgram)
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
    exceptionHandler = err.ExceptionHandler()
    sys.excepthook = exceptionHandler.handler
    exceptionHandler.errorMessage.connect(main.show_error_window)

    main.show()
    sys.exit(APP.exec_())
