#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function, division

import llspy
import llspy.gui.exceptions as err
from llspy.gui.main_gui import Ui_Main_GUI
from llspy.gui import workers
from llspy.gui.camcalibgui import CamCalibDialog
from llspy.gui.helpers import (newWorkerThread,
    wait_for_file_close, wait_for_folder_finished,
    shortname, string_to_iterable, guisave, guirestore)
from llspy.gui.img_dialog import ImgDialog
from llspy.gui.qtlogger import NotificationHandler
from fiducialreg.fiducialreg import RegFile, RegistrationError


from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, RegexMatchingEventHandler
from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets as QtW

import json
import os
import os.path as osp
import fnmatch
import numpy as np
import time
import logging

logger = logging.getLogger()  # set root logger
logger.setLevel(logging.DEBUG)
lhStdout = logger.handlers[0]   # grab console handler so we can delete later
ch = logging.StreamHandler()    # create new console handler
ch.setLevel(logging.ERROR)      # with desired logging level
# ch.addFilter(logging.Filter('llspy'))  # and any filters
logger.addHandler(ch)           # add it to the root logger
logger.removeHandler(lhStdout)  # and delete the original streamhandler

_SPIMAGINE_IMPORTED = False

# import sys
# sys.path.append(osp.join(osp.abspath(__file__), os.pardir, os.pardir))

# Ui_Main_GUI = uic.loadUiType(osp.join(thisDirectory, 'main_gui.ui'))[0]
# form_class = uic.loadUiType('./llspy/gui/main_gui.ui')[0]  # for debugging

# platform independent settings file
QtCore.QCoreApplication.setOrganizationName("llspy")
QtCore.QCoreApplication.setOrganizationDomain("llspy.com")
sessionSettings = QtCore.QSettings("llspy", "llspyGUI")
defaultSettings = QtCore.QSettings("llspy", 'llspyDefaults')
# programDefaults are provided in guiDefaults.ini as a reasonable starting place
# this line finds the relative path depending on whether we're running in a
# pyinstaller bundle or live.
defaultINI = llspy.util.getAbsoluteResourcePath('gui/guiDefaults.ini')
programDefaults = QtCore.QSettings(defaultINI, QtCore.QSettings.IniFormat)

if not sessionSettings.value('disableSpimagineCheckBox', False, type=bool):
    try:
        #raise ImportError("skipping")
        from spimagine import DataModel, NumpyData
        from spimagine.gui.mainwidget import MainWidget as spimagineWidget
        _SPIMAGINE_IMPORTED = True
    except ImportError:
        logger.error("could not import spimagine!  falling back to matplotlib")


