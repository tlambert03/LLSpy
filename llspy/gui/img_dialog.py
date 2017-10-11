import sys
import os
import numpy as np

from PyQt5 import QtWidgets, QtCore
from llspy.gui.img_window import Ui_Dialog


import matplotlib
matplotlib.use("Qt5Agg")

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# here = os.path.dirname(os.path.abspath(__file__))
# form_class = uic.loadUiType(os.path.join(here, 'img_window.ui'))[0]  # for debugging


class DataModel(QtCore.QObject):

    _idxChanged = QtCore.pyqtSignal()
    _dataChanged = QtCore.pyqtSignal()

    def __init__(self, data=None, projection=None):
        super(DataModel, self).__init__()
        self.setData(data)
        self.projection = projection
        self.curImgIdx = [0, 0, 0]  # T, C, Z

    @QtCore.pyqtSlot(str)
    def setProjType(self, projtype):
        if projtype in ('min', 'max', 'std', 'mean'):
            self.projection = projtype
        else:
            self.projection = None
        self._dataChanged.emit()

    def setData(self, data):
        print('data changed')
        self.ndim = len(data.shape)
        if self.ndim < 2:
            raise ValueError("Not an image!")

        if self.ndim == 2:
            self.shape = (1, 1, 1) + data.shape
            self.data = data.copy().reshape(self.shape)
        elif self.ndim == 3:
            self.shape = (1, 1) + data.shape
            self.data = data.copy().reshape(self.shape)
        elif self.ndim == 4:
            self.shape = (1,) + data.shape
            self.data = data.copy().reshape(self.shape)
        elif self.ndim == 5:
            self.shape = data.shape
            self.data = data.copy()
        else:
            raise TypeError("data should be 3-5 dimensional! shape = %s" % str(data.shape))

        self._dataChanged.emit()

    @QtCore.pyqtSlot(int, int)
    def setIdx(self, dim, idx):
        self.curImgIdx[dim] = idx
        self._idxChanged.emit()

    @QtCore.pyqtSlot(int, int)
    def getIdx(self, dim):
        return self.curImgIdx[dim]

    def max(self):
        return self.data.max()

    def min(self):
        return self.data.min()

    def getCurrent(self):
        if self.projection is not None:
            return getattr(np, self.projection)(self.data[tuple(self.curImgIdx[:2])], 0)
        else:
            return self.data[tuple(self.curImgIdx)]

    def __getitem__(self, tczTuple):
        return np.squeeze(self.data[tuple(tczTuple)])


class MplCanvas(FigureCanvas):

    _contrastChanged = QtCore.pyqtSignal()

    def __init__(self):
        self.figure = Figure(figsize=(12,12), tight_layout=True, facecolor='r')
        self.figure.patch.set_alpha(0)  # transparent background
        self.ax = self.figure.add_subplot(111)
        super(MplCanvas, self).__init__(self.figure)

    def setData(self, data):
        self.data = data
        self.data._idxChanged.connect(self.updateImage)
        self.data._dataChanged.connect(self.updateImage)

    def setDisplayOptions(self, options):
        self.displayOptions = options
        if not hasattr(self.displayOptions, 'cmap'):
            self.displayOptions['cmap'] = 'cubehelix'
        self.cmaps = tuple({self.displayOptions['cmap'], 'gray', 'afmhot', 'cubehelix', 'inferno'})
        self.currentCmap = 1

    @QtCore.pyqtSlot(dict)
    def setContrast(self, **kwargs):
        self.displayOptions.update(kwargs)
        self._contrastChanged.emit()

    def cycleCMAP(self):
        self.currentCmap += 1
        newmap = self.cmaps[self.currentCmap % len(self.cmaps)]
        self.displayOptions['cmap'] = newmap
        self._contrastChanged.emit()

    def createImage(self):
        self.image = self.ax.imshow(self.data.getCurrent(), **self.displayOptions)
        self.cbar = self.figure.colorbar(self.image, fraction=0.045, pad=0.04)
        self._contrastChanged.connect(self.updateImage)
        self.draw()

    def updateImage(self):
        self.image.set_data(self.data.getCurrent())
        self.image.set_clim(vmin=self.displayOptions['vmin'], vmax=self.displayOptions['vmax'])
        self.image.set_cmap(self.displayOptions['cmap'])
        self.draw()

