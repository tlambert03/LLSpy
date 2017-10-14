import sys
import os
import numpy as np
import logging
from PyQt5 import QtWidgets, QtCore, QtGui
from llspy.gui.img_window import Ui_Dialog
logger = logging.getLogger(__name__)

import matplotlib
matplotlib.use("Qt5Agg")

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# here = os.path.dirname(os.path.abspath(__file__))
# form_class = uic.loadUiType(os.path.join(here, 'img_window.ui'))[0]  # for debugging

LUTS = {
    'Red':     [1, 0, 0],
    'Green':   [0, 1, 0],
    'Blue':    [0, 0, 1],
    'Cyan':    [0, 1, 1],
    'Yellow':  [1, 1, 0],
    'Magenta': [1, 0, 1],
    'Gray':    [1, 1, 1],
}

preferredLUTs = ['Green', 'Magenta', 'Cyan', 'Blue']

class channelSelector(QtWidgets.QWidget):
    def __init__(self, name, wave=None, parent=None):
        super(channelSelector, self).__init__(parent)
        if wave is None:
            wave = name
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setObjectName(name + "Layout")
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.checkBox = QtWidgets.QCheckBox(self)
        # self.checkBox.setMaximumSize(QtCore.QSize(60, 16777215))
        self.checkBox.setObjectName(name + "checkBox")
        self.checkBox.setText(name + ": " + str(wave))
        self.checkBox.setChecked(True)
        self.layout.addWidget(self.checkBox)

        self.maxSlider = QtWidgets.QSlider(self)
        self.maxSlider.setOrientation(QtCore.Qt.Horizontal)
        self.maxSlider.setObjectName(name + "slider")
        # self.maxSlider.setMaximumSize(QtCore.QSize(60, 16777215))
        self.maxSlider.setMinimum(50)
        self.maxSlider.setMaximum(300)
        self.maxSlider.setProperty("value", 100)
        self.layout.addWidget(self.maxSlider)

        self.LUTcombo = QtWidgets.QComboBox(self)
        self.LUTcombo.setEnabled(True)
        self.LUTcombo.setMaximumSize(QtCore.QSize(90, 16777215))
        self.LUTcombo.setObjectName(name + "LUTcombo")
        for lut in LUTS.keys():
            self.LUTcombo.addItem(lut)
        self.layout.addWidget(self.LUTcombo)
        self.checkBox.clicked['bool'].connect(self.LUTcombo.setEnabled)
        self.checkBox.clicked['bool'].connect(self.maxSlider.setEnabled)


class DataModel(QtCore.QObject):

    _idxChanged = QtCore.pyqtSignal()
    _dataChanged = QtCore.pyqtSignal()

    def __init__(self, data=None, projection=None):
        super(DataModel, self).__init__()
        self.setData(data)
        self.projection = projection
        self._overlay = False
        self.curImgIdx = [0, 0, 0]  # T, C, Z

    @QtCore.pyqtSlot(str)
    def setProjType(self, projtype):
        if projtype in ('min', 'max', 'std', 'mean'):
            self.projection = projtype
        else:
            self.projection = None
        self._dataChanged.emit()

    @QtCore.pyqtSlot(bool)
    def setOverlay(self, val):
        self._overlay = bool(val)
        self._dataChanged.emit()

    @QtCore.pyqtSlot(bool)
    def toggleChannel(self, val):
        chan = int(self.sender().objectName().strip('checkBox').strip('ch'))
        logger.debug("Channel {} {}activated".format(chan, '' if val else 'de'))
        self.chanSettings[chan]['active'] = val
        self._dataChanged.emit()

    @QtCore.pyqtSlot(str)
    def changeLUT(self, val):
        chan = int(self.sender().objectName().strip('LUTcombo').strip('ch'))
        logger.debug("Channel {} LUT changed to {}".format(chan, val))
        self.chanSettings[chan]['lut'] = LUTS[val]
        self._dataChanged.emit()

    @QtCore.pyqtSlot(int)
    def setChannelScale(self, val):
        chan = int(self.sender().objectName().strip('slider').strip('ch'))
        self.chanSettings[chan]['scale'] = val/100.00
        self._dataChanged.emit()

    def setData(self, data):
        logger.debug('data changed')
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

        self.nT, self.nC, self.nZ, self.nY, self.nX = self.data.shape
        self.cmax = [self.data[:, c, :, :, :].max() for c in range(self.nC)]
        self.cmin = [self.data[:, c, :, :, :].min() for c in range(self.nC)]

        self.chanSettings = [{'active': True,
                              'lut': LUTS[preferredLUTs[c]],
                              'scale': 1.0}
                             for c in range(self.nC)]

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
        if self._overlay:
            curT, curC, curZ = tuple(self.curImgIdx)

            if self.projection is not None:
                # get 2D projection
                data = getattr(np, self.projection)(self.data[curT], 1)
            else:
                data = self.data[curT, :, curZ]

            ny, nx = data.shape[-2:]
            rgb = np.zeros((ny, nx, 3))

            for chan in range(self.nC):
                if not self.chanSettings[chan]['active']:
                    continue
                lut = self.chanSettings[chan]['lut']
                D = np.maximum(data[chan].astype(np.float) - self.cmin[chan], 0)
                D /= self.cmax[chan] if self.projection is None else D.max()
                D *= self.chanSettings[chan]['scale']
                D = np.tile(D, (3, 1, 1)).transpose(1, 2, 0)
                lutmask = np.tile(lut, (ny, nx, 1))
                rgb += D * lutmask

            return np.minimum(rgb, 1)

        elif self.projection is not None:
            # generate 2D projection
            return getattr(np, self.projection)(self.data[tuple(self.curImgIdx[:2])], 0)
        else:
            # use full 3D data
            return self.data[tuple(self.curImgIdx)]

    def __getitem__(self, tczTuple):
        return np.squeeze(self.data[tuple(tczTuple)])


