import os
import llspy
from PyQt5 import QtCore, uic
from PyQt5 import QtWidgets as QtW
from llspy import util
from llspy.gui import workers, dialogs
from llspy.gui.helpers import reveal, shortname, newWorkerThread
from llspy.gui.implist import IMP_DIR

Ui_Main_GUI = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'main_gui.ui'))[0]
# form_class = uic.loadUiType('./llspy/gui/main_gui.ui')[0]  # for debugging


class LLSpyActions(QtW.QMainWindow, Ui_Main_GUI):
    def __init__(self, *args, **kwargs):
        super(LLSpyActions, self).__init__(*args, **kwargs)
        self.setupUi(self)  # method inherited from form_class to init UI

        self.actionReveal.triggered.connect(self.revealSelected)
        self.actionMerge_MIPs_from_folder.triggered.connect(self.mergeMIPtool)
        self.actionOpen_LLSdir.triggered.connect(self.openLLSdir)
        self.actionRun.triggered.connect(self.onProcess)
        self.actionClose_All_Previews.triggered.connect(self.close_all_previews)
        self.actionPreview.triggered.connect(self.onPreview)
        self.actionReduce_to_Raw.triggered.connect(self.reduceSelected)
        self.actionFreeze.triggered.connect(self.freezeSelected)
        self.actionCompress_Folder.triggered.connect(self.compressSelected)
        self.actionDecompress_Folder.triggered.connect(self.decompressSelected)
        self.actionConcatenate.triggered.connect(self.concatenateSelected)
        self.actionRename_Scripted.triggered.connect(self.renameSelected)
        self.actionUndo_Rename_Iters.triggered.connect(self.undoRenameSelected)
        self.actionAbout_LLSpy.triggered.connect(self.showAboutWindow)
        self.actionHelp.triggered.connect(self.showHelpWindow)

        self.openPluginsAction = self.menuFile.addAction('Open Plugins Folder')
        self.openPluginsAction.triggered.connect(self.showPlugins)
        self.openPluginsAction = self.menuLLSpy.addAction('Preferences...')
        self.openPluginsAction.triggered.connect(self.showPreferences)

    def showPlugins(self):
        if not os.path.exists(IMP_DIR):
            os.mkdir(IMP_DIR)
        reveal(IMP_DIR)

    def showPreferences(self):
        win = dialogs.PreferencesWindow()
        win.exec_()

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

