import sys
import os
import numpy as np
import logging
from PyQt5 import QtWidgets, QtCore, QtGui
#from llspy.gui.img_window import Ui_Dialog
from img_window import Ui_Dialog
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
        self.maxSlider.setMaximum(400)
        self.maxSlider.setProperty("value", 170)
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
        self.isComplex = False
        self.setData(data)
        self.projection = projection
        self._overlay = False
        self.curImgIdx = [0, 0, 0]  # T, C, Z
        self.cplxAttrib = "Amp" # other choices: 'Real', 'Imag', 'Phase'

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

    @QtCore.pyqtSlot(str)
    def setCplxAttrib(self, val):
        ## Select which attribute of complex values to display:
        if val in ("Amp", "Real", "Imag", "Phase"):
            self.cplxAttrib = val
        else:
            self.cplxAttrib = None
        self._dataChanged.emit()

    def setData(self, data):
        logger.debug('data changed')
        self.ndim = len(data.shape)
        if self.ndim < 2:
            raise ValueError("Not an image!")

        self.isComplex = (data.dtype==np.complex64 or data.dtype==np.complex128)

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
        if not self.isComplex:
            self.cmax = [self.data[:, c, :, :, :].max() for c in range(self.nC)]
            self.cmin = [self.data[:, c, :, :, :].min() for c in range(self.nC)]
        else:
            self.cmax = [np.abs(self.data)[:, c, :, :, :].max() for c in range(self.nC)]
            self.cmin = [0 for c in range(self.nC)]

        self.chanSettings = [{'active': True,
                              'lut': LUTS[preferredLUTs[c]],
                              'scale': 1.7}
                             for c in range(self.nC)]

        if not self.isComplex:
            self.maxVal = self.data.max()
            self.minVal = self.data.min()
        else:
            self.maxVal = (np.abs(self.data)).max()
            self.minVal = (np.abs(self.data)).min()
        self._dataChanged.emit()

    @QtCore.pyqtSlot(int, int)
    def setIdx(self, dim, idx):
        self.curImgIdx[dim] = idx
        self._idxChanged.emit()

    @QtCore.pyqtSlot(int, int)
    def getIdx(self, dim):
        return self.curImgIdx[dim]

    def recalcMinMax(self):
        # only necessary when data is complex-valued
        if self.isComplex:
            if self.cplxAttrib == "Amp":
                ampArr = np.abs(self.data)
                self.maxVal = ampArr.max()
                self.minVal = ampArr.min()
            elif self.cplxAttrib == "Phase":
                phaseArr = np.angle(self.data)
                self.maxVal = phaseArr.max()
                self.minVal = phaseArr.min()
            elif self.cplxAttrib == "Real":
                self.maxVal = self.data.real.max()
                self.minVal = self.data.real.min()
            elif self.cplxAttrib == "Imag":
                self.maxVal = self.data.imag.max()
                self.minVal = self.data.imag.min()
            else:
                pass
        else:
            logger.debug('recalcMinMax() called on non-complex data')


    def max(self):
        return self.maxVal

    def min(self):
        return self.minVal

    def range(self):
        return self.maxVal - self.minVal

    def getCurrent(self):
        dataToReturn = None
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

            dataToReturn = np.minimum(rgb, 1)

        elif self.projection is not None:
            # generate 2D projection
            dataToReturn = getattr(np, self.projection)(self.data[tuple(self.curImgIdx[:2])], 0)
        else:
            # use full 3D data
            dataToReturn = self.data[tuple(self.curImgIdx)]

        if self.isComplex:
            if self.cplxAttrib == "Amp":
                return np.abs(dataToReturn)
            elif self.cplxAttrib == "Real":
                return dataToReturn.real
            elif self.cplxAttrib == "Imag":
                return dataToReturn.imag
            elif self.cplxAttrib == "Phase":
                return np.angle(dataToReturn)
            else:
                pass
        else:
            return dataToReturn


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
        # self.data_range = data.max() - data.min()
        # self.data_min = data.min()
        self.data._idxChanged.connect(self.updateImage)
        self.data._dataChanged.connect(self.updateImage)

        def f_c(x, y):
            return 'x=%.2f  y=%.2f ' % (x, y)
                
        self.ax.format_coord = f_c

    def setDisplayOptions(self, options):
        self.displayOptions = options
        if not ('cmap' in self.displayOptions):
            self.displayOptions['cmap'] = 'cubehelix'
        self.cmaps = tuple({self.displayOptions['cmap'], 'gray', 'afmhot', 'cubehelix', 'inferno'})
        self.currentCmap = 1

    @QtCore.pyqtSlot(int, int)
    def setContrast(self, valmin=None, valmax=None):
        if valmin is not None:
            self.displayOptions['vmin'] = self.data.min() + valmin/100.*self.data.range()
        if valmax is not None:
            self.displayOptions['vmax'] = self.data.min() + valmax/100.*self.data.range()
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
        if 'norm' in self.displayOptions:
            self.image.set_norm(self.displayOptions['norm'])

        self.draw()

    @QtCore.pyqtSlot(int)
    def setGamma(self, val):
        if (val==100):
            self.displayOptions['norm'] = matplotlib.colors.Normalize(vmin=self.displayOptions['vmin'], vmax=self.displayOptions['vmax'])
        else:
            self.displayOptions['norm'] = matplotlib.colors.PowerNorm(val/100., vmin=self.displayOptions['vmin'], vmax=self.displayOptions['vmax'])
        self._contrastChanged.emit()