class MplCanvas(FigureCanvas):

    _contrastChanged = QtCore.pyqtSignal()

    def __init__(self):
        self.figure = Figure(figsize=(15, 15), tight_layout=True, facecolor='r')
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
        self.gamSlider.hide()
        self.gamLabel.hide()
        self.chanSelectWidget.hide()

        self.data = DataModel(data)
        self.canvas = MplCanvas()
        self.canvas.setData(self.data)

        self.waves = []
        if info is not None:
            if isinstance(info, dict):
                txt = "\n".join(["{} = {}".format(k, v) for k, v in info.items()])
                self.infoText.setText(txt)
                if 'cRange' in info and 'wavelength' in info:
                    self.waves = [info['wavelength'][i] for i in info['cRange']]
            elif isinstance(info, str):
                self.infoText.setText(info)

        self.initialize()

        self.maxProjButton.toggled.connect(self.setProjection)
        self.stdProjButton.toggled.connect(self.setProjection)
        self.meanProjButton.toggled.connect(self.setProjection)
        self.overlayButton.toggled.connect(self.setOverlay)

        self.playButton.clicked.connect(self.playMovie)
        self.fpsSpin.valueChanged.connect(self.changeFPS)

        self.Zslider.valueChanged.connect(lambda val: self.setDimIdx(2, val))
        self.Cslider.valueChanged.connect(lambda val: self.setDimIdx(1, val))
        self.Tslider.valueChanged.connect(lambda val: self.setDimIdx(0, val))
        self.maxSlider.valueChanged.connect(lambda val: self.canvas.setContrast(vmax=val))
        self.minSlider.valueChanged.connect(lambda val: self.canvas.setContrast(vmin=val))
        # self.gamSlider.valueChanged.connect(self.canvas.setGamma)

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
        elif self.sender() == self.stdProjButton:
            if val:
                self.maxProjButton.setChecked(False)
                self.meanProjButton.setChecked(False)
        elif self.sender() == self.meanProjButton:
            if val:
                self.stdProjButton.setChecked(False)
                self.maxProjButton.setChecked(False)

        projtype = None
        if self.maxProjButton.isChecked():
            projtype = 'max'
        if self.meanProjButton.isChecked():
            projtype = 'mean'
        if self.stdProjButton.isChecked():
            projtype = 'std'

        if val:
            self.Zwidget.hide()
        else:
            self.Zwidget.show()

        self.data.setProjType(projtype)

    @QtCore.pyqtSlot(bool)
    def setOverlay(self, val):
        group = (self.Cwidget, self.maxSlider, self.maxLabel,
                 self.minSlider, self.minLabel)
        if val:
            self.data.setOverlay(True)
            [item.hide() for item in group]
        else:
            self.data.setOverlay(False)
            [item.show() for item in group]

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
        vmin_init = datamin - dataRange * 0.03
        vmax_init = datamax * 0.55

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

        try:
            figheight = 600
            yxAspect = self.data.shape[-2]/self.data.shape[-1]
            if yxAspect > 0:
                self.resize(figheight/yxAspect, figheight+75)
        except Exception:
            pass

        for chan in range(nC):
            try:
                wave = self.waves[chan]
            except Exception:
                wave = None
            selector = channelSelector('ch'+str(chan), wave=wave)
            selector.LUTcombo.setCurrentText(preferredLUTs[chan])
            selector.checkBox.clicked['bool'].connect(self.data.toggleChannel)
            selector.LUTcombo.currentTextChanged.connect(self.data.changeLUT)
            selector.maxSlider.valueChanged.connect(self.data.setChannelScale)
            self.chanSelectLayout.addWidget(selector)

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
        elif event.key() in (QtCore.Qt.Key_M,):
            if self.maxProjButton.isChecked():
                self.maxProjButton.setChecked(False)
            else:
                self.maxProjButton.setChecked(True)
        elif event.key() in (QtCore.Qt.Key_N,):
            if self.meanProjButton.isChecked():
                self.meanProjButton.setChecked(False)
            else:
                self.meanProjButton.setChecked(True)
        elif event.key() in (QtCore.Qt.Key_B,):
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
