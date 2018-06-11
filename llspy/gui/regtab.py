import numpy as np
import logging
import json
import os
import llspy.gui.exceptions as err
from PyQt5 import QtCore, QtWidgets
from llspy import llsdir
from llspy.gui.helpers import newWorkerThread
from llspy.gui import workers
from llspy.gui.img_dialog import ImgDialog
from fiducialreg.fiducialreg import RegistrationError


logger = logging.getLogger(__name__)


class RegistrationTab(object):

    def __init__(self):
        self.RegCalibPathLoadButton.clicked.connect(self.setRegCalibPath)
        self.GenerateRegFileButton.clicked.connect(self.generateCalibrationFile)
        self.RegCalibPreviewButton.clicked.connect(self.previewRegistration)
        self.RegFilePathLoadButton.clicked.connect(self.loadRegistrationFile)
        self.RegCalib_channelRefCombo.clear()
        self.RegCalib_channelRefModeCombo.clear()

    def setRegCalibPath(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Set Registration Calibration Directory',
            '', QtWidgets.QFileDialog.ShowDirsOnly)
        if path is None or path is '':
            return
        RD = llsdir.RegDir(path)
        if not RD.isValid:
            raise err.RegistrationError(
                'Registration Calibration dir not valid: {}'.format(RD.path))

        self.RegCalibPathLineEdit.setText(path)
        layout = self.RegCalibRefGroupLayout
        group = self.RegCalibRefChannelsGroup
        for cb in group.findChildren(QtWidgets.QCheckBox):
            layout.removeWidget(cb)
            cb.setParent(None)
        for wave in RD.parameters.channels.values():
            box = QtWidgets.QCheckBox(str(wave), group)
            layout.addWidget(box)
            box.setChecked(True)

    def generateCalibrationFile(self):
        group = self.RegCalibRefChannelsGroup
        refs = [int(cb.text()) for cb in group.findChildren(QtWidgets.QCheckBox) if cb.isChecked()]
        path = self.RegCalibPathLineEdit.text()
        if not path or path == '':
            raise err.InvalidSettingsError('Please load a fiducial dataset path first')
        if not len(refs):
            raise err.InvalidSettingsError('Select at least one reference channel')

        autoThresh = self.RegAutoThreshCheckbox.isChecked()
        if autoThresh:
            minbeads = int(self.RegMinBeadsSpin.value())
            RD = llsdir.RegDir(path, usejson=False, threshold='auto', mincount=minbeads)
        else:
            threshold = int(self.RegBeadThreshSpin.value())
            RD = llsdir.RegDir(path, threshold=threshold, usejson=False)

        if not RD.isValid:
            raise err.RegistrationError(
                'Registration Calibration dir not valid: {}'.format(RD.path))

        outdir = QtWidgets.QFileDialog \
            .getExistingDirectory(self, 'Chose destination for registration file',
                                  '', QtWidgets.QFileDialog.ShowDirsOnly)
        if outdir is None or outdir is '':
            return

        class RegThread(QtCore.QThread):
            finished = QtCore.pyqtSignal(str)
            warning = QtCore.pyqtSignal(str, str)

            def __init__(self, RD, outdir, refs):
                QtCore.QThread.__init__(self)
                self.RD = RD
                self.outdir = outdir
                self.refs = refs

            def run(self):
                try:
                    outfile, outstring = self.RD.write_reg_file(outdir, refs=self.refs)
                    counts = self.RD.cloudset().count
                    if np.std(counts) > 15:
                        outstr = "\n".join(["wave: {}, beads: {}".format(
                            channel, counts[i]) for i, channel in enumerate(self.RD.waves)])
                        self.warning.emit('Suspicious Registration Result',
                                          "Warning: there was a large variation in the number "
                                          "of beads per channel.  Auto-detection may have failed.  "
                                          "Try changing 'Min number of beads'...\n\n" + outstr)
                except RegistrationError as e:
                    raise err.RegistrationError("Fiducial registration failed:", str(e))

                # also write to appdir ... may use it later
                # TODO: consider making app_dir a global APP attribute,
                # like gpulist
                from click import get_app_dir
                appdir = get_app_dir('LLSpy')
                if not os.path.isdir(appdir):
                    os.mkdir(appdir)
                regdir = os.path.join(appdir, 'regfiles')
                if not os.path.isdir(regdir):
                    os.mkdir(regdir)
                outfile2 = os.path.join(regdir, os.path.basename(outfile))
                with open(outfile2, 'w') as file:
                    file.write(outstring)

                logger.debug("registration file output: {}".format(outfile))
                logger.debug("registration file output: {}".format(outfile2))
                self.finished.emit(outfile)

        def finishup(outfile):
            self.statusBar.showMessage(
                'Registration file written: {}'.format(outfile), 5000)
            self.loadRegistrationFile(outfile)

        def notifyuser(title, msg):
            QtWidgets.QMessageBox.warning(self, title, msg, QtWidgets.QMessageBox.Ok)

        self.regthreads = []
        regthread = RegThread(RD, outdir, refs)
        regthread.finished.connect(finishup)
        regthread.warning.connect(notifyuser)
        self.regthreads.append(regthread)
        self.statusBar.showMessage(
            'Calculating registrations for ref channels: {}...'.format(refs))
        regthread.start()

    # TODO: this is mostly duplicate functionality of loadRegObject below
    def loadRegistrationFile(self, file=None):
        if not file:
            file = QtWidgets.QFileDialog \
                .getOpenFileName(
                    self, 'Choose registration file ', os.path.expanduser('~'),
                    "Text Files (*.reg *.txt *.json)")[0]

            if file is None or file is '':
                return
        try:
            with open(file) as json_data:
                regdict = json.load(json_data)
            refs = sorted(list(set([t['reference'] for t in regdict['tforms']])))
            # mov = set([t['moving'] for t in regdict['tforms']])
            modes = ['None']
            modes.extend(sorted(list(set(
                [t['mode'].title().replace('Cpd', 'CPD') for t in regdict['tforms']]
            ))))
            self.RegCalib_channelRefCombo.clear()
            self.RegCalib_channelRefCombo.addItems([str(r) for r in refs])
            self.RegCalib_channelRefModeCombo.clear()
            self.RegCalib_channelRefModeCombo.addItems(modes)
            self.RegFilePath.setText(file)
        except json.decoder.JSONDecodeError as e:
            raise err.RegistrationError("Failed to parse registration file", str(e))
        except Exception as e:
            raise err.RegistrationError("Failed to load registration file", str(e))

    def previewRegistration(self):
        RD = llsdir.RegDir(self.RegCalibPathLineEdit.text())
        if not RD.isValid:
            raise err.RegistrationError(
                'Registration Calibration dir not valid. Please check Fiducial Data path above.')

        if not self.RegFilePath.text():
            QtWidgets.QMessageBox.warning(self, "Must load registration file!",
                                          "No registration file!\n\nPlease click load, "
                                          "and load a registration file.  Or use the "
                                          "generate button to generate and load a new one.",
                                          QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton)
            return

        @QtCore.pyqtSlot(np.ndarray, float, float, dict)
        def displayRegPreview(array, dx=None, dz=None, params=None):
            win = ImgDialog(array, info=params,
                            title="Registration Mode: {} -- RefWave: {}".format(
                                opts['regMode'], opts['regRefWave']))
            win.overlayButton.click()
            win.maxProjButton.click()
            self.spimwins.append(win)

        self.previewButton.setDisabled(True)
        self.previewButton.setText('Working...')

        try:
            opts = self.getValidatedOptions()
        except Exception:
            self.previewButton.setEnabled(True)
            self.previewButton.setText('Preview')
            raise

        opts['regMode'] = self.RegCalib_channelRefModeCombo.currentText()
        if opts['regMode'].lower() == 'none':
            opts['doReg'] = False
        else:
            opts['doReg'] = True
        opts['regRefWave'] = int(self.RegCalib_channelRefCombo.currentText())
        opts['regCalibPath'] = self.RegFilePath.text()
        opts['correctFlash'] = False
        opts['medianFilter'] = False
        opts['trimZ'] = (0, 0)
        opts['trimY'] = (0, 0)
        opts['trimX'] = (0, 0)
        opts['nIters'] = 0

        w, thread = newWorkerThread(workers.TimePointWorker,
                                    RD, [0], None, opts,
                                    workerConnect={'previewReady': displayRegPreview},
                                    start=True)

        w.finished.connect(lambda: self.previewButton.setEnabled(True))
        w.finished.connect(lambda: self.previewButton.setText('Preview'))
        self.previewthreads = (w, thread)