class ImgDialog(QtWidgets.QDialog, Ui_Dialog):
    def __init__(self, data, title='Image Preview', cmap=None, info=None, parent=None):
        super(ImgDialog, self).__init__(parent)
        self.setupUi(self)   #defined in class Ui_Dialog
        self.setWindowTitle(title)

        self.cmap = cmap

        self.infoText.hide()
        self.chanSelectWidget.hide()

        self.data = DataModel(data)

        if self.data.isComplex:
            self.complexAttrib.setEnabled(True)
        else:
            self.complexAttrib.setEnabled(False)

        self.canvas = MplCanvas()
        self.canvas.setData(self.data)

        self.waves = []
        if info is not None:
            if isinstance(info, dict):
                txt = "\n".join(["{} = {}".format(k, v) for k, v in info.items()])
                self.infoText.setText(txt)
                if 'wavelength' in info:
                    self.waves = info['wavelength']
            elif isinstance(info, str):
                self.infoText.setText(info)

        self.initialize()

        self.maxProjButton.toggled.connect(self.setProjection)
        self.stdProjButton.toggled.connect(self.setProjection)
        self.meanProjButton.toggled.connect(self.setProjection)
        self.overlayButton.toggled.connect(self.setOverlay)

        self.complexAttrib.currentTextChanged.connect(self.setComplexAttrib)

        self.playButton.clicked.connect(self.playMovie)
        self.fpsSpin.valueChanged.connect(self.changeFPS)

        self.Zslider.valueChanged.connect(lambda val: self.setDimIdx(2, val))
        self.Cslider.valueChanged.connect(lambda val: self.setDimIdx(1, val))
        self.Tslider.valueChanged.connect(lambda val: self.setDimIdx(0, val))

        self.minSlider.valueChanged.connect(lambda val: self.minSliderMoved(val))
        self.maxSlider.valueChanged.connect(lambda val: self.maxSliderMoved(val))
        self.gamSlider.valueChanged.connect(lambda val: self.gamSliderMoved(val))

        self.gammaText = QtWidgets.QLabel(self)
        def verticalText_paintEvent(evt):
            # To be able to draw gamma label vertically
            painter = QtGui.QPainter(self.gammaText)
            painter.setPen(QtCore.Qt.black)
            painter.rotate(90)
            painter.drawText(QtCore.QPoint(0,0), self.gammaText.text())

        self.gammaText.paintEvent = verticalText_paintEvent

        def gamSliderResizeEvent(evt):
            # To keep gamma text next to handle when slider height changes
            self.gammaLabelUpdate()

        self.gamSlider.resizeEvent = gamSliderResizeEvent

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
                 self.minSlider, self.minLabel, self.gamSlider, self.gamLabel)
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
        # dataRange = datamax - datamin
        vmin_init = datamin# - dataRange * 0.03
        vmax_init = datamax# * 0.55

        displayOptions = {
            # 'vmin': int(vmin_init),
            # 'vmax': int(vmax_init),
            'vmin': vmin_init,
            'vmax': vmax_init,
            'cmap': self.cmap,
        }

        self.canvas.setDisplayOptions(displayOptions)
        self.canvas.createImage()

        # self.minSlider.setMinimum(datamin - dataRange * 0.1)
        # self.minSlider.setMaximum(datamin + dataRange * 0.1)
        # self.minSlider.setValue(vmin_init)
        self.minSlider.setRange(-5, 105)
        self.minSlider.setValue(0)
        # self.maxSlider.setMinimum(datamin)
        # self.maxSlider.setMaximum(datamax)
        # self.maxSlider.setValue(vmax_init)
        self.maxSlider.setRange(-5, 105)
        self.maxSlider.setValue(100)

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

    def setComplexAttrib(self, attrib):
        self.data.setCplxAttrib(attrib)
        self.data.recalcMinMax()
        self.canvas.setContrast(self.minSlider.value(), self.maxSlider.value())
        self.gamSlider.setValue(100)  # reset to default gamma; necessary?
        if (attrib == 'Phase'):
            self.gamSlider.setEnabled(False)
        else:
            self.gamSlider.setEnabled(True)

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
        elif event.key() == QtCore.Qt.Key_O:
            self.overlayButton.click()
        elif event.key() == QtCore.Qt.Key_Space:
            if hasattr(self, 'timer') and self.timer.isActive():
                self.stopMovie()
            else:
                self.playMovie()
        elif event.key() == QtCore.Qt.Key_C:
            self.canvas.cycleCMAP()

    def closeEvent(self, evnt):
        del self.data.data
        del self.data
        self.deleteLater()
        super(ImgDialog, self).closeEvent(evnt)

    def minSliderMoved(self, pos):
        # Also moves max slider up if min slider is overtaking max slider
        if pos >= self.maxSlider.sliderPosition():
            self.maxSlider.setSliderPosition(pos+1)
        self.canvas.setContrast(valmin=pos)

    def maxSliderMoved(self, pos):
        # Also moves min slider down if max slider drops below min slider
        if pos <= self.minSlider.sliderPosition():
            self.minSlider.setSliderPosition(pos-1)
        self.canvas.setContrast(valmax=pos)

    def gamSliderMoved(self, pos):
        # Also updates gamma value label beside the handle
        self.canvas.setGamma(pos)
        self.gammaText.setNum(pos/100.)
        self.gammaLabelUpdate()
        
    def gammaLabelUpdate(self):
        sliderHeight = self.gamSlider.size().height()
        sliderXorigin = self.gamSlider.pos().x()
        sliderYorigin = self.gamSlider.pos().y()
        handleVPos = (1. - float(self.gamSlider.value() - self.gamSlider.minimum()) / \
                      (self.gamSlider.maximum() - self.gamSlider.minimum())) \
                      * sliderHeight
        self.gammaText.move(QtCore.QPoint(sliderXorigin + 13,
                                          int(handleVPos)+sliderYorigin-30))

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    if len(sys.argv) > 1:
        import tifffile as tf
        path = sys.argv[1]
        im = tf.imread(path)
        if 'fft' in sys.argv:
            im = np.fft.fftshift(np.fft.fftn(np.fft.fftshift(im)))
    else:
        im = np.random.rand(4, 2, 10, 100, 100) * 32000
    main = ImgDialog(im)
    main.show()

    sys.exit(app.exec_())
