import re
import numpy as np
from . import slm as _slm
from .luts import LUTs
from .slm_pattern_dialog import Ui_Dialog

from PyQt5 import QtWidgets, QtCore, QtGui
import logging
logger = logging.getLogger(__name__)

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


def str_is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def make8bit(data, p):
    data -= data.min()
    data /= np.percentile(data, p)
    data = np.minimum(data, 1)
    data *= 255
    return data.astype(np.uint8)


class PatternPreviewThread(QtCore.QThread):
    finished = QtCore.pyqtSignal(tuple)

    def __init__(self, params, mode='square'):
        QtCore.QThread.__init__(self)
        self.params = params
        if mode not in ('square', 'hex', 'ronchi'):
            raise ValueError('Mode must be one of {square, hex, ronchi}, got: ', mode)
        self.mode = mode

    def run(self):
        if self.mode == 'square':
            output = _slm.makeSLMPattern(pattern_only=False, **self.params)
        elif self.mode == 'hex':
            output = _slm.makeSLMPattern_hex(pattern_only=False, **self.params)
        elif self.mode == 'ronchi':
            width = self.params.get('width', 1)
            slm_xpix = self.params.get('slm_xpix', 1280)
            slm_ypix = self.params.get('slm_ypix', 1024)
            # orientation = self.params.get('orientation', 'horizontal')
            output = (_slm.ronchi_ruling(width, slm_xpix, slm_ypix),)
        self.finished.emit(output)


class PatternWriteThread(QtCore.QRunnable):

    def __init__(self, path, params, mode='square'):
        QtCore.QThread.__init__(self)
        self.params = params
        self.path = path
        if mode not in ('square', 'hex', 'ronchi'):
            raise ValueError('Mode must be one of {square, hex, ronchi}, got: ', mode)
        self.mode = mode
        # self.finished.connect(self.cleanup)

    def run(self):
        logger.debug("Writing {} SLM pattern to {}".format(self.mode, self.path))
        if self.mode == 'square':
            _slm.makeSLMPattern(outdir=self.path, pattern_only=True, **self.params)
        elif self.mode == 'hex':
            _slm.makeSLMPattern_hex(outdir=self.path, pattern_only=True, **self.params)
        elif self.mode == 'ronchi':
            width = self.params.get('width', 1)
            slm_xpix = self.params.get('slm_xpix', 1280)
            slm_ypix = self.params.get('slm_ypix', 1024)
            # orientation = self.params.get('orientation', 'horizontal')
            _slm.ronchi_ruling(width, slm_xpix, slm_ypix, outdir=self.path)