class LLSDragDropTable(QtW.QTableWidget):
    colHeaders = ['path', 'name', 'nC', 'nT', 'nZ', 'nY', 'nX', 'angle', 'dz', 'dx']
    nCOLS = len(colHeaders)

    # A signal needs to be defined on class level:
    dropSignal = QtCore.pyqtSignal(list, name="dropped")

    # This signal emits when a URL is dropped onto this list,
    # and triggers handler defined in parent widget.

    def __init__(self, parent=None):
        super(LLSDragDropTable, self).__init__(0, self.nCOLS, parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QtW.QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QtW.QAbstractItemView.SelectRows)
        self.setEditTriggers(QtW.QAbstractItemView.DoubleClicked)
        self.setGridStyle(3)  # dotted grid line
        self.llsObjects = {}  # dict to hold LLSdir Objects when instantiated

        self.setHorizontalHeaderLabels(self.colHeaders)
        self.hideColumn(0)  # column 0 is a hidden col for the full pathname
        header = self.horizontalHeader()
        header.setSectionResizeMode(1, QtW.QHeaderView.Stretch)
        header.resizeSection(2, 27)
        header.resizeSection(3, 45)
        header.resizeSection(4, 40)
        header.resizeSection(5, 40)
        header.resizeSection(6, 40)
        header.resizeSection(7, 40)
        header.resizeSection(8, 48)
        header.resizeSection(9, 48)
        self.cellChanged.connect(self.onCellChanged)

    @QtCore.pyqtSlot(int, int)
    def onCellChanged(self, row, col):
        # if it's not one of the last few columns that changed, ignore
        if col < 7:
            return
        # must be the ACTIVE column that changed...
        if col == self.currentColumn():
            self.cellChanged.disconnect(self.onCellChanged)
            try:
                val = float(self.currentItem().text())
            except ValueError:
                self.currentItem().setText('0.0')
                raise err.InvalidSettingsError('Value entered was not a number')
            try:
                if col == 7:
                    if not (-90 < val < 90):
                        self.currentItem().setText('0.0')
                        raise err.InvalidSettingsError('angle must be between -90 and 90')
                    self.getLLSObjectByIndex(row).parameters['angle'] = val
                if col == 8:
                    if not (0 < val < 20):
                        self.currentItem().setText('0.0')
                        raise err.InvalidSettingsError('dz must be between 0 and 20 (microns)')
                    self.getLLSObjectByIndex(row).parameters['dz'] = val
                if col == 9:
                    if not (0 < val < 5):
                        self.currentItem().setText('0.0')
                        raise err.InvalidSettingsError('dx must be between 0 and 5 (microns)')
                    self.getLLSObjectByIndex(row).parameters['dx'] = val
                # change color once updated
            finally:
                if ((col == 7 and not (-90 < val < 90)) or
                        (col == 8 and not (0 < val < 20)) or
                        (col == 9 and not (0 < val < 5))):
                    self.currentItem().setForeground(QtCore.Qt.white)
                    self.currentItem().setBackground(QtCore.Qt.red)
                else:
                    self.currentItem().setForeground(QtCore.Qt.black)
                    self.currentItem().setBackground(QtCore.Qt.white)
                self.cellChanged.connect(self.onCellChanged)

    @QtCore.pyqtSlot(str)
    def addPath(self, path):
        try:
            self.cellChanged.disconnect(self.onCellChanged)
        except TypeError:
            pass
        if not (osp.exists(path) and osp.isdir(path)):
            return

        mainGUI = self.parent().parent().parent().parent().parent()
        # If this folder is not on the list yet, add it to the list:
        if not llspy.util.pathHasPattern(path, '*Settings.txt'):
            if not mainGUI.allowNoSettingsCheckBox.isChecked():
                logger.warning('No Settings.txt! Ignoring: {}'.format(path))
                return

        # if it's already on the list, don't add it
        if len(self.findItems(path, QtCore.Qt.MatchExactly)):
            return

        # if it's a folder containing files with "_Iter_"  warn the user...
        if llspy.util.pathHasPattern(path, '*Iter_*'):
            if sessionSettings.value('warnIterFolder', True, type=bool):
                box = QtW.QMessageBox()
                box.setWindowTitle('Note')
                box.setText('You have added a folder that appears to have been acquired'
                    ' in Script Editor: it has "Iter_" in the filenames.\n\n'
                    'LLSpy generally assumes that each folder contains '
                    'a single position timelapse dataset (see docs for assumptions '
                    'about data format).  Hit PROCESS ANYWAY to process this folder as is, '
                    'but it may yield unexpected results. You may also RENAME ITERS, '
                    'this will RENAME all files as if they were single experiments '
                    'acquired at different positions and place them into their own '
                    'folders (cannot be undone). Hit CANCEL to prevent adding this '
                    'item to the queue.')
                box.setIcon(QtW.QMessageBox.Warning)
                box.addButton(QtW.QMessageBox.Cancel)
                box.addButton("Process Anyway", QtW.QMessageBox.YesRole)
                box.addButton("Rename Iters", QtW.QMessageBox.ActionRole)
                box.setDefaultButton(QtW.QMessageBox.Cancel)
                # pref = QtW.QCheckBox("Remember my answer")
                # box.setCheckBox(pref)

                reply = box.exec_()

                if reply > 1000:  # cancel hit
                    return
                elif reply == 1:  # rename iters hit
                    if not hasattr(self, 'renamedPaths'):
                        self.renamedPaths = []
                    llspy.llsdir.rename_iters(path)
                    self.renamedPaths.append(path)
                    # self.removePath(path)
                    [self.addPath(osp.join(path, p)) for p in os.listdir(path)]
                    return
                elif reply == 0:  # process anyway hit
                    pass

        E = llspy.LLSdir(path)
        if not E.has_lls_tiffs:
            if llspy.util.pathHasPattern(path, '*.tif'):
                if sessionSettings.value('warnOnNoLLStiffs', True, type=bool):
                    box = QtW.QMessageBox()
                    box.setWindowTitle('Path has tiff files, but none of them match'
                    ' the file naming convention assumed by LLSpy.')
                    box.setText('Path has tiff files, but none of them match'
                    ' the file naming convention assumed by LLSpy.  Please read '
                    'Data Structure Assumptions in the documentation for more info.\n\n'
                    'http://llspy.readthedocs.io/en/latest/main.html#data-structure-assumptions\n')
                    box.setIcon(QtW.QMessageBox.Warning)
                    box.addButton(QtW.QMessageBox.Ok)
                    box.setDefaultButton(QtW.QMessageBox.Ok)
                    pref = QtW.QCheckBox("Just skip these folders in the future")
                    box.setCheckBox(pref)

                    def setPref(value):
                        sessionSettings.setValue('warnOnNoLLStiffs', bool(value))
                        sessionSettings.sync()

                    pref.stateChanged.connect(setPref)
                    box.exec_()
            else:
                logger.info('No tiff files detected! Ignoring: {}'.format(path))
            return
        logger.info('Adding to queue: %s' % shortname(path))

        rowPosition = self.rowCount()
        self.insertRow(rowPosition)
        item = [path,
                shortname(str(E.path)),
                str(E.parameters.nc),
                str(E.parameters.nt),
                str(E.parameters.nz),
                str(E.parameters.ny),
                str(E.parameters.nx)]
        if E.has_settings:
            item.extend([
                "{:2.1f}".format(E.parameters.angle) if E.parameters.samplescan else "0",
                "{:0.3f}".format(E.parameters.dz),
                "{:0.3f}".format(E.parameters.dx)])
        else:
            dx = E.parameters.dx or mainGUI.defaultDxSpin.value()
            dz = E.parameters.dz or mainGUI.defaultDzSpin.value()
            angle = E.parameters.angle or mainGUI.defaultAngleSpin.value()
            item.extend([
                "{:2.1f}".format(angle),
                "{:0.3f}".format(dz),
                "{:0.3f}".format(dx)])
            E.parameters.angle = angle
            E.parameters.samplescan = True if angle > 0 else False
            E.parameters.dx = dx
            E.parameters.dz = dz
        for col, elem in enumerate(item):
            entry = QtW.QTableWidgetItem(elem)
            if col < 7:
                entry.setFlags(QtCore.Qt.ItemIsSelectable |
                               QtCore.Qt.ItemIsEnabled)
            else:
                entry.setFlags(QtCore.Qt.ItemIsSelectable |
                               QtCore.Qt.ItemIsEnabled |
                               QtCore.Qt.ItemIsEditable)
                if not E.has_settings:
                    faintRed = QtGui.QBrush(QtGui.QColor(255, 0, 0, 30))
                    lightGray = QtGui.QBrush(QtGui.QColor(160, 160, 160))
                    entry.setForeground(lightGray)
                    entry.setBackground(faintRed)
            self.setItem(rowPosition, col, entry)
            if col > 7 and float(elem) == 0:
                entry.setForeground(QtCore.Qt.white)
                entry.setBackground(QtCore.Qt.red)
        self.llsObjects[path] = E
        self.cellChanged.connect(self.onCellChanged)

    def selectedPaths(self):
        selectedRows = self.selectionModel().selectedRows()
        return [self.getPathByIndex(i.row()) for i in selectedRows]

    @QtCore.pyqtSlot(str)
    def removePath(self, path):
        self.llsObjects.pop(path)
        items = self.findItems(path, QtCore.Qt.MatchExactly)
        for item in items:
            self.removeRow(item.row())
        if hasattr(self, 'skipped_items'):
            if path in self.skipped_items:
                self.skipped_items.remove(path)

    def getPathByIndex(self, index):
        return self.item(index, 0).text()

    def getLLSObjectByPath(self, path):
        return self.llsObjects[path]

    def getLLSObjectByIndex(self, index):
        return self.llsObjects[self.getPathByIndex(index)]

    def setRowBackgroudColor(self, row, color):
        try:
            self.cellChanged.disconnect(self.onCellChanged)
        except TypeError:
            pass
        if isinstance(color, QtGui.QColor):
            brush = QtGui.QBrush(color)
        else:
            brush = QtGui.QBrush(QtGui.QColor(color))
        for col in range(self.nCOLS):
            self.item(row, col).setBackground(brush)
            if col > 7 and float(self.item(row, col).text()) == 0:
                self.item(row, col).setForeground(QtCore.Qt.white)
                self.item(row, col).setBackground(QtCore.Qt.red)
        self.cellChanged.connect(self.onCellChanged)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            # links = []
            for url in event.mimeData().urls():
                # links.append(str(url.toLocalFile()))
                self.addPath(str(url.toLocalFile()))
            # self.dropSignal.emit(links)
            # for url in links:
            #   self.listbox.addPath(url)
        else:
            event.ignore()

    def keyPressEvent(self, event):
        super(LLSDragDropTable, self).keyPressEvent(event)
        if (event.key() == QtCore.Qt.Key_Delete or event.key() == QtCore.Qt.Key_Backspace):
            indices = self.selectionModel().selectedRows()
            i = 0
            for index in sorted(indices):
                removerow = index.row() - i
                path = self.getPathByIndex(removerow)
                logger.info('Removing from queue: %s' % shortname(path))
                self.removePath(path)
                i += 1


