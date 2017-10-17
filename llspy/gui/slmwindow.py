import sys
import numpy as np
import json
from llspy import slm as _slm

from PyQt5 import QtWidgets, QtCore, QtGui
from llspy.gui.slm_pattern_dialog import Ui_Dialog
import logging
logger = logging.getLogger(__name__)

with open('llspy/LUTs.json') as json_data:
    LUTs = json.load(json_data)
QLuts = {k: [QtGui.qRgb(*i) for i in v] for k, v in LUTs.items()}

SLMs = {
    'SXGA-3DM': {
        'pixel_size': 13.62,
        'xpix': 1280,
        'ypix': 1024,
    },
    'WXGA-3DM': {
        'pixel_size': 13.62,
        'xpix': 1280,
        'ypix': 768,
    },
    'QXGA-3DM': {
        'pixel_size': 8.2,
        'xpix': 2048,
        'ypix': 1536,
    },
    'Custom': {
        'pixel_size': 10,
        'xpix': 1000,
        'ypix': 1000,
    }
}


class SLMdialog(QtWidgets.QDialog, Ui_Dialog):
    def __init__(self, parent=None):
        super(SLMdialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('LLSpy :: SLM Pattern Generator')
        self.autofill = False

        self.fudgeSpin.valueChanged.connect(self.updateSpacing)
        self.wavelengthSpin.valueChanged.connect(self.updateSpacing)
        self.innerNASpin.valueChanged.connect(self.updateSpacing)
        self.autoSpacingCheckBox.toggled.connect(self.toggleAutoSpace)

        # self.slmBinaryLabel.setGeometry(QtCore.QRect(0, 0, 300, 800))
        # self.slmBinaryLabel.setStyleSheet("background-color: rgb(111, 174, 255);")
        self.slmBinaryLabel = QtWidgets.QLabel(self)
        self.slmBinaryLabel.setBackgroundRole(QtGui.QPalette.Base)
        self.slmBinaryLabel.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        # self.slmBinaryLabel.setScaledContents(True)

        self.sampleIntensityLabel = QtWidgets.QLabel(self)
        self.sampleIntensityLabel.setBackgroundRole(QtGui.QPalette.Base)
        self.sampleIntensityLabel.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        self.maskIntensityLabel = QtWidgets.QLabel(self)
        self.maskIntensityLabel.setBackgroundRole(QtGui.QPalette.Base)
        self.maskIntensityLabel.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        self.upperRightScroll.setBackgroundRole(QtGui.QPalette.Dark)
        self.lowerLeftScroll.setBackgroundRole(QtGui.QPalette.Dark)
        self.lowerRightScroll.setBackgroundRole(QtGui.QPalette.Dark)
        self.upperRightScroll.setWidget(self.maskIntensityLabel)
        self.lowerLeftScroll.setWidget(self.slmBinaryLabel)
        self.lowerRightScroll.setWidget(self.sampleIntensityLabel)

        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(60)

        self.lowerLeftTitle = QtWidgets.QLabel(self.lowerLeftScroll)
        self.lowerLeftTitle.setGeometry(QtCore.QRect(8, 137, 111, 16))
        self.lowerLeftTitle.setFont(font)
        self.lowerLeftTitle.setStyleSheet("color:#777;")
        self.lowerLeftTitle.setObjectName("lowerLeftTitle")
        self.lowerLeftTitle.setText("binary SLM mask")

        self.lowerRightTitle = QtWidgets.QLabel(self.lowerRightScroll)
        self.lowerRightTitle.setGeometry(QtCore.QRect(324, 137, 122, 16))
        self.lowerRightTitle.setFont(font)
        self.lowerRightTitle.setStyleSheet("color:#777;")
        self.lowerRightTitle.setObjectName("lowerRightTitle")
        self.lowerRightTitle.setText("Intensity At Sample")

        self.upperRightTitle = QtWidgets.QLabel(self.upperRightScroll)
        self.upperRightTitle.setGeometry(QtCore.QRect(190, 6, 122, 16))
        self.upperRightTitle.setFont(font)
        self.upperRightTitle.setStyleSheet("color:#777;")
        self.upperRightTitle.setObjectName("upperRightTitle")
        self.upperRightTitle.setText("Intensity After Mask")

        self.previewPatternButton.clicked.connect(self.previewPattern)
        self.writeFileButton.clicked.connect(self.writeFile)
        self.PatternPresetsCombo.currentTextChanged.connect(self.updatePreset)
        self.SLMmodelCombo.currentTextChanged.connect(self.setSLM)
        self.SLMmodelCombo.clear()
        self.SLMmodelCombo.addItems(SLMs.keys())
        self.setSLM('SXGA-3DM')
        self.PatternPresetsCombo.setCurrentText('Square Lattice, Fill Chip')

    def toggleAutoFill(self, val):
        dependents = [self.slm_pixelSize_spin, self.slm_xpix_spin,
                      self.magSpin, self.spacingSpin, self.fudgeSpin]
        if val:
            [d.valueChanged.connect(self.updateAutoBeams) for d in dependents]
            self.updateAutoBeams()
        else:
            try:
                [d.valueChanged.disconnect(self.updateAutoBeams) for d in dependents]
            except Exception:
                pass

    def updateAutoBeams(self):
        pixel = self.slm_pixelSize_spin.value()
        slm_xpix = self.slm_xpix_spin.value()
        mag = self.magSpin.value()
        spacing = self.spacingSpin.value()
        fillchip = 0.95
        n_beam = int(np.floor(1 + ((fillchip * (slm_xpix * (pixel/mag)/2)) / spacing)))
        self.nBeamsSpin.setValue(n_beam)

    def toggleAutoSpace(self, val):
        if val:
            self.fudgeSpin.valueChanged.connect(self.updateSpacing)
            self.wavelengthSpin.valueChanged.connect(self.updateSpacing)
            self.innerNASpin.valueChanged.connect(self.updateSpacing)
        else:
            self.fudgeSpin.valueChanged.disconnect(self.updateSpacing)
            self.wavelengthSpin.valueChanged.disconnect(self.updateSpacing)
            self.innerNASpin.valueChanged.disconnect(self.updateSpacing)

    def updateSpacing(self):
        fudge = self.fudgeSpin.value()
        wave = float(self.wavelengthSpin.value())/1000
        NA_inner = self.innerNASpin.value()
        spacing = fudge * wave / NA_inner
        self.spacingSpin.setValue(spacing)

    def previewPattern(self):

        slm_binary, sample_intensity, mask_intensity = _slm.makeSLMPattern(**self.getparams())

        data = slm_binary.astype(np.uint8)
        dh, dw = data.shape
        w = self.slmBinaryLabel.width()/2
        h = self.slmBinaryLabel.height()/2
        data = data[int(dh/2-h):int(dh/2+h), int(dw/2-w):int(dw/2+w)] * 255
        QI = QtGui.QImage(
            data, data.shape[1], data.shape[0], QtGui.QImage.Format_Indexed8)
        p = QtGui.QPixmap.fromImage(QI)
        self.slmBinaryLabel.setPixmap(p)

        data = sample_intensity
        data -= data.min()
        data /= data.max() * 0.65
        data = np.minimum(data, 1)
        data *= 255
        data = data.astype(np.uint8)
        dh, dw = data.shape
        w = self.sampleIntensityLabel.width()/2
        h = self.sampleIntensityLabel.height()/2
        data = data[int(dh/2-h):int(dh/2+h), int(dw/2-w):int(dw/2+w)] * 1
        QI = QtGui.QImage(
            data, data.shape[1], data.shape[0], QtGui.QImage.Format_Indexed8)
        QI.setColorTable(QLuts['VIRIDIS'])
        p = QtGui.QPixmap.fromImage(QI)
        self.sampleIntensityLabel.setPixmap(p)

        data = mask_intensity
        data -= data.min()
        data /= data.max() * 0.65
        data = np.minimum(data, 1)
        data *= 255
        data = data.astype(np.uint8)
        dh, dw = data.shape
        w = self.maskIntensityLabel.width()/2
        h = self.maskIntensityLabel.height()/2
        data = data[int(dh/2-h):int(dh/2+h), int(dw/2-w):int(dw/2+w)] * 1
        QI = QtGui.QImage(
            data, data.shape[1], data.shape[0], QtGui.QImage.Format_Indexed8)
        QI.setColorTable(QLuts['INFERNO'])
        p = QtGui.QPixmap.fromImage(QI)
        self.maskIntensityLabel.setPixmap(p)


        #w = self.slmBinaryLabel.width()
        #h = self.slmBinaryLabel.height()
        #self.slmBinaryLabel.setPixmap(p.scaled(w, h, QtCore.Qt.KeepAspectRatio))

    def writeFile(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Where do you want to save the SLM pattern?', '',
            QtWidgets.QFileDialog.ShowDirsOnly)
        if path is None or path is '':
            return
        logger.debug("Writing SLM pattern to " + path)
        _slm.makeSLMPattern(outdir=path, **self.getparams())

    def updatePreset(self, preset):
        logger.debug("SLM Preset changed to: " + preset)
        if preset == 'Manual':
            self.toggleAutoFill(False)
            self.nBeamsSpin.setEnabled(True)
            self.autoSpacingCheckBox.setChecked(True)
            self.autoSpacingCheckBox.setEnabled(True)
            self.spacingSpin.setDisabled(True)
            self.fudgeSpin.setEnabled(True)
        elif preset == 'Single Bessel':
            self.toggleAutoFill(False)
            self.nBeamsSpin.setValue(1)
            self.nBeamsSpin.setDisabled(True)
            self.autoSpacingCheckBox.setChecked(False)
            self.autoSpacingCheckBox.setDisabled(True)
            self.fudgeSpin.setDisabled(True)
            self.spacingSpin.setValue(1)
            self.spacingSpin.setDisabled(True)
            self.cropSpin.setValue(.0291)
        elif preset == '3-Beam Spaced':
            self.toggleAutoFill(False)
            self.nBeamsSpin.setValue(3.0)
            self.nBeamsSpin.setDisabled(True)
            self.autoSpacingCheckBox.setChecked(False)
            self.autoSpacingCheckBox.setDisabled(True)
            self.spacingSpin.setValue(22)
            self.spacingSpin.setEnabled(True)
            self.fudgeSpin.setDisabled(True)
            self.cropSpin.setValue(.05)
        elif preset == 'Square Lattice, Fill Chip':
            self.toggleAutoFill(True)
            self.nBeamsSpin.setDisabled(True)
            self.autoSpacingCheckBox.setChecked(True)
            self.autoSpacingCheckBox.setDisabled(True)
            self.cropSpin.setValue(.22)
            self.updateSpacing()
        else:
            pass

    def setSLM(self, slm):
        if slm not in SLMs:
            return
        if slm.lower() == 'custom':
            self.SLMmodelCombo.setCurrentText(slm)
            self.slm_pixelSize_spin.setEnabled(True)
            self.slm_xpix_spin.setEnabled(True)
            self.slm_ypix_spin.setEnabled(True)
        else:
            self.SLMmodelCombo.setCurrentText(slm)
            self.slm_pixelSize_spin.setValue(SLMs[slm]['pixel_size'])
            self.slm_xpix_spin.setValue(SLMs[slm]['xpix'])
            self.slm_ypix_spin.setValue(SLMs[slm]['ypix'])
            self.slm_pixelSize_spin.setDisabled(True)
            self.slm_xpix_spin.setDisabled(True)
            self.slm_ypix_spin.setDisabled(True)

    def getparams(self):
        opts = {}
        opts['wave'] = float(self.wavelengthSpin.value())/1000
        opts['NA_inner'] = self.innerNASpin.value()
        opts['NA_outer'] = self.outerNASpin.value()

        if opts['NA_outer'] <= opts['NA_inner']:
            raise InvalidSettingsError('Outer NA must be greater than inner NA')

        opts['fudge'] = self.fudgeSpin.value()
        if self.autoSpacingCheckBox.isChecked():
            opts['spacing'] = None
        else:
            opts['spacing'] = self.spacingSpin.value()
        opts['tilt'] = self.tiltSpin.value()
        opts['shift_x'] = self.shiftXSpin.value()
        opts['shift_y'] = self.shiftYSpin.value()
        opts['mag'] = self.magSpin.value()
        opts['crop'] = self.cropSpin.value()
        opts['n_beam'] = self.nBeamsSpin.value()
        opts['pixel'] = self.slm_pixelSize_spin.value()
        opts['slm_xpix'] = self.slm_xpix_spin.value()
        opts['slm_ypix'] = self.slm_ypix_spin.value()
        logger.info("SLM params: {}".format(opts))
        return opts

    @QtCore.pyqtSlot(str, str, str, str)
    def show_error_window(self, errMsg, title=None, info=None, detail=None):
        self.msgBox = QtWidgets.QMessageBox()
        if title is None or title is '':
            title = "LLSpy Error"
        self.msgBox.setWindowTitle(title)

        # self.msgBox.setTextFormat(QtCore.Qt.RichText)
        self.msgBox.setIcon(QtWidgets.QMessageBox.Warning)
        self.msgBox.setText(errMsg)
        if info is not None and info is not '':
            self.msgBox.setInformativeText(info+'\n')
        if detail is not None and detail is not '':
            self.msgBox.setDetailedText(detail)
        self.msgBox.exec_()


class SLMerror(Exception):
    pass


class InvalidSettingsError(SLMerror):
    def __init__(self, msg=None, detail=''):
        if msg is None:
            msg = "An unexpected error occured in the SLM Pattern Generator"
        super(InvalidSettingsError, self).__init__(msg)
        self.msg = msg
        self.detail = detail


class ExceptionHandler(QtCore.QObject):
    """General class to handle all raise exception errors in the GUI"""

    # error message, title, more info, detail (e.g. traceback)
    errorMessage = QtCore.pyqtSignal(str, str, str, str)

    def __init__(self):
        super(ExceptionHandler, self).__init__()

    def handler(self, etype, value, tb):
        err_info = (etype, value, tb)
        self.handleError(*err_info)

    def handleError(self, etype, value, tb):
        import traceback
        tbstring = "".join(traceback.format_exception(etype, value, tb))
        title = "SLM Pattern Generator Error"
        self.errorMessage.emit(value.msg, title, value.detail, tbstring)


def main():
    from llspy.util import getAbsoluteResourcePath
    app = QtWidgets.QApplication(sys.argv)
    appicon = QtGui.QIcon(getAbsoluteResourcePath('gui/logo_dark.png'))
    app.setWindowIcon(appicon)

    main = SLMdialog()
    main.show()

    # instantiate the execption handler
    exceptionHandler = ExceptionHandler()
    sys.excepthook = exceptionHandler.handler
    exceptionHandler.errorMessage.connect(main.show_error_window)

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
