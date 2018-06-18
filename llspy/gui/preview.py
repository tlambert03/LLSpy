from PyQt5 import QtWidgets, QtCore
from llspy.gui import workers, img_dialog, exceptions
from llspy.gui.helpers import newWorkerThread, shortname, string_to_iterable
from llspy.gui.settings import sessionSettings
from llspy import util
import os
import numpy as np
import logging

logger = logging.getLogger(__name__)
_SPIMAGINE_IMPORTED = False

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


class HasPreview(object):

    def onPreview(self):
        self.previewButton.setDisabled(True)
        self.previewButton.setText('Working...')
        if self.listbox.rowCount() == 0:
            QtWidgets.QMessageBox.warning(
                self, "Nothing Added!",
                'Nothing to preview! Drop LLS experiment folders into the list',
                QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton)
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
                QtWidgets.QMessageBox.warning(
                    self, "Nothing Selected!",
                    "Please select an item (row) from the table to preview",
                    QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton)
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
                box = QtWidgets.QMessageBox()
                box.setWindowTitle('Note')
                box.setText(
                    "You have selected to preview a subset of channels, but "
                    "have also selected Flash camera correction.  Note that the camera "
                    "correction requires all channels to be enabled.  Preview will not "
                    "reflect accurate camera correction.")
                box.setIcon(QtWidgets.QMessageBox.Warning)
                box.addButton(QtWidgets.QMessageBox.Ok)
                box.setDefaultButton(QtWidgets.QMessageBox.Ok)
                pref = QtWidgets.QCheckBox("Don't remind me.")
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