class ActiveHandler(RegexMatchingEventHandler, QtCore.QObject):
    tReady = QtCore.pyqtSignal(int)
    allReceived = QtCore.pyqtSignal()  # don't expect to receive anymore
    newfile = QtCore.pyqtSignal(str)

    def __init__(self, path, nC, nT, **kwargs):
        super(ActiveHandler, self).__init__(**kwargs)
        self.path = path
        self.nC = nC
        self.nT = nT
        # this assumes the experiment hasn't been stopped mid-stream
        self.counter = np.zeros(self.nT)

    def check_for_existing_files(self):
        # this is here in case files already exist in the directory...
        # we don't want the handler to miss them
        # this is called by the parent after connecting the tReady signal
        for f in os.listdir(self.path):
            if fnmatch.fnmatch(f, '*tif'):
                self.register_file(osp.join(self.path, f))

    def on_created(self, event):
        # Called when a file or directory is created.
        self.register_file(event.src_path)

    def register_file(self, path):
        self.newfile.emit(path)
        p = llspy.parse.parse_filename(osp.basename(path))
        self.counter[p['stack']] += 1
        ready = np.where(self.counter == self.nC)[0]
        # break counter for those timepoints
        self.counter[ready] = np.nan
        # can use <100 as a sign of timepoints still not finished
        if len(ready):
            # try to see if file has finished writing... does this work?
            wait_for_file_close(path)
            [self.tReady.emit(t) for t in ready]

        # once all nC * nT has been seen emit allReceived
        if all(np.isnan(self.counter)):
            logger.debug("All Timepoints Received")
            self.allReceived.emit()


class ActiveWatcher(QtCore.QObject):
    """docstring for ActiveWatcher"""

    finished = QtCore.pyqtSignal()
    stalled = QtCore.pyqtSignal()
    status_update = QtCore.pyqtSignal(str, int)

    def __init__(self, path, timeout=30):
        super(ActiveWatcher, self).__init__()
        self.path = path
        self.timeout = timeout  # seconds to wait for new file before giving up
        self.inProcess = False
        settext = llspy.util.find_filepattern(path, '*Settings.txt')
        wait_for_file_close(settext)
        time.sleep(1)  # give the settings file a minute to write
        self.E = llspy.LLSdir(path, False)
        # TODO:  probably need to check for files that are already there
        self.tQueue = []
        self.allReceived = False
        self.worker = None

        try:
            app = QtCore.QCoreApplication.instance()
            gui = next(w for w in app.topLevelWidgets() if isinstance(w, main_GUI))
            self.opts = gui.getValidatedOptions()
        except Exception:
            raise

        # timeout clock to make sure this directory doesn't stagnate
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.stall)
        self.timer.start(self.timeout * 1000)

        # Too strict?
        fpattern = '^.+_ch\d_stack\d{4}_\D*\d+.*_\d{7}msec_\d{10}msecAbs.*.tif'
        # fpattern = '.*.tif'
        handler = ActiveHandler(str(self.E.path),
            self.E.parameters.nc, self.E.parameters.nt,
            regexes=[fpattern], ignore_directories=True)
        handler.tReady.connect(self.add_ready)
        handler.allReceived.connect(self.all_received)
        handler.newfile.connect(self.newfile)
        handler.check_for_existing_files()

        self.observer = Observer()
        self.observer.schedule(handler, self.path, recursive=False)
        self.observer.start()

        logger.info("New LLS directory now being watched: " + self.path)

    @QtCore.pyqtSlot(str)
    def newfile(self, path):
        self.restart_clock()
        self.status_update.emit(shortname(path), 2000)

    def all_received(self):
        self.allReceived = True
        if not self.inProcess and len(self.tQueue):
            self.terminate()

    def restart_clock(self):
        # restart the kill timer, since the handler is still alive
        self.timer.start(self.timeout * 1000)

    def add_ready(self, t):
        # add the new timepoint to the Queue
        self.tQueue.append(t)
        # start processing
        self.process()

    def process(self):
        if not self.inProcess and len(self.tQueue):
            self.inProcess = True
            timepoints = []
            while len(self.tQueue):
                timepoints.append(self.tQueue.pop())
            timepoints = sorted(timepoints)
            cRange = None  # TODO: plug this in
            self.tQueue = []

            # note: it was important NOT to ditch partial tiffs with the activate
            # watcher since the files aren't finished yet...
            w, thread = newWorkerThread(workers.TimePointWorker, self.path,
                timepoints, cRange, self.opts, False,
                workerConnect={
                    'previewReady': self.writeFile
                },
                start=True)
            self.worker = (timepoints, w, thread)
        elif not any((self.inProcess, len(self.tQueue), not self.allReceived)):
            self.terminate()

    @QtCore.pyqtSlot(np.ndarray, float, float)
    def writeFile(self, stack, dx, dz):
        timepoints, worker, thread = self.worker

        def write_stack(s, c=0, t=0):
            if self.opts['nIters'] > 0:
                outfolder = 'GPUdecon'
                proctype = '_decon'
            else:
                outfolder = 'Deskewed'
                proctype = '_deskewed'
            if not self.E.path.joinpath(outfolder).exists():
                self.E.path.joinpath(outfolder).mkdir()

            corstring = '_COR' if self.opts['correctFlash'] else ''
            basename = os.path.basename(self.E.get_files(c=c, t=t)[0])
            filename = basename.replace('.tif', corstring + proctype + '.tif')
            outpath = str(self.E.path.joinpath(outfolder, filename))
            llspy.util.imsave(llspy.util.reorderstack(np.squeeze(s), 'zyx'),
                outpath, dx=self.E.parameters.dx, dz=self.E.parameters.dzFinal)

        if stack.ndim == 5:
            if not stack.shape[0] == len(timepoints):
                raise ValueError('Processed stacks length not equal to requested'
                    ' number of timepoints processed')
            for t in range(stack.shape[0]):
                for c in range(stack.shape[1]):
                    s = stack[t][c]
                    write_stack(s, c, timepoints[t])
        elif stack.ndim == 4:
            for c in range(stack.shape[0]):
                write_stack(stack[c], c, timepoints[0])
        else:
            write_stack(stack, t=timepoints[0])

        thread.quit()
        thread.wait()
        self.inProcess = False
        self.process()  # check to see if there's more waiting in the queue

    def stall(self):
        self.stalled.emit()
        logger.debug('WATCHER TIMEOUT REACHED!')
        self.terminate()

    @QtCore.pyqtSlot()
    def terminate(self):
        logger.debug('TERMINATING WATCHER')
        self.observer.stop()
        self.observer.join()
        self.finished.emit()