class SLMdialog(QtWidgets.QDialog, Ui_Dialog):

    PRESETS = ['Single Bessel', '3-Beam Spaced', 'Square Lattice, Fill Chip',
               'Square Lattice, Manual', 'Hex Lattice', 'Ronchi Ruling']

    def __init__(self, parent=None):
        super(SLMdialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('LLSpy :: SLM Pattern Generator')
        self.autofill = False
        self.mode = 'square'
        self.dithered = False
        self.writeThreadpool = QtCore.QThreadPool()

        self.PatternPresetsCombo.addItems(self.PRESETS)

        self.fudgeSpin.valueChanged.connect(self.updateSpacing)
        self.wavelengthSpin.valueChanged.connect(self.updateSpacing)
        self.innerNASpin.valueChanged.connect(self.updateSpacing)
        self.autoSpacingCheckBox.toggled.connect(self.toggleAutoSpace)

        # self.slmBinaryLabel.setStyleSheet("background-color: rgb(111, 174, 255);")
        self.slmBinaryLabel = QtWidgets.QLabel(self)
        self.slmBinaryLabel.setBackgroundRole(QtGui.QPalette.Base)
        self.slmBinaryLabel.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        #self.slmBinaryLabel.setGeometry(QtCore.QRect(0, 0, 476, 150))
        self.slmBinaryLabel.setFixedWidth(476)
        self.slmBinaryLabel.setFixedHeight(150)
        # self.slmBinaryLabel.setScaledContents(True)

        self.sampleIntensityLabel = QtWidgets.QLabel(self)
        self.sampleIntensityLabel.setBackgroundRole(QtGui.QPalette.Base)
        self.sampleIntensityLabel.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        #self.sampleIntensityLabel.setGeometry(QtCore.QRect(0, 0, 476, 150))
        self.sampleIntensityLabel.setFixedWidth(476)
        self.sampleIntensityLabel.setFixedHeight(150)

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
        #font.setFamily("Helvetica")
        font.setBold(True)
        font.setWeight(60)

        self.lowerLeftTitle = QtWidgets.QLabel(self.lowerLeftScroll)
        self.lowerLeftTitle.setGeometry(QtCore.QRect(5, 5, 170, 16))
        self.lowerLeftTitle.setFont(font)
        self.lowerLeftTitle.setStyleSheet("color:#777;")
        self.lowerLeftTitle.setObjectName("lowerLeftTitle")
        self.lowerLeftTitle.setText("binary SLM mask")

        self.lowerRightTitle = QtWidgets.QLabel(self.lowerRightScroll)
        self.lowerRightTitle.setGeometry(QtCore.QRect(5, 5, 170, 16))
        self.lowerRightTitle.setFont(font)
        self.lowerRightTitle.setStyleSheet("color:#777;")
        self.lowerRightTitle.setObjectName("lowerRightTitle")
        self.lowerRightTitle.setText("Intensity At Sample")

        self.upperRightTitle = QtWidgets.QLabel(self.upperRightScroll)
        self.upperRightTitle.setGeometry(QtCore.QRect(5, 5, 170, 16))
        self.upperRightTitle.setFont(font)
        self.upperRightTitle.setStyleSheet("color:#777;")
        self.upperRightTitle.setObjectName("upperRightTitle")
        self.upperRightTitle.setText("Intensity After Mask")

        self.ditherButton = QtWidgets.QPushButton(self.lowerRightScroll)
        self.ditherButton.setCheckable(True)
        w = self.lowerRightScroll.width()
        self.ditherButton.setGeometry(QtCore.QRect(w - 64, 4, 60, 25))
        self.ditherButton.setStyleSheet("color:#000;")
        self.ditherButton.setText("Dither")
        self.ditherButton.setFlat(True)
        self.ditherButton.setAutoFillBackground(True)
        self.ditherButton.clicked.connect(self.setDitherState)

        self.previewPatternButton.clicked.connect(self.previewPattern)
        self.writeFileButton.clicked.connect(self.writeFile)
        self.batchProcessButton.clicked.connect(self.batchProcess)
        self.chooseBatchOutputDir.clicked.connect(self.setBatchOutput)

        self.PatternPresetsCombo.currentTextChanged.connect(self.updatePreset)
        self.SLMmodelCombo.currentTextChanged.connect(self.setSLM)
        self.SLMmodelCombo.clear()
        self.SLMmodelCombo.addItems(SLMs.keys())
        self.setSLM('SXGA-3DM')
        self.PatternPresetsCombo.setCurrentText('Square Lattice, Fill Chip')

        lutnames = sorted([lut.title() for lut in QLuts.keys()])
        self.maskLUTCombo.addItems(lutnames)
        self.maskLUTCombo.setCurrentText('Inferno')
        self.maskLUTCombo.currentTextChanged.connect(self.plotMaskIntensity)
        self.sampleLUTCombo.addItems(lutnames)
        self.sampleLUTCombo.setCurrentText('Viridis')
        self.sampleLUTCombo.currentTextChanged.connect(self.plotSampleIntensity)

        rangeRX = QtCore.QRegExp("[\d.-]+:?([\d.-]+)?:?([\d.-]+)?")
        rangeValidator = QtGui.QRegExpValidator(rangeRX)
        self.batch_tilt.setValidator(rangeValidator)
        self.batch_xShift.setValidator(rangeValidator)
        self.batch_yShift.setValidator(rangeValidator)

        numCommaRX = QtCore.QRegExp("[\d,.]+")
        numCommaValidator = QtGui.QRegExpValidator(numCommaRX)
        self.batch_outerNA.setValidator(numCommaValidator)
        self.batch_innerNA.setValidator(numCommaValidator)
        numCommaRX = QtCore.QRegExp("[\d,]+")
        self.batch_wave.setValidator(QtGui.QRegExpValidator(numCommaRX))

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
            self.updateSpacing()
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
        self.previewPatternButton.setText('Calculating...')
        self.previewPatternButton.setDisabled(True)

        def show(output):
            if self.mode != 'ronchi':
                slm_binary, sample_intensity, mask_intensity = output
                self.sample_intensity_data = sample_intensity
                self.mask_intensity_data = mask_intensity
            else:
                slm_binary = output[0]

            data = slm_binary.astype(np.uint8)
            dh, dw = data.shape
            w = self.slmBinaryLabel.width()/2
            h = self.slmBinaryLabel.height()/2
            data = data[int(dh/2-h):int(dh/2+h), int(dw/2-w):int(dw/2+w)] * 255
            QI = QtGui.QImage(
                data, data.shape[1], data.shape[0], QtGui.QImage.Format_Indexed8)
            p = QtGui.QPixmap.fromImage(QI)
            self.slmBinaryLabel.setPixmap(p)

            if self.mode != 'ronchi':
                self.plotSampleIntensity()
                self.plotMaskIntensity()
            else:
                self.maskIntensityLabel.clear()
                self.sampleIntensityLabel.clear()

            self.previewPatternButton.setText('Preview Pattern')
            self.previewPatternButton.setEnabled(True)

        self.patternThread = PatternPreviewThread(self.getparams(), mode=self.mode)
        self.patternThread.finished.connect(show)
        self.patternThread.start()

    def setDitherState(self, value):
        self.dithered = bool(value)
        self.plotSampleIntensity()

    def plotMaskIntensity(self):
        if not hasattr(self, 'mask_intensity_data'):
            return

        data = make8bit(self.mask_intensity_data, 99.99)
        dh, dw = data.shape
        w = 150
        h = 150
        data = data[int(dh/2-h):int(dh/2+h), int(dw/2-w):int(dw/2+w)] * 1
        QI = QtGui.QImage(
            data, data.shape[1], data.shape[0], QtGui.QImage.Format_Indexed8)
        QI.setColorTable(QLuts[self.maskLUTCombo.currentText().lower()])
        p = QtGui.QPixmap.fromImage(QI)
        self.maskIntensityLabel.setPixmap(p)

    def plotSampleIntensity(self):
        if not hasattr(self, 'sample_intensity_data'):
            return

        if 'hex' in self.PatternPresetsCombo.currentText().lower():
            perc = 99.9
        elif 'square' in self.PatternPresetsCombo.currentText().lower():
            perc = 99.975
        else:
            perc = 99.999

        if self.dithered:
            data = self.sample_intensity_data.mean(1)
            w = self.sampleIntensityLabel.width()
            data = np.tile(data, (w, 1)).T
            data = np.require(make8bit(data, 99.99), requirements='C')
        else:
            data = make8bit(self.sample_intensity_data, perc)

        dh, dw = data.shape
        w = self.sampleIntensityLabel.width()/2
        h = self.sampleIntensityLabel.height()/2
        data = data[int(dh/2-h):int(dh/2+h), int(dw/2-w):int(dw/2+w)] * 1
        QI = QtGui.QImage(
            data, data.shape[1], data.shape[0], QtGui.QImage.Format_Indexed8)
        QI.setColorTable(QLuts[self.sampleLUTCombo.currentText().lower()])
        p = QtGui.QPixmap.fromImage(QI)
        self.sampleIntensityLabel.setPixmap(p)

    def writeFile(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Where do you want to save the SLM pattern?', '',
            QtWidgets.QFileDialog.ShowDirsOnly)
        if not path:
            return

        worker = PatternWriteThread(path, self.getparams(), mode=self.mode)
        self.writeThreadpool.start(worker)

    def updatePreset(self, preset):
        logger.debug("SLM Preset changed to: " + preset)
        self.mode = 'square'
        if 'hex' in preset.lower():
            self.mode = 'hex'
            self.HexWidget.show()
            self.nBeamsLabel.hide()
            self.nBeamsSpin.hide()
            self.outerNASpin.setValue(0.6)
            self.innerNASpin.setValue(0.505)
            self.idealNASpin.setValue(0.55)
            self.cropSpin.setValue(0.15)
        else:
            self.HexWidget.hide()
            self.nBeamsLabel.show()
            self.nBeamsSpin.show()
        if 'square' in preset.lower():
            self.SpacingWidget.show()
            self.autoSpacingCheckBox.setChecked(True)
        else:
            self.SpacingWidget.hide()
        if 'ronchi' in preset.lower():
            self.mode = 'ronchi'
            self.nBeamsLabel.setText('Line Width:')
            self.nBeamsLabel.setEnabled(True)
            self.nBeamsSpin.setEnabled(True)
            self.nBeamsSpin.setValue(1)
        else:
            self.nBeamsLabel.setText('# Beams:')

        if preset == 'Square Lattice, Manual':
            self.toggleAutoFill(False)
            self.nBeamsSpin.setEnabled(True)
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
            self.autoSpacingCheckBox.setDisabled(True)
            self.cropSpin.setValue(.22)
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

        if 'hex' in self.PatternPresetsCombo.currentText().lower():
            opts['NA_ideal'] = self.idealNASpin.value()
            if not (opts['NA_outer'] <= opts['NA_ideal'] <= opts['NA_inner']):
                raise InvalidSettingsError('Ideal NA must be between inner NA and outer NA')
            opts['fill_factor'] = self.hexFillFactorSpin.value()
            opts['bound'] = self.hexBoundCombo.currentText().lower()
        elif 'ronchi' in self.PatternPresetsCombo.currentText().lower():
            opts['width'] = self.nBeamsSpin.value()
        else:
            opts['n_beam'] = self.nBeamsSpin.value()
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
        opts['pixel'] = self.slm_pixelSize_spin.value()
        opts['slm_xpix'] = self.slm_xpix_spin.value()
        opts['slm_ypix'] = self.slm_ypix_spin.value()

        logger.info("SLM params: {}".format(opts))
        return opts

    def setBatchOutput(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Where do you want to save the SLM pattern?', '',
            QtWidgets.QFileDialog.ShowDirsOnly)
        if path:
            self.batch_outputDir.setText(path)
        return path

    def batchProcess(self):
        combos = self.getBatchParams()
        if not combos:
            return

        path = self.batch_outputDir.text()
        if path is None or path is '':
            path = self.setBatchOutput()
            if not path:
                return

        self.threadpool = QtCore.QThreadPool()
        for combo in combos:
            nbeam = combo[3][0]
            nbeam = int((nbeam-1)/2)+1 if not isinstance(nbeam, str) else nbeam
            params = {
                'wave': combo[0],
                'NA_inner': combo[1],
                'NA_outer': combo[2],
                'n_beam': nbeam,
                'spacing': combo[3][1],
                'shift_x': combo[4],
                'shift_y': combo[5],
                'tilt': round(combo[6], 2),
            }
            # for now, enforce "reasonable" cropping for single and 3-beam patterns
            if nbeam == 1:
                params['crop'] = 0.0291
            elif isinstance(params['spacing'], float) and params['spacing'] >= 6:
                params['crop'] = 0.06
            logger.debug("SLM batch params: {}".format(params))

            worker = PatternWriteThread(path, params)
            self.writeThreadpool.start(worker)
        # TODO: disable the write button until the threadpool is done

    def getBatchParams(self):
        errors = []
        waves = []
        innerNAs = []
        outerNAs = []
        bstups = []

        wave = self.batch_wave.text()
        if not any(wave.split(',')):
            errors.append('Must include at least one wavelength')
        else:
            for w in wave.split(','):
                if not w:
                    continue
                elif not w.isdigit() or not (300 < int(w) < 800):
                    errors.append('Wavelength "{}" not an integeger from 300-800'.format(w))
                else:
                    waves.append(float(w)/1000)

        innerNA = self.batch_innerNA.text()
        if not any(innerNA.split(',')):
            errors.append('Must include at least one innerNA')
        else:
            for w in innerNA.split(','):
                try:
                    w = float(w)
                    if not (0 < w < .7):
                        raise ValueError('')
                    else:
                        innerNAs.append(w)
                except ValueError:
                    errors.append('InnerNA "{}" not a float from 0-0.7'.format(w))

        outerNA = self.batch_outerNA.text()
        if not any(outerNA.split(',')):
            errors.append('Must include at least one outerNA')
        else:
            for w in outerNA.split(','):
                try:
                    w = float(w)
                    if not (0 < w < .7):
                        raise ValueError('')
                    else:
                        outerNAs.append(w)
                except ValueError:
                    errors.append('outerNA "{}" not a float from 0-0.7'.format(w))

        beamSpacing = self.batch_beamSpacing.text()
        tupstring = "(\\(.*?\\))"
        tups = re.findall(tupstring, beamSpacing)
        if not len(tups):
            errors.append('Must include at least one "(beams, spacing)" tuple')
        else:
            from ast import literal_eval as make_tuple
            for tup in tups:
                try:
                    t = list(make_tuple(tup))
                    if len(t) != 2:
                        errors.append('(beams, spacing) length not equal to 2: {}'.format(t))
                    else:
                        if not (1 <= t[0] <= 100):
                            errors.append('Number of Beams "{}" not an int between 0-100'.format(t[0]))
                            t[0] = None
                        else:
                            t[0] = int(t[0])
                        if not (0 <= t[1] <= 50):
                            errors.append('Beam Spacing "{}" not a float between 0-50'.format(t[1]))
                            t[1] = None
                        else:
                            t[1] = float(t[1])
                        if all([x is not None for x in t]):
                            bstups.append(tuple(t))
                except ValueError:
                    t = tup.strip('(').strip(')').split(',')
                    if len(t) != 2:
                        errors.append('(beams, spacing) length not equal to 2: {}'.format(t))
                    else:
                        if t[0].lower().strip() == 'fill':
                            t[0] = 'fill'
                        elif t[0].isdigit() and (1 <= int(t[0]) <= 100):
                            t[0] = int(t[0])
                        else:
                            errors.append('Number of Beams "{}" not an int between 0-100 or keyword "fill"'.format(t[0]))
                            t[0] = None
                        if t[1].lower().strip() == 'auto':
                            t[1] = 'auto'
                        elif str_is_float(t[1]) and (0 < float(t[1]) <= 50):
                            t[1] = float(t[1])
                        else:
                            errors.append('Beam Spacing "{}" must either be float between 0-50 or keyword "auto"'.format(t[1]))
                            t[1] = None
                        if all([t[0], t[1]]):
                            t[1] = None if t[1] == 'auto' else t[1]
                            bstups.append(tuple(t))

        xshift = self.batch_xShift.text()
        if not any(xshift.split(':')):
            xshifts = [0]
        else:
            try:
                a = [float(x) for x in xshift.split(':')]
                if len(a) > 1:
                    a[1] += .000001  # include stop index
                xshifts = np.arange(*a)
                xshifts = sorted(list(set([round(y, 2) for y in xshifts if -100 < y < 100])))
            except TypeError as e:
                errors.append('X Shift Range not valid: {}'.format(e))

        yshift = self.batch_yShift.text()
        if not any(yshift.split(':')):
            yshifts = [0]
        else:
            try:
                a = [float(y) for y in yshift.split(':')]
                if len(a) > 1:
                    a[1] += .000001  # include stop index
                yshifts = np.arange(*a)
                yshifts = sorted(list(set([round(y, 2) for y in yshifts if -100 < y < 100])))
            except TypeError as e:
                errors.append('Y Shift Range not valid: {}'.format(e))

        tilt = self.batch_tilt.text()
        if not any(tilt.split('-')):
            tilts = [0]
        else:
            try:
                a = [float(ti) for ti in tilt.split(':')]
                if len(a) > 1:
                    a[1] += .000001  # include stop index
                tilts = np.arange(*a)
                tilts = sorted(list(set([round(ti, 2) for ti in tilts if -1.5 <= ti <= 1.5])))
            except TypeError as e:
                errors.append('Tilt Range not valid: {}'.format(e))

        # yshift = self.batch_yShift.text()
        # tilt = self.batch_tilt.text()
        if len(errors):
            self.show_error_window('There were some errors in the batch slm settings:',
                title='Batch SLM Error', info='\n'.join(errors))
        else:
            from itertools import product
            a = [waves, innerNAs, outerNAs, bstups, xshifts, yshifts, tilts]
            combos = [list(c) for c in product(*a) if c[1] < c[2]]
            for c in combos:
                # if only 1 beam, force tilt to 0
                if isinstance(c[3][0], int) and c[3][0] == 1:
                    c[6] = 0
            combos = list(set([tuple(c) for c in combos]))  # get rid of duplicates, like from tilt=0
            if not len(combos):
                raise InvalidSettingsError('No valid combinations!',
                    'Is there at least one outerNA that is greater than the min innerNA?')
            return combos

    @QtCore.pyqtSlot(str, str, str, str)
    def show_error_window(self, errMsg, title=None, info=None, detail=None):
        self.msgBox = QtWidgets.QMessageBox()
        if title is None or title is '':
            title = "SLM Pattern Error"
        self.msgBox.setWindowTitle(title)

        # self.msgBox.setTextFormat(QtCore.Qt.RichText)
        self.msgBox.setIcon(QtWidgets.QMessageBox.Warning)
        self.msgBox.setText(errMsg)
        if info is not None and info is not '':
            self.msgBox.setInformativeText(info+'\n')
        if detail is not None and detail is not '':
            self.msgBox.setDetailedText(detail)
        self.msgBox.exec_()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            pass
        elif event.key() in (QtCore.Qt.Key_P,):
            self.previewPatternButton.click()
        elif event.key() in (QtCore.Qt.Key_R,):
            self.writeFileButton.click()
        elif event.key() in (QtCore.Qt.Key_D,):
            self.ditherButton.click()


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
        try:
            self.errorMessage.emit(value.msg, title, value.detail, tbstring)
        except Exception:
            self.errorMessage.emit(str(value), title, '', tbstring)


def getAbsoluteResourcePath(relativePath):
    """ Load relative path, in an environment agnostic way"""
    import sys
    import os

    try:
        # PyInstaller stores data files in a tmp folder refered to as _MEIPASS
        basePath = sys._MEIPASS
    except Exception:
        # If not running as a PyInstaller created binary, try to find the data file as
        # an installed Python egg
        try:
            basePath = os.path.dirname(sys.modules['slmgen'].__file__)
        except Exception:
            basePath = ''

        # If the egg path does not exist, assume we're running as non-packaged
        if not os.path.exists(os.path.join(basePath, relativePath)):
            basePath = 'slmgen'

    path = os.path.join(basePath, relativePath)
    # If the path still doesn't exist, this function won't help you
    if not os.path.exists(path):
        return None

    return path


def main():
    import sys

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
