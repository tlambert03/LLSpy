from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets as QtW
import llspy
from llspy import camcalib
from llspy.util import getAbsoluteResourcePath, pathHasPattern
import numpy as np
import os
import sys
import glob
import tifffile as tf
from llspy.gui.camcordialog import Ui_Dialog as camcorDialog
from llspy.gui.helpers import newWorkerThread

thisDirectory = os.path.dirname(os.path.abspath(__file__))


class CamCalibWorker(QtCore.QObject):
    """docstring for TimePointWorker"""

    finished = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal(int)
    setProgMax = QtCore.pyqtSignal(int)
    setStatus = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal()

    def __init__(self, folder, darkavg=None, darkstd=None):
        super(CamCalibWorker, self).__init__()
        self.folder = folder
        self.darkavg = darkavg
        self.darkstd = darkstd

    @QtCore.pyqtSlot()
    def work(self):

        def updatedarkstatus(prog):
            if prog == 0:
                self.setStatus.emit('Calculating offset map... [Step 2 of 4]')
            elif prog == 0:
                self.setStatus.emit('Calculating noise map... [Step 3 of 4]')
            return

        try:
            # first handle dark images
            self.setStatus.emit('Loading dark images... [Step 1 of 4]')
            darklist = glob.glob(os.path.join(self.folder, '*dark*.tif'))
            numdark = len(darklist)
            self.setProgMax.emit(numdark*2)
            darkavg = self.darkavg
            darkstd = self.darkstd
            if not (darkavg and darkstd):
                darkavg, darkstd = camcalib.process_dark_images(
                            self.folder, self.progress.emit, updatedarkstatus)

            with tf.TiffFile(darklist[0]) as t:
                nz, ny, nx = t.series[0].shape

            self.setProgMax.emit(ny*nx)
            self.setStatus.emit('Calculating correction image... This will take a while')
            out = camcalib.process_bright_images(self.folder, darkavg, darkstd, self.progress.emit)

            self.setStatus.emit("Done! Calibration file has been written to: {}".format(out[0]))

            self.finished.emit()

        except Exception:
            self.error.emit()
            self.finished.emit()
            raise


class CamCalibDialog(QtW.QDialog, camcorDialog):

    def __init__(self, parent=None):
        super(CamCalibDialog, self).__init__(parent)
        self.setupUi(self)  # method inherited from form_class to init UI
        self.setWindowTitle("Flash4.0 Charge Carryover Correction")
        self.abortButton.hide()
        self.picture.setPixmap(QtGui.QPixmap(getAbsoluteResourcePath("gui/before_after.png")))
        self.progressBar.setValue(0)
        self.statusLabel.setText('Select folder and press run...')

        self.selectFolderPushButton.clicked.connect(self.setFolder)

        self.DarkAVGPushButton.clicked.connect(lambda:
            self.darkAVGLineEdit.setText(
                QtW.QFileDialog.getOpenFileName(
                    self, 'Chose Dark_AVG.tif', '',
                    "Image Files (*.tif *.tiff)")[0]))

        self.DarkSTDPushButton.clicked.connect(lambda:
            self.darkSTDLineEdit.setText(
                QtW.QFileDialog.getOpenFileName(
                    self, 'Chose Dark_STD.tif', '',
                    "Image Files (*.tif *.tiff)")[0]))

        self.runButton.clicked.connect(self.processFolder)

    def setFolder(self):
        self.camCalibFolderLineEdit.setText(
            QtW.QFileDialog.getExistingDirectory(
                self, 'Select folder with calibration images',
                '', QtW.QFileDialog.ShowDirsOnly))
        folder = self.camCalibFolderLineEdit.text()

        if os.path.isfile(os.path.join(folder, 'dark_AVG.tif')):
            self.darkAVGLineEdit.setText(os.path.join(folder, 'dark_AVG.tif'))
        if os.path.isfile(os.path.join(folder, 'dark_STD.tif')):
            self.darkSTDineEdit.setText(os.path.join(folder, 'dark_STD.tif'))

    def processFolder(self):

        folder = self.camCalibFolderLineEdit.text()

        darkavg = None
        if os.path.isfile(self.darkAVGLineEdit.text()):
            darkavg = tf.imread(self.darkAVGLineEdit.text())
        elif os.path.isfile(os.path.join(folder, 'dark_AVG.tif')):
            darkavg = tf.imread(os.path.join(folder, 'dark_AVG.tif'))
        darkstd = None
        if os.path.isfile(self.darkSTDLineEdit.text()):
            darkstd = tf.imread(self.darkSTDLineEdit.text())
        elif os.path.isfile(os.path.join(folder, 'dark_STD.tif')):
            darkstd = tf.imread(os.path.join(folder, 'dark_STD.tif'))

        if not (darkavg and darkstd):
            if not pathHasPattern(folder, '*dark*.tif*'):
                QtW.QMessageBox.warning(self, "No dark images!",
                    'Camera calibration requires dark images, but none provided'
                    ' and none detected in provided folder.  Read docs for more info.',
                    QtW.QMessageBox.Ok, QtW.QMessageBox.NoButton)
                return

        self.worker, self.thread = newWorkerThread(CamCalibWorker, folder,
            darkavg, darkstd,
            workerConnect={
                'progress': self.incrementProgress,
                'setProgMax': self.resetWithMax,
                'setStatus': self.statusLabel.setText,
                'finished': self.abortButton.hide,
            }, start=True)
        # self.abortButton.clicked.connect(self._abort)
        # self.abortButton.show()

    @QtCore.pyqtSlot(int)
    def incrementProgress(self, val=None):
        self.progressBar.setValue(self.progressBar.value() + 1)

    @QtCore.pyqtSlot(int)
    def resetWithMax(self, maxm):
        self.progressBar.setMaximum(maxm)
        self.progressBar.setValue(0)

    @QtCore.pyqtSlot()
    def _abort(self):
        self.thread.terminate()
        self.thread.wait()


if __name__ == "__main__":

    app = QtW.QApplication(sys.argv)
    # dlg = LogWindow()
    # dlg.show()
    camcorDialog = CamCalibDialog()
    camcorDialog.show()

    sys.exit(app.exec_())