class ImgDialog(QtWidgets.QDialog, Ui_Dialog):
    def __init__(self, data, title='Image Preview', cmap=None, info=None, parent=None):
        super(ImgDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle(title)

        self.cmap = cmap

        self.infoText.hide()

        self.data = DataModel(data)
        self.canvas = MplCanvas()
        self.canvas.setData(self.data)

        self.initialize()

        if info is not None:
            self.infoText.setText(info)

        self.maxProjButton.toggled.connect(self.setProjection)
        self.stdProjButton.toggled.connect(self.setProjection)
        self.meanProjButton.toggled.connect(self.setProjection)
        self.minProjButton.toggled.connect(self.setProjection)
        self.playButton.clicked.connect(self.playMovie)
        self.fpsSpin.valueChanged.connect(self.changeFPS)

        self.Zslider.valueChanged.connect(lambda val: self.setDimIdx(2, val))
        self.Cslider.valueChanged.connect(lambda val: self.setDimIdx(1, val))
        self.Tslider.valueChanged.connect(lambda val: self.setDimIdx(0, val))
        self.maxSlider.valueChanged.connect(lambda val: self.canvas.setContrast(vmax=val))
        self.minSlider.valueChanged.connect(lambda val: self.canvas.setContrast(vmin=val))
        # self.gamSlider.valueChanged.connect(self.canvas.setGamma)

        self.gamSlider.hide()
        self.gamLabel.hide()
        self.infoButton.toggled.connect(self.toggleInfo)

        self.toolbar = NavigationToolbar(self.canvas, self)
        self.mainLayout.insertWidget(0, self.toolbar)
        self.imgLayout.insertWidget(3, self.canvas)

        # this code is a start to a matplotlib independent viewer
        # a QPixMap gets painted into a Qlabel
        # can use qimage2ndarray to convert np.array to QImage
        # then QPixmap.fromImage(img)
        # currently struggling with resizing...

        # self.label = QtWidgets.QLabel()
        # self.label.setScaledContents(True)
        # self.label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored )
        # import qimage2ndarray as qi
        # img = qi.array2qimage(self.data[0,0,0])
        # self.label.setPixmap(QtGui.QPixmap.fromImage(img))
        # self.imgLayout.addWidget(self.label)

        self.show()

    @QtCore.pyqtSlot(bool)
    def setProjection(self, val):
        if self.sender() == self.maxProjButton:
            if val:
                self.stdProjButton.setChecked(False)
                self.meanProjButton.setChecked(False)
                self.minProjButton.setChecked(False)
        elif self.sender() == self.stdProjButton:
            if val:
                self.maxProjButton.setChecked(False)
                self.meanProjButton.setChecked(False)
                self.minProjButton.setChecked(False)
        elif self.sender() == self.meanProjButton:
            if val:
                self.stdProjButton.setChecked(False)
                self.maxProjButton.setChecked(False)
                self.minProjButton.setChecked(False)
        elif self.sender() == self.minProjButton:
            if val:
                self.stdProjButton.setChecked(False)
                self.maxProjButton.setChecked(False)
                self.meanProjButton.setChecked(False)

        projtype = None
        if self.maxProjButton.isChecked():
            projtype = 'max'
        if self.meanProjButton.isChecked():
            projtype = 'mean'
        if self.stdProjButton.isChecked():
            projtype = 'std'
        if self.minProjButton.isChecked():
            projtype = 'min'

        self.data.setProjType(projtype)

    def toggleInfo(self, val):
        w = self.size().width()
        h = self.size().height()
        if val:
            self.infoText.show()
            self.resize(w, h + 210)
        else:
            self.infoText.hide()
            self.resize(w, h - 210)

    def initialize(self):

        datamax = self.data.max()
        datamin = self.data.min()
        dataRange = datamax - datamin
        vmin_init = datamin - dataRange * 0.02
        vmax_init = datamax * 0.6

        displayOptions = {
            'vmin': int(vmin_init),
            'vmax': int(vmax_init),
            'cmap': self.cmap,
        }

        self.canvas.setDisplayOptions(displayOptions)
        self.canvas.createImage()

        self.minSlider.setMinimum(datamin - dataRange * 0.1)
        self.minSlider.setMaximum(datamin + dataRange * 0.1)
        self.minSlider.setValue(vmin_init)
        self.maxSlider.setMinimum(datamin)
        self.maxSlider.setMaximum(datamax)
        self.maxSlider.setValue(vmax_init)

        nT, nC, nZ, nY, nX = self.data.shape
        self.data.setIdx(2, int(nZ/2))
        self.setDimIdx(0, 0)
        self.setDimIdx(1, 0)
        self.setDimIdx(2, int(nZ/2))

        if nT > 1:
            self.Twidget.show()
            self.Tslider.setMaximum(nT-1)
        else:
            self.Twidget.hide()
        if nC > 1:
            self.Cwidget.show()
            self.Cslider.setMaximum(nC-1)
        else:
            self.Cwidget.hide()
        if nZ > 1:
            self.Zwidget.show()
            self.Zslider.setMaximum(nZ-1)
        else:
            self.Zwidget.hide()

        figheight = 600
        yxAspect = self.data.shape[-2]/self.data.shape[-1]
        self.resize(figheight/yxAspect, figheight)

    def setDimIdx(self, dim, idx):
        F = {
            0: (self.Tslider.setValue, self.TsliderInfo.setText),
            1: (self.Cslider.setValue, self.CsliderInfo.setText),
            2: (self.Zslider.setValue, self.ZsliderInfo.setText),
        }
        self.data.setIdx(dim, idx)
        F[dim][0](idx)
        F[dim][1]('{} [{}]'.format(idx, self.data.shape[dim]))

    def incDimIndex(self, dim=0):
        newIdx = self.data.getIdx(dim) + 1
        if newIdx > (self.data.shape[dim] - 1):
            newIdx = 0
        self.setDimIdx(dim, newIdx)

    def decDimIndex(self, dim):
        self.setDimIdx(dim, self.data.getIdx(dim)-1)

    def playMovie(self):
        self.playButton.clicked.disconnect()
        self.playButton.clicked.connect(self.stopMovie)
        self.playButton.setText('stop')
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.incDimIndex)
        self.timer.start(1000/self.fpsSpin.value())

    def stopMovie(self):
        self.timer.stop()
        self.playButton.clicked.disconnect()
        self.playButton.clicked.connect(self.playMovie)
        self.playButton.setText('play')

    def changeFPS(self, val):
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
            self.timer.start(1000/self.fpsSpin.value())

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        elif event.key() in (QtCore.Qt.Key_1, QtCore.Qt.Key_M):
            if self.maxProjButton.isChecked():
                self.maxProjButton.setChecked(False)
            else:
                self.maxProjButton.setChecked(True)
        elif event.key() in (QtCore.Qt.Key_2, QtCore.Qt.Key_N):
            if self.minProjButton.isChecked():
                self.minProjButton.setChecked(False)
            else:
                self.minProjButton.setChecked(True)
        elif event.key() in (QtCore.Qt.Key_3, QtCore.Qt.Key_B):
            if self.meanProjButton.isChecked():
                self.meanProjButton.setChecked(False)
            else:
                self.meanProjButton.setChecked(True)
        elif event.key() in (QtCore.Qt.Key_4, QtCore.Qt.Key_V):
            if self.stdProjButton.isChecked():
                self.stdProjButton.setChecked(False)
            else:
                self.stdProjButton.setChecked(True)
        elif event.key() == QtCore.Qt.Key_I:
            if self.infoButton.isChecked():
                self.infoButton.setChecked(False)
            else:
                self.infoButton.setChecked(True)
        elif event.key() == QtCore.Qt.Key_Space:
            if hasattr(self, 'timer') and self.timer.isActive():
                self.stopMovie()
            else:
                self.playMovie()
        elif event.key() == QtCore.Qt.Key_C:
            self.canvas.cycleCMAP()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    main = ImgDialog(np.random.rand(4,2,10,100,100)*32000)
    main.show()

    sys.exit(app.exec_())
