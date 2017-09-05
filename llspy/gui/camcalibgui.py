from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets as QtW
import llspy
from llspy import camcalib
import numpy as np
import os
import sys
import tifffile as tf
from llspy.gui.camcordialog import Ui_Dialog as camcorDialog
from llspy.gui.helpers import newWorkerThread

thisDirectory = os.path.dirname(os.path.abspath(__file__))


class CamCalibWorker(QtCore.QObject):
    """docstring for TimePointWorker"""

    finished = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal()
    setProgMax = QtCore.pyqtSignal(int)
    setStatus = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal()

    def __init__(self, folder, darkAVG, darkSTD=None):
        super(CamCalibWorker, self).__init__()
        self.folder = folder
        self.darkAVG = darkAVG
        self.darkSTD = darkSTD

    @QtCore.pyqtSlot()
    def work(self):

        try:
            self.setStatus.emit('Loading tiff files... progress bar output will begin in a minute')
            ch0list, ch1list = camcalib.get_channel_list(self.folder)
            pre, post = camcalib.combine_stacks(ch0list, ch1list, self.darkAVG)
            nz, ny, nx = pre.shape
            self.setProgMax.emit(ny*nx)

            self.setStatus.emit('Calculating correction image... This will take a while')
            results = camcalib.parallel_fit(pre, post, self.progress.emit)

            # add dark images to the results
            results = np.vstack((results, self.darkSTD[None, :, :]))
            if self.darkSTD is not None:
                results = np.vstack((results, self.darkSTD[None, :, :]))

            # create name
            E = llspy.LLSdir(self.folder)
            outname = "FlashParam_sn{}_roi{}_date{}.tif".format(
                E.settings.camera.serial,
                "-".join([str(i) for i in E.settings.camera.roi]),
                E.date.strftime('%Y%m%d'))

            # reorder and write
            results = llspy.util.reorderstack(results, 'zyx')
            tf.imsave(os.path.join(self.folder, outname), results, imagej=True,
                resolution=(1 / E.parameters.dx, 1 / E.parameters.dx),
                metadata={
                    'unit': 'micron',
                    'hyperstack': 'true',
                    'mode': 'composite'})

            self.setStatus.emit('Calibration Tiff written to input folder.  You may close this dialog.')
            self.finished.emit()

        except Exception:
            (excepttype, value, traceback) = sys.exc_info()
            sys.excepthook(excepttype, value, traceback)
            self.error.emit()


class CamCalibDialog(QtW.QDialog, camcorDialog):

    def __init__(self, parent=None):
        super(CamCalibDialog, self).__init__(parent)
        self.setupUi(self)  # method inherited from form_class to init UI
        self.setWindowTitle("Flash4.0 Charge Carryover Correction")
        self.abortButton.hide()
        self.picture.setPixmap(QtGui.QPixmap(os.path.join(thisDirectory, "before_after.png")))
        self.progressBar.setValue(0)
        self.statusLabel.setText('Select folder and press run...')

        self.selectFolderPushButton.clicked.connect(self.setFolder)

        self.choseDarkImgPushButton.clicked.connect(lambda:
            self.darkImageLineEdit.setText(
                QtW.QFileDialog.getOpenFileName(
                    self, 'Chose Dark_AVG.tif', '',
                    "Image Files (*.tif *.tiff)")[0]))

        self.runButton.clicked.connect(self.processFolder)

    def setFolder(self):
        self.camCalibFolderLineEdit.setText(
            QtW.QFileDialog.getExistingDirectory(
                self, 'Select folder with calibration images',
                '', QtW.QFileDialog.ShowDirsOnly))
        folder = self.camCalibFolderLineEdit.text()

        if os.path.isfile(os.path.join(folder, 'dark_AVG.tif')):
            self.darkImageLineEdit.setText(os.path.join(folder, 'dark_AVG.tif'))

    def processFolder(self):

        folder = self.camCalibFolderLineEdit.text()
        # futhermore ... there should be a folder inside of that called 'dark' that
        # holds the following files:
        # '.\dark\dark_AVG.tif'  -> an Avgerage projection of > 20,000 dark images
        # '.\dark\dark_STD.tif'  -> an StdDev projection of > 20,000 dark images
        darkavg = tf.imread(os.path.join(folder, 'dark_AVG.tif'))
        if os.path.isfile(os.path.join(folder, 'dark_STD.tif')):
            darkstd = tf.imread(os.path.join(folder, 'dark_STD.tif'))
        else:
            darkstd = None

        self.worker, self.thread = newWorkerThread(CamCalibWorker, folder, darkavg, darkstd,
            workerConnect={
                'progress': self.incrementProgress,
                'setProgMax': self.progressBar.setMaximum,
                'setStatus': self.statusLabel.setText,
                'finished': self.abortButton.hide,
            }, start=True)
        # self.abortButton.clicked.connect(self.thread.quit)
        # self.abortButton.show()

    def incrementProgress(self):
        self.progressBar.setValue(self.progressBar.value() + 1)


if __name__ == "__main__":

    app = QtW.QApplication(sys.argv)
    # dlg = LogWindow()
    # dlg.show()
    camcorDialog = CamCalibDialog()
    camcorDialog.show()

    sys.exit(app.exec_())