class MainHandler(FileSystemEventHandler, QtCore.QObject):
    foundLLSdir = QtCore.pyqtSignal(str)
    lostListItem = QtCore.pyqtSignal(str)

    def __init__(self):
        super(MainHandler, self).__init__()

    def on_created(self, event):
        # Called when a file or directory is created.
        if event.is_directory:
            pass
        else:
            if 'Settings.txt' in event.src_path:
                wait_for_folder_finished(osp.dirname(event.src_path))
                self.foundLLSdir.emit(osp.dirname(event.src_path))

    def on_deleted(self, event):
        # Called when a file or directory is created.
        if event.is_directory:
            app = QtCore.QCoreApplication.instance()
            gui = next(w for w in app.topLevelWidgets() if isinstance(w, main_GUI))

            # TODO:  Is it safe to directly access main gui listbox here?
            if len(gui.listbox.findItems(event.src_path, QtCore.Qt.MatchExactly)):
                self.lostListItem.emit(event.src_path)


class RegistrationTab(object):

    def __init__(self):
        self.RegCalibPathLoadButton.clicked.connect(self.setRegCalibPath)
        self.GenerateRegFileButton.clicked.connect(self.generateCalibrationFile)
        self.RegCalibPreviewButton.clicked.connect(self.previewRegistration)
        self.RegFilePathLoadButton.clicked.connect(self.loadRegistrationFile)
        self.RegCalib_channelRefCombo.clear()
        self.RegCalib_channelRefModeCombo.clear()

    def setRegCalibPath(self):
        path = QtW.QFileDialog.getExistingDirectory(
            self, 'Set Registration Calibration Directory',
            '', QtW.QFileDialog.ShowDirsOnly)
        if path is None or path is '':
            return
        RD = llspy.RegDir(path)
        if not RD.isValid:
            raise err.RegistrationError(
                'Registration Calibration dir not valid: {}'.format(RD.path))

        self.RegCalibPathLineEdit.setText(path)
        layout = self.RegCalibRefGroupLayout
        group = self.RegCalibRefChannelsGroup
        for cb in group.findChildren(QtW.QCheckBox):
            layout.removeWidget(cb)
            cb.setParent(None)
        for wave in RD.parameters.channels.values():
            box = QtW.QCheckBox(str(wave), group)
            layout.addWidget(box)
            box.setChecked(True)

    def generateCalibrationFile(self):
        group = self.RegCalibRefChannelsGroup
        refs = [int(cb.text()) for cb in group.findChildren(QtW.QCheckBox) if cb.isChecked()]
        path = self.RegCalibPathLineEdit.text()
        if not path or path == '':
            raise err.InvalidSettingsError('Please load a fiducial dataset path first')
        if not len(refs):
            raise err.InvalidSettingsError('Select at least one reference channel')

        autoThresh = self.RegAutoThreshCheckbox.isChecked()
        if autoThresh:
            minbeads = int(self.RegMinBeadsSpin.value())
            RD = llspy.RegDir(path, usejson=False, threshold='auto', mincount=minbeads)
        else:
            threshold = int(self.RegBeadThreshSpin.value())
            RD = llspy.RegDir(path, threshold=threshold, usejson=False)

        if not RD.isValid:
            raise err.RegistrationError(
                'Registration Calibration dir not valid: {}'.format(RD.path))

        outdir = QtW.QFileDialog.getExistingDirectory(
                    self, 'Chose destination for registration file', '',
                    QtW.QFileDialog.ShowDirsOnly)
        if outdir is None or outdir is '':
            return

        class RegThread(QtCore.QThread):
            finished = QtCore.pyqtSignal(str)
            warning = QtCore.pyqtSignal(str, str)

            def __init__(self, RD, outdir, refs):
                QtCore.QThread.__init__(self)
                self.RD = RD
                self.outdir = outdir
                self.refs = refs

            def run(self):
                try:
                    outfile, outstring = self.RD.write_reg_file(outdir, refs=self.refs)
                    counts = self.RD.cloudset().count
                    if np.std(counts) > 15:
                        outstr = "\n".join(["wave: {}, beads: {}".format(
                            channel, counts[i]) for i, channel in enumerate(self.RD.waves)])
                        self.warning.emit('Suspicious Registration Result',
                            "Warning: there was a large variation in the number "
                            "of beads per channel.  Auto-detection may have failed.  "
                            "Try changing 'Min number of beads'...\n\n" + outstr)
                except RegistrationError as e:
                    raise err.RegistrationError("Fiducial registration failed:", str(e))

                # also write to appdir ... may use it later
                # TODO: consider making app_dir a global APP attribute,
                # like gpulist
                from click import get_app_dir
                appdir = get_app_dir('LLSpy')
                if not os.path.isdir(appdir):
                    os.mkdir(appdir)
                regdir = os.path.join(appdir, 'regfiles')
                if not os.path.isdir(regdir):
                    os.mkdir(regdir)
                outfile2 = os.path.join(regdir, os.path.basename(outfile))
                with open(outfile2, 'w') as file:
                    file.write(outstring)

                logger.debug("registration file output: {}".format(outfile))
                logger.debug("registration file output: {}".format(outfile2))
                self.finished.emit(outfile)

        def finishup(outfile):
            self.statusBar.showMessage(
                    'Registration file written: {}'.format(outfile), 5000)
            self.loadRegistrationFile(outfile)

        def notifyuser(title, msg):
            QtW.QMessageBox.warning(self, title, msg, QtW.QMessageBox.Ok)

        self.regthreads = []
        regthread = RegThread(RD, outdir, refs)
        regthread.finished.connect(finishup)
        regthread.warning.connect(notifyuser)
        self.regthreads.append(regthread)
        self.statusBar.showMessage(
            'Calculating registrations for ref channels: {}...'.format(refs))
        regthread.start()

    # TODO: this is mostly duplicate functionality of loadRegObject below
    def loadRegistrationFile(self, file=None):
        if not file:
            file = QtW.QFileDialog.getOpenFileName(self,
                    'Choose registration file ',  os.path.expanduser('~'),
                    "Text Files (*.reg *.txt *.json)")[0]

            if file is None or file is '':
                return
        try:
            with open(file) as json_data:
                regdict = json.load(json_data)
            refs = sorted(list(set([t['reference'] for t in regdict['tforms']])))
            # mov = set([t['moving'] for t in regdict['tforms']])
            modes = ['None']
            modes.extend(sorted(list(set(
                [t['mode'].title().replace('Cpd', 'CPD') for t in regdict['tforms']]
            ))))
            self.RegCalib_channelRefCombo.clear()
            self.RegCalib_channelRefCombo.addItems([str(r) for r in refs])
            self.RegCalib_channelRefModeCombo.clear()
            self.RegCalib_channelRefModeCombo.addItems(modes)
            self.RegFilePath.setText(file)
        except json.decoder.JSONDecodeError as e:
            raise err.RegistrationError("Failed to parse registration file", str(e))
        except Exception as e:
            raise err.RegistrationError("Failed to load registration file", str(e))

    def previewRegistration(self):
        RD = llspy.RegDir(self.RegCalibPathLineEdit.text())
        if not RD.isValid:
            raise err.RegistrationError(
                'Registration Calibration dir not valid: {}'.format(RD.path))

        @QtCore.pyqtSlot(np.ndarray, float, float, dict)
        def displayRegPreview(array, dx=None, dz=None, params=None):
            win = ImgDialog(array,
                info=params,
                title="Registration Mode: {} -- RefWave: {}".format(opts['regMode'], opts['regRefWave']))
            win.overlayButton.click()
            win.maxProjButton.click()
            self.spimwins.append(win)

        self.previewButton.setDisabled(True)
        self.previewButton.setText('Working...')

        try:
            opts = self.getValidatedOptions()
        except Exception:
            self.previewButton.setEnabled(True)
            self.previewButton.setText('Preview')
            raise

        opts['regMode'] = self.RegCalib_channelRefModeCombo.currentText()
        if opts['regMode'].lower() == 'none':
            opts['doReg'] = False
        else:
            opts['doReg'] = True
        opts['regRefWave'] = int(self.RegCalib_channelRefCombo.currentText())
        opts['regCalibPath'] = self.RegCalibPathLineEdit.text()
        w, thread = newWorkerThread(workers.TimePointWorker,
            RD.path, [0], None, opts,
            workerConnect={'previewReady': displayRegPreview},
            start=True)

        w.finished.connect(lambda: self.previewButton.setEnabled(True))
        w.finished.connect(lambda: self.previewButton.setText('Preview'))
        self.previewthreads = (w, thread)


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
        self.observer = None  # for watching the watchdir
        self.activeWatchers = {}
        self.spimwins = []

        # delete and reintroduce custom LLSDragDropTable
        self.listbox.setParent(None)
        self.listbox = LLSDragDropTable(self)
        self.process_tab_layout.insertWidget(0, self.listbox)

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
        self.useBundledBinariesCheckBox.stateChanged.connect(self.checkBundled)

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
        try:
            app = QtCore.QCoreApplication.instance()
            if not hasattr(app, 'gpuset'):
                app.gpuset = set()
            gpulist = llspy.cudabinwrapper.gpulist()
            if len(gpulist):
                for i, gpu in enumerate(gpulist):
                    box = QtW.QCheckBox(self.tab_config)
                    box.setChecked(True)
                    box.setObjectName('useGPU_{}'.format(i))
                    box.setText(gpu.strip('GeForce'))
                    box.stateChanged.connect(toggleActiveGPU)
                    app.gpuset.add(i)
                    self.gpuGroupBoxLayout.addWidget(box)
            else:
                label = QtW.QLabel(self.tab_config)
                label.setText('No CUDA-capabled GPUs detected')
                self.gpuGroupBoxLayout.addWidget(label)

        except llspy.cudabinwrapper.CUDAbinException:
            pass

        self.watchDirToolButton.clicked.connect(self.changeWatchDir)
        self.watchDirCheckBox.stateChanged.connect(
            lambda st: self.startWatcher() if st else self.stopWatcher())

        # connect actions
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
        ctrangeRX = QtCore.QRegExp("(\d[\d-]*,?)*")  # could be better
        ctrangeValidator = QtGui.QRegExpValidator(ctrangeRX)
        self.processCRangeLineEdit.setValidator(ctrangeValidator)
        self.processTRangeLineEdit.setValidator(ctrangeValidator)
        self.previewCRangeLineEdit.setValidator(ctrangeValidator)
        self.previewTRangeLineEdit.setValidator(ctrangeValidator)

        # FIXME: this way of doing it clears the text field if you hit cancel
        self.RegProcessPathPushButton.clicked.connect(self.setFiducialData)
        self.RegProcessLoadRegFile.clicked.connect(self.loadProcessRegFile)
        self.cudaDeconvPathToolButton.clicked.connect(self.setCudaDeconvPath)
        self.otfFolderToolButton.clicked.connect(self.setOTFdirPath)
        self.camParamTiffToolButton.clicked.connect(self.setCamParamPath)

        self.RegProcessPathLineEdit.setText('')
        self.RegProcessPathLineEdit.textChanged.connect(self.loadRegObject)

        self.disableSpimagineCheckBox.clicked.connect(lambda:
            QtW.QMessageBox.information(self, 'Restart Required',
                "Please quit and restart LLSpy for changes to take effect",
                QtW.QMessageBox.Ok))

        self.availableCompression = []
        # get compression options
        for ctype in ['lbzip2', 'bzip2', 'pbzip2', 'pigz', 'gzip']:
            if llspy.util.which(ctype) is not None:
                self.availableCompression.append(ctype)
        self.compressTypeCombo.addItems(self.availableCompression)

        i = 0
        for comptype in ('lbzip2', 'pigz', 'bzip2'):
            try:
                i = self.availableCompression.index(comptype)
            except ValueError:
                continue
        self.compressTypeCombo.setCurrentIndex(i)

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

        # TODO: reenable when feature is ready
        self.watchModeServerRadio.setChecked(True)
        self.watchModeAcquisitionRadio.setDisabled(True)

        self.watcherStatus = QtW.QLabel()
        self.statusBar.insertPermanentWidget(0, self.watcherStatus)

        if not _SPIMAGINE_IMPORTED:
            self.prevBackendMatplotlibRadio.setChecked(True)
            self.prevBackendSpimagineRadio.setDisabled(True)
            self.prevBackendSpimagineRadio.setText("spimagine [unavailable]")

        self.show()
        self.raise_()

        if self.watchDirCheckBox.isChecked():
            self.startWatcher()

    @QtCore.pyqtSlot()
    def startWatcher(self):
        self.watchdir = self.watchDirLineEdit.text()
        if osp.isdir(self.watchdir):
            logger.info('Starting watcher on {}'.format(self.watchdir))
            # TODO: check to see if we need to save watchHandler
            self.watcherStatus.setText("👁 {}".format(osp.basename(self.watchdir)))
            watchHandler = MainHandler()
            watchHandler.foundLLSdir.connect(self.on_watcher_found_item)
            watchHandler.lostListItem.connect(self.listbox.removePath)
            self.observer = Observer()
            self.observer.schedule(watchHandler, self.watchdir, recursive=True)
            self.observer.start()

    @QtCore.pyqtSlot()
    def stopWatcher(self):
        if self.observer is not None and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logging.info('Stopped watcher on {}'.format(self.watchdir))
            self.watchdir = None
        if not self.observer:
            self.watcherStatus.setText("")
        for watcher in self.activeWatchers.values():
            watcher.terminate()

    @QtCore.pyqtSlot(str)
    def on_watcher_found_item(self, path):
        if self.watchModeAcquisitionRadio.isChecked():
            # assume more files are coming (like during live acquisition)
            activeWatcher = ActiveWatcher(path)
            activeWatcher.finished.connect(activeWatcher.deleteLater)
            activeWatcher.status_update.connect(self.statusBar.showMessage)
            self.activeWatchers[path] = activeWatcher
        elif self.watchModeServerRadio.isChecked():
            # assumes folders are completely finished when dropped
            self.listbox.addPath(path)
            self.onProcess()

    @QtCore.pyqtSlot()
    def changeWatchDir(self):
        self.watchDirLineEdit.setText(QtW.QFileDialog.getExistingDirectory(
            self, 'Choose directory to monitor for new LLSdirs', '',
            QtW.QFileDialog.ShowDirsOnly))
        if self.watchDirCheckBox.isChecked():
            self.stopWatcher()
            self.startWatcher()

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
            file = QtW.QFileDialog.getOpenFileName(self,
                    'Choose registration file ',  os.path.expanduser('~'),
                    "Text Files (*.reg *.txt *.json)")[0]
            if file is None or file is '':
                return
        self.RegProcessPathLineEdit.setText(file)

    def saveCurrentAsDefault(self):
        if len(defaultSettings.childKeys()):
            reply = QtW.QMessageBox.question(self, 'Save Settings',
                "Overwrite existing default GUI settings?",
                QtW.QMessageBox.Yes | QtW.QMessageBox.No,
                QtW.QMessageBox.No)
            if reply != QtW.QMessageBox.Yes:
                return
        guisave(self, defaultSettings)

    def loadDefaultSettings(self):
        if not len(defaultSettings.childKeys()):
            reply = QtW.QMessageBox.information(self, 'Load Settings',
                "Default settings have not yet been saved.  Use Save Settings")
            if reply != QtW.QMessageBox.Yes:
                return
        guirestore(self, defaultSettings, programDefaults)

    def openLLSdir(self):
        path = QtW.QFileDialog.getExistingDirectory(self,
            'Choose LLSdir to add to list', '', QtW.QFileDialog.ShowDirsOnly)
        if path is not None:
            self.listbox.addPath(path)

    def incrementProgress(self):
        # with no values, simply increment progressbar
        self.progressBar.setValue(self.progressBar.value() + 1)

    def onPreview(self):
        self.previewButton.setDisabled(True)
        self.previewButton.setText('Working...')
        if self.listbox.rowCount() == 0:
            QtW.QMessageBox.warning(self, "Nothing Added!",
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
                QtW.QMessageBox.warning(self, "Nothing Selected!",
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
                box.setText("You have selected to preview a subset of channels, but "
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
            raise err.InvalidSettingsError("Parameters are incomplete for this item. "
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

        w, thread = newWorkerThread(workers.TimePointWorker, obj, tRange, cRange, self.lastopts,
            workerConnect={
                            'previewReady': self.displayPreview,
                            'updateCrop': self.updateCrop,
                          }, start=True)

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
                win.sliceWidget.sliderSlice.setValue(int(arr.shape[-3]/2))

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
            QtW.QMessageBox.warning(self, "Nothing Added!",
                'Nothing to process! Drag and drop folders into the list',
                QtW.QMessageBox.Ok, QtW.QMessageBox.NoButton)
            self.enableProcessButton()
            return

        # store current options for this processing run.  TODO: Unecessary?
        try:
            self.optionsOnProcessClick = self.getValidatedOptions()
            op = self.optionsOnProcessClick
            if not (op['nIters'] or
                    (op['keepCorrected'] and (op['correctFlash'] or op['medianFilter'])) or
                    op['saveDeskewedRaw'] or
                    op['doReg']):
                self.show_error_window('Nothing done!', 'Nothing done!',
                    'No deconvolution, deskewing, image correction, '
                    'or registration performed. Check GUI options.', '')

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

        idx = 0  # might use this later to spawn more threads
        opts = self.optionsOnProcessClick

        # check if already processed
        if llspy.util.pathHasPattern(self.currentPath, '*' + llspy.config.__OUTPUTLOG__):
            if not opts['reprocess']:
                msg = 'Skipping! Path already processed: {}'.format(self.currentPath)
                logger.info(msg)
                self.statusBar.showMessage(msg, 5000)
                skip()
                return

        if not len(QtCore.QCoreApplication.instance().gpuset):
            self.on_proc_finished()
            raise err.InvalidSettingsError("No GPUs selected. Check Config Tab")

        self.statusBar.showMessage('Starting processing on {} ...'.format(shortname(self.currentPath)))
        LLSworker, thread = newWorkerThread(workers.LLSitemWorker,
            obj, idx, opts, workerConnect={
                'finished': self.on_item_finished,
                'status_update': self.statusBar.showMessage,
                'progressMaxVal': self.progressBar.setMaximum,
                'progressValue': self.progressBar.setValue,
                'progressUp': self.incrementProgress,
                'clockUpdate': self.clock.display,
                'error': self.abort_workers,
                'skipped': self.skip_item,
                # 'error': self.errorstring  # implement error signal?
            })

        self.LLSItemThreads.append((thread, LLSworker))

        # connect mainGUI abort LLSworker signal to the new LLSworker
        self.sig_abort_LLSworkers.connect(LLSworker.abort)

        # prepare and start LLSworker:
        # thread.started.connect(LLSworker.work)
        thread.start()  # this will emit 'started' and start thread's event loop

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

    def getValidatedOptions(self):
        options = {
            'correctFlash': self.camcorCheckBox.isChecked(),
            'flashCorrectTarget': self.camcorTargetCombo.currentText(),
            'medianFilter': self.medianFilterCheckBox.isChecked(),
            'keepCorrected': self.saveCamCorrectedCheckBox.isChecked(),
            'trimZ': (self.trimZ0SpinBox.value(), self.trimZ1SpinBox.value()),
            'trimY': (self.trimY0SpinBox.value(), self.trimY1SpinBox.value()),
            'trimX': (self.trimX0SpinBox.value(), self.trimX1SpinBox.value()),
            'nIters': self.iterationsSpinBox.value() if self.doDeconGroupBox.isChecked() else 0,
            'nApodize': self.apodizeSpinBox.value(),
            'nZblend': self.zblendSpinBox.value(),
            # if bRotate == True and rotateAngle is not none: rotate based on sheet angle
            # this will be done in the LLSdir function
            'bRotate': self.rotateGroupBox.isChecked(),
            'rotate': (self.rotateOverrideSpinBox.value() if
                       self.rotateOverrideCheckBox.isChecked() else None),
            'saveDeskewedRaw': self.saveDeskewedCheckBox.isChecked(),
            # 'bsaveDecon': self.saveDeconvolvedCheckBox.isChecked(),
            'MIP': tuple([int(i) for i in (self.deconXMIPCheckBox.isChecked(),
                                           self.deconYMIPCheckBox.isChecked(),
                                           self.deconZMIPCheckBox.isChecked())]),
            'rMIP': tuple([int(i) for i in (self.deskewedXMIPCheckBox.isChecked(),
                                            self.deskewedYMIPCheckBox.isChecked(),
                                            self.deskewedZMIPCheckBox.isChecked())]),
            'mergeMIPs': self.deconJoinMIPCheckBox.isChecked(),
            # 'mergeMIPsraw': self.deskewedJoinMIPCheckBox.isChecked(),
            'uint16': ('16' in self.deconvolvedBitDepthCombo.currentText()),
            'uint16raw': ('16' in self.deskewedBitDepthCombo.currentText()),
            'bleachCorrection': self.bleachCorrectionCheckBox.isChecked(),
            'doReg': self.doRegistrationGroupBox.isChecked(),
            'regMode': (self.RegProcessChannelRefModeCombo.currentText()
                if self.RegProcessChannelRefModeCombo.currentText() else 'none'),
            'otfDir': self.otfFolderLineEdit.text() if self.otfFolderLineEdit.text() is not '' else None,
            'compressRaw': self.compressRawCheckBox.isChecked(),
            'compressionType': self.compressTypeCombo.currentText(),
            'reprocess': self.reprocessCheckBox.isChecked(),
            'width': self.cropWidthSpinBox.value(),
            'shift': self.cropShiftSpinBox.value(),
            'cropPad': self.autocropPadSpinBox.value(),
            'background': (-1 if self.backgroundAutoRadio.isChecked()
                           else self.backgroundFixedSpinBox.value())

            # 'bRollingBall': self.backgroundRollingRadio.isChecked(),
            # 'rollingBall': self.backgroundRollingSpinBox.value()
        }

        if options['nIters'] > 0 and not options['otfDir']:
            raise err.InvalidSettingsError(
                'Deconvolution requested but no OTF available', 'Check OTF path')

        # otherwise a cudaDeconv error occurs... could FIXME in cudadeconv
        if not options['saveDeskewedRaw']:
            options['rMIP'] = (0, 0, 0)

        if options['correctFlash']:
            options['camparamsPath'] = self.camParamTiffLineEdit.text()
            if not osp.isfile(options['camparamsPath']):
                raise err.InvalidSettingsError(
                    'Flash pixel correction requested, but camera parameters file '
                    'not provided.', 'Check CamParam Tiff path.\n\n'
                    'For information on how to generate this file for your camera,'
                    ' see documentation at llspy.readthedocs.io')
        else:
            options['camparamsPath'] = None

        rCalibText = self.RegProcessPathLineEdit.text()
        if rCalibText and rCalibText is not '':
            options['regCalibPath'] = rCalibText
        else:
            options['regCalibPath'] = None


        if not self.RegProcessChannelRefCombo.currentText():
            options['regRefWave'] = 0
        else:
            text = self.RegProcessChannelRefCombo.currentText()
            if text.isdigit():
                options['regRefWave'] = int(text)
            else:
                if options['doReg']:
                    self.show_error_window('Problem with channel registration settings!',
                        'Registration Error', 'Channel registration was selected, '
                        'but the selected reference wavelength does not seem to be a '
                        'number.  This may be an issue with filenaming convention.  '
                        'Please read docs regarding data structure assumptions.')
                else:
                    options['regRefWave'] = 0


        if options['doReg'] and options['regCalibPath'] in (None, ''):
            raise err.InvalidSettingsError(
                'Registration requested, but calibration object not provided.',
                'In the post-processing section, click Use RegFile to load a '
                'previously generated registration file '
                'or click Use Dataset to use a folder of fiducials. Registraion '
                'files can be generated on the registration tab.')

        if options['doReg']:
            ro = llspy.llsdir.get_regObj(options['regCalibPath'])
            if not ro or not ro.isValid:
                raise err.InvalidSettingsError(
                    'Registration requested, but calibration path does not point to'
                    ' either a valid registration file or a fiducial marker dataset.  '
                    'Check registration settings, or default registration folder in '
                    'config tab.')

        if self.croppingGroupBox.isChecked():
            if self.cropAutoRadio.isChecked():
                options['cropMode'] = 'auto'
            elif self.cropManualRadio.isChecked():
                options['cropMode'] = 'manual'
        else:
            options['cropMode'] = 'none'

        procCRangetext = self.processCRangeLineEdit.text()
        if procCRangetext:
            options['cRange'] = string_to_iterable(procCRangetext)
        else:
            options['cRange'] = None

        procTRangetext = self.processTRangeLineEdit.text()
        if procTRangetext:
            options['tRange'] = string_to_iterable(procTRangetext)
        else:
            options['tRange'] = None

        return options

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

        worker, thread = newWorkerThread(workers.CompressionWorker, item, 'compress',
            self.compressTypeCombo.currentText(),
            workerConnect={
                'status_update': self.statusBar.showMessage,
                'finished': lambda: self.statusBar.showMessage('Compression finished', 4000)
            },
            start=True)
        self.compressionThreads.append((worker, thread))

    def decompressSelected(self):
        for item in self.listbox.selectedPaths():
            if not llspy.util.find_filepattern(item, '*.tar*'):
                self.statusBar.showMessage(
                    'No .tar file found in ' + shortname(item), 4000)
                continue

            def onfinish():
                self.listbox.llsObjects[item]._register_tiffs()
                self.statusBar.showMessage('Decompression finished', 4000)

            worker, thread = newWorkerThread(workers.CompressionWorker, item, 'decompress',
                self.compressTypeCombo.currentText(),
                workerConnect={
                    'status_update': self.statusBar.showMessage,
                    'finished': onfinish
                },
                start=True)
            self.compressionThreads.append((worker, thread))


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
            path = QtW.QFileDialog.getExistingDirectory(self,
                    'Choose Directory to Undo', os.path.expanduser('~'),
                    QtW.QFileDialog.ShowDirsOnly)
            if path:
                llspy.llsdir.undo_rename_iters(path)
        elif reply == 0:  # yes role  hit
            if not hasattr(self.listbox, 'renamedPaths') or not self.listbox.renamedPaths:
                return
            for path in self.listbox.renamedPaths:
                llspy.llsdir.undo_rename_iters(path)
                self.listbox.renamedPaths.remove(path)

    def renameSelected(self):
        if not hasattr(self.listbox, 'renamedPaths'):
            self.listbox.renamedPaths = []
        for item in self.listbox.selectedPaths():
            llspy.llsdir.rename_iters(item)
            self.listbox.renamedPaths.append(item)
            self.listbox.removePath(item)
            [self.listbox.addPath(osp.join(item, p)) for p in os.listdir(item)]

    def toggleOptOut(self, value):
        err._OPTOUT = True if value else False

    def checkBundled(self, value):
        if value:
            try:
                self.setBinaryPath(llspy.cudabinwrapper.get_bundled_binary())
            except llspy.cudabinwrapper.CUDAbinException:
                raise err.MissingBinaryError('Could not load bundled cudaDeconv.  Check that it is installed.  read docs')
        else:
            self.setBinaryPath(self.cudaDeconvPathLineEdit.text())

    def setBinaryPath(self, path):
        workers._CUDABIN = path
        logger.info("Using cudaDeconv binary: {}".format(workers._CUDABIN))

    @QtCore.pyqtSlot()
    def setCudaDeconvPath(self, path=None):
        if not path:
            path = QtW.QFileDialog.getOpenFileName(self,
                    'Choose cudaDeconv Binary', '/usr/local/bin/')[0]
        if path:
            if llspy.cudabinwrapper.is_cudaDeconv(path):
                self.cudaDeconvPathLineEdit.setText(path)
                if self.useBundledBinariesCheckBox.isChecked():
                    self.setBinaryPath(self.cudaDeconvPathLineEdit.text())
            else:
                QtW.QMessageBox.critical(self, 'Invalid File',
                    "That file does not appear to be a valid cudaDeconv exectuable",
                    QtW.QMessageBox.Ok)

    @QtCore.pyqtSlot()
    def setOTFdirPath(self, path=None):
        if not path:
            path = QtW.QFileDialog.getExistingDirectory(self,
                    'Choose OTF Directory', os.path.expanduser('~'), QtW.QFileDialog.ShowDirsOnly)
        if path:
            if llspy.otf.dir_has_otfs(path):
                self.otfFolderLineEdit.setText(path)
            else:
                QtW.QMessageBox.warning(self, 'Invalid OTF Directory',
                    "That folder does not appear to contain any OTF or PSF tif files",
                    QtW.QMessageBox.Ok)

    @QtCore.pyqtSlot()
    def setCamParamPath(self, path=None):
        if not path:
            path = QtW.QFileDialog.getOpenFileName(self,
                    'Choose camera parameters tiff',  os.path.expanduser('~'),
                    "Image Files (*.tif *.tiff)")[0]
        if path:
            if llspy.camera.seemsValidCamParams(path):
                self.camParamTiffLineEdit.setText(path)
            else:
                QtW.QMessageBox.critical(self, 'Invalid File',
                    'That file does not appear to be a valid camera parameters tiff.  '
                    'It must have >= 3 planes.  See llspy.readthedocs.io for details.',
                    QtW.QMessageBox.Ok)

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
            self.msgBox.setInformativeText(info+'\n')
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

            pref.stateChanged.connect(lambda value:
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

    def quitProgram(self):
        guisave(self, sessionSettings)
        sessionSettings.setValue('cleanExit', True)
        sessionSettings.sync()
        QtW.QApplication.quit()


if __name__ == "__main__":
    print("main function moved to llspy.bin.llspy_gui")
