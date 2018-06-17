import os
import llspy
from PyQt5 import QtCore
from PyQt5 import QtWidgets as QtW
from llspy import util
from llspy.gui import workers
from llspy.gui.helpers import reveal, guisave, guirestore, shortname, newWorkerThread

defaultINI = util.getAbsoluteResourcePath('gui/guiDefaults.ini')
defaultSettings = QtCore.QSettings("llspy", 'llspyDefaults')
programDefaults = QtCore.QSettings(defaultINI, QtCore.QSettings.IniFormat)


class LLSpyActions(object):
    def __init__(self, *args, **kwargs):
        super(LLSpyActions, self).__init__(*args, **kwargs)
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

        def revealSelected(self):
            selectedPaths = self.listbox.selectedPaths()
            if len(selectedPaths):
                for p in selectedPaths:
                    if os.path.exists(p):
                        reveal(p)

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

        def openLLSdir(self):
            path = QtW.QFileDialog.getExistingDirectory(
                self, 'Choose LLSdir to add to list',
                '', QtW.QFileDialog.ShowDirsOnly)
            if path is not None:
                self.listbox.addPath(path)

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

        def loadDefaultSettings(self):
            if not len(defaultSettings.childKeys()):
                reply = QtW.QMessageBox.information(
                    self, 'Load Settings', 'Default settings have not yet been '
                    'saved.  Use Save Settings')
                if reply != QtW.QMessageBox.Yes:
                    return
            guirestore(self, defaultSettings, programDefaults)

        def loadProgramDefaults(self):
            guirestore(self, QtCore.QSettings(), programDefaults)

        def reduceSelected(self):
            for item in self.listbox.selectedPaths():
                llspy.LLSdir(item).reduce_to_raw(
                    keepmip=self.saveMIPsDuringReduceCheckBox.isChecked())

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

        def freezeSelected(self):
            for item in self.listbox.selectedPaths():
                llspy.LLSdir(item).reduce_to_raw(
                    keepmip=self.saveMIPsDuringReduceCheckBox.isChecked())
                self.compressItem(item)

        def compressSelected(self):
            [self.compressItem(item) for item in self.listbox.selectedPaths()]

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

        def concatenateSelected(self):
            selectedPaths = self.listbox.selectedPaths()
            if len(selectedPaths) > 1:
                llspy.llsdir.concatenate_folders(selectedPaths)
                [self.listbox.removePath(p) for p in selectedPaths]
                [self.listbox.addPath(p) for p in selectedPaths]

        def renameSelected(self):
            if not hasattr(self.listbox, 'renamedPaths'):
                self.listbox.renamedPaths = []
            for item in self.listbox.selectedPaths():
                llspy.llsdir.rename_iters(item)
                self.listbox.renamedPaths.append(item)
                self.listbox.removePath(item)
                [self.listbox.addPath(os.path.join(item, p)) for p in os.listdir(item)]

        def undoRenameSelected(self):
            box = QtW.QMessageBox()
            box.setWindowTitle('Undo Renaming')
            box.setText("Do you want to undo all renaming that has occured "
                        "in this session?, or chose a directory?")
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
                if (not hasattr(self.listbox, 'renamedPaths')
                        or not self.listbox.renamedPaths):
                    return
                paths = self.listbox.renamedPaths

            for P in paths:
                for root, subd, file in os.walk(P):
                    self.listbox.removePath(root)
                    for d in subd:
                        self.listbox.removePath(os.path.join(root, d))
                llspy.llsdir.undo_rename_iters(P)
            self.listbox.renamedPaths = []

        def showAboutWindow(self):
            import datetime
            now = datetime.datetime.now()
            QtW.QMessageBox.about(
                self, 'LLSpy',
                'LLSpy v.{}\n'.format(llspy.__version__) +
                'Copyright ©  {}, '.format(now.year) +
                'President and Fellows of Harvard College.  All rights '
                'reserved.\n\nDeveloped by Talley Lambert\n\nThe cudaDeconv '
                'deconvolution program is owned and licensed by HHMI, Janelia '
                'Research Campus.  Please contact innovation@janlia.hhmi.org '
                'for access.')

        def showHelpWindow(self):
            QtW.QMessageBox.about(self, 'LLSpy', 'Please see documentation at llspy.readthedocs.io')

