
import llspy
import llspy.gui.exceptions as err
import numpy as np
import os
import sys
import tarfile
import shutil
import json


from PyQt5 import QtCore
from llspy.gui.helpers import newWorkerThread, byteArrayToString, shortname
import logging
logger = logging.getLogger(__name__)  # set root logger


try:
    _CUDABIN = llspy.cudabinwrapper.get_bundled_binary()
except llspy.cudabinwrapper.CUDAbinException:
    _CUDABIN = None


class SubprocessWorker(QtCore.QObject):
    """This worker class encapsulates a QProcess (subprocess) for a given binary.

    It is intended to be subclassed, with new signals added as necessary and
    methods overwritten.  The work() method is where the subprocess gets started.
    procReadyRead, and procErrorRead define what to do with the stdout and stderr
    outputs.
    """

    processStarted = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()

    def __init__(self, binary, args, env=None, wid=1, **kwargs):
        super(SubprocessWorker, self).__init__()
        self.id = int(wid)
        self.binary = llspy.util.which(binary)
        if not binary:
            raise err.MissingBinaryError('Binary not found or not executable: {}'.format(self.binary))
        self.args = args
        self.env = env
        self.polling_interval = 100
        self.name = 'Subprocess'
        self.__abort = False
        self._logger = logging.getLogger('llspy.worker.'+type(self).__name__)

        self.process = QtCore.QProcess(self)
        self.process.readyReadStandardOutput.connect(self.procReadyRead)
        self.process.readyReadStandardError.connect(self.procErrorRead)

    @QtCore.pyqtSlot()
    def work(self):
        """
        this worker method does work that takes a long time. During this time,
        the thread's event loop is blocked, except if the application's
        processEvents() is called: this gives every thread (incl. main) a
        chance to process events, which means processing signals received
        from GUI (such as abort).
        """
        logger.debug('Subprocess {} START'.format(self.name))
        self._logger.info('~' * 20 + '\nRunning {} thread_{} with args: '
            '\n{}\n'.format(self.binary, self.id, " ".join(self.args)) + '\n')
        self.process.finished.connect(self.onFinished)
        self.process.finished.connect(lambda:
            logger.debug('Subprocess {} FINISH'.format(self.name)))
        # set environmental variables (for instance, to chose GPU)
        if self.env is not None:
            sysenv = QtCore.QProcessEnvironment.systemEnvironment()
            for k, v in self.env.items():
                sysenv.insert(k, str(v))
                logger.debug('Setting Environment Variable: {} = {}'.format(k, v))
            self.process.setProcessEnvironment(sysenv)
        self.process.start(self.binary, self.args)
        self.processStarted.emit()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.check_events)
        self.timer.start(self.polling_interval)

    def check_events(self):
        QtCore.QCoreApplication.instance().processEvents()
        if self.__abort:
            # self.process.terminate() # didn't work on Windows
            self.process.kill()
            # note that "step" value will not necessarily be same for every thread
            self._logger.info('aborting {} #{}'.format(self.name, self.id))

            self.process.waitForFinished()

    @QtCore.pyqtSlot()
    def procReadyRead(self):
        line = byteArrayToString(self.process.readAllStandardOutput())
        if line is not '':
            self._logger.update(line.rstrip())

    @QtCore.pyqtSlot()
    def procErrorRead(self):
        self._logger.error("Error in subprocess: {}".format(self.name))
        line = byteArrayToString(self.process.readAllStandardError())
        if line is not '':
            self._logger.info(line.rstrip())

    @QtCore.pyqtSlot(int, QtCore.QProcess.ExitStatus)
    def onFinished(self, exitCode, exitStatus):
        statusmsg = {0: 'exited normally', 1: 'crashed'}
        self._logger.info('{} #{} {} with exit code: {}'.format(
            self.name, self.id, statusmsg[exitStatus], exitCode))
        self.finished.emit()

    @QtCore.pyqtSlot()
    def abort(self):
        self._logger.info('{} #{} notified to abort'.format(self.name, self.id))
        self.__abort = True


class CudaDeconvWorker(SubprocessWorker):
    file_finished = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(int)  # worker id

    def __init__(self, args, env=None, **kwargs):
        binaryPath = _CUDABIN
        super(CudaDeconvWorker, self).__init__(binaryPath, args, env, **kwargs)
        self.name = 'CudaDeconv'

    def procReadyRead(self):
        while self.process.canReadLine():
            line = self.process.readLine()
            line = byteArrayToString(line)
            if "*** Finished!" in line or "Output:" in line:
                self.file_finished.emit()
            elif  "Iteration" in line:
                self._logger.info("CUDAworker {}: ".format(self.id) + line.rstrip())
            else:
                self._logger.info(line.rstrip())

    @QtCore.pyqtSlot(int, QtCore.QProcess.ExitStatus)
    def onFinished(self, exitCode, exitStatus):
        statusmsg = {0: 'exited normally', 1: 'crashed'}
        self._logger.info('{} #{} {} with exit code: {}'.format(
            self.name, self.id, statusmsg[exitStatus], exitCode))
        self.finished.emit(self.id)


class CompressionWorker(SubprocessWorker):

    status_update = QtCore.pyqtSignal(str, int)

    def __init__(self, path, mode='compress', binary=None, wid=1, **kwargs):
        if binary is None:
            if sys.platform.startswith('win32'):
                binary = 'pigz'
            else:
                binary = 'lbzip2'
        binary = llspy.util.which(binary)
        if not binary:
            raise err.MissingBinaryError("No binary found for compression program: {}".format(binary))
        super(CompressionWorker, self).__init__(binary, [], wid, **kwargs)
        self.path = path
        self.mode = mode
        self.name = 'CompressionWorker'

    @QtCore.pyqtSlot()
    def work(self):
        if self.mode == 'decompress':
            self.status_update.emit(
                'Decompressing {}...'.format(shortname(self.path)), 0)
            tar_compressed = llspy.util.find_filepattern(self.path, '*.tar*')
            tar_extension = os.path.splitext(tar_compressed)[1]
            if tar_extension not in llspy.compress.EXTENTIONS:
                self._logger.error('Unexpected uncompressed tar file found')
                raise err.LLSpyError('found a tar file, but don\'t know how to decompress')
            if self.binary not in llspy.compress.EXTENTIONS[tar_extension]:
                    for compbin in llspy.compress.EXTENTIONS[tar_extension]:
                        if llspy.util.which(compbin):
                            self.binary = llspy.util.which(compbin)
                            break
            if not self.binary:
                raise err.MissingBinaryError(
                    "No binary found for compression program: {}".format(
                        llspy.compress.EXTENTIONS[tar_extension]))
            self.args = ['-dv', tar_compressed]
            self.process.finished.connect(
                lambda: self.untar(os.path.splitext(tar_compressed)[0]))

        elif self.mode == 'compress':
            if llspy.util.find_filepattern(self.path, '*.tar*'):
                raise err.LLSpyError('There are both raw tiffs and a compressed file in '
                    'directory: {}'.format(self.path),
                    'If you would like to compress this directory, '
                    'please either remove any existing *.tar files, or remove '
                    'the uncompressed tiff files.  Alternatively, you can use '
                    'the Decompress Raw function to decompress the *.tar file. '
                    'This will overwrite any raw tiffs with matching names')
            self.status_update.emit(
                'Compressing {}...'.format(shortname(self.path)), 0)
            tarball = llspy.compress.tartiffs(self.path)
            self.args = ['-v', tarball]
            self.process.finished.connect(self.finished.emit)

        msg = '\nRunning {} thread_{} with args:\n{}\n'.format(
            self.name, self.id, self.binary + " " + " ".join(self.args))
        self._logger.info('~' * 20 + msg)

        self.process.start(self.binary, self.args)
        self.processStarted.emit()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.check_events)
        self.timer.start(self.polling_interval)

    def untar(self, tarball, delete=True):
        if not os.path.isfile(tarball):
            self.finished.emit()
            return
        try:
            with tarfile.open(tarball) as tar:
                tar.extractall(path=os.path.dirname(tarball))
        except Exception:
            raise
        if delete:
            os.remove(tarball)
        self.finished.emit()

    @QtCore.pyqtSlot()
    def procErrorRead(self):
        # for some reason, lbzip2 puts its verbose output in stderr
        line = byteArrayToString(self.process.readAllStandardError())
        if line is not '':
            if '%' in line:
                self.result_string = line
            self._logger.info(line.rstrip())


# class CorrectionWorker(QtCore.QObject):
#     """docstring for ImCorrector"""

#     finished = QtCore.pyqtSignal()
#     error = QtCore.pyqtSignal()

#     def __init__(self, path, tRange, camparams, median, target):
#         super(CorrectionWorker, self).__init__()
#         self.path = path
#         self.tRange = tRange
#         self.camparams = camparams
#         self.median = median
#         self.target = target
#         self.E = llspy.LLSdir(self.path)

#     @QtCore.pyqtSlot()
#     def work(self):
#         try:
#             self.E.correct_flash(trange=self.tRange, camparamsPath=self.camparams,
#                                  median=self.median, target=self.target)
#         except Exception:
#             self.error.emit()
#             raise

#         self.finished.emit()


def divide_arg_queue(E, n_gpus, binary):
    """generate all the channel specific cudaDeconv arguments for this item."""
    argQueue = []

    def split(a, n):
        k, m = divmod(len(a), n)
        return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))

    P = E.localParams()
    cudaOpts = P.copy()
    n_time = len(P.tRange)

    for i, chan in enumerate(P.cRange):
        # generate channel and gpu specific options
        cudaOpts['input-dir'] = str(E.path)
        cudaOpts['otf-file'] = P.otfs[i]
        cudaOpts['background'] = P.background[i] if not P.correctFlash else 0
        cudaOpts['wavelength'] = float(E.parameters.channels[chan]) / 1000

        # if the number of GPUs is less than or equal to
        # the number of timepoints being processed
        # then split the work across GPUs by processing each channel,
        # diving time across the available GPUS
        if n_gpus <= n_time:
            tRanges = list(split(P.tRange, n_gpus))

            for tRange in tRanges:
                # filter by channel and trange
                if len(tRange) == E.parameters.nt:
                    cudaOpts['filename-pattern'] = '_ch{}_'.format(chan)
                else:
                    cudaOpts['filename-pattern'] = '_ch{}_stack{}'.format(chan,
                        llspy.util.pyrange_to_perlregex(tRange))

                argQueue.append(binary.assemble_args(**cudaOpts))

        # if there are more GPUs than timepoints available
        # (e.g. single stack of multiple channels)
        # then if there are enough gpus to cover all channels,
        # divide channels across gpus
        else:
            cudaOpts['filename-pattern'] = '_ch{}_'.format(chan)
            argQueue.append(binary.assemble_args(**cudaOpts))

    return argQueue


class LLSitemWorker(QtCore.QObject):

    sig_starting_item = QtCore.pyqtSignal(str, int)  # item path, numfiles

    status_update = QtCore.pyqtSignal(str)  # update mainGUI status
    progressUp = QtCore.pyqtSignal()  # set progressbar value
    progressValue = QtCore.pyqtSignal(int)  # set progressbar value
    progressMaxVal = QtCore.pyqtSignal(int)  # set progressbar maximum
    clockUpdate = QtCore.pyqtSignal(str)  # set progressbar value
    file_finished = QtCore.pyqtSignal()  # worker id, filename

    finished = QtCore.pyqtSignal()
    sig_abort = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal()
    skipped = QtCore.pyqtSignal(str)

    def __init__(self, lls_dir, wid, opts, **kwargs):
        super(LLSitemWorker, self).__init__()

        if isinstance(lls_dir, llspy.LLSdir):
            self.E = lls_dir
            self.path = str(self.E.path)
        else:
            self.path = str(lls_dir)
            self.E = llspy.LLSdir(self.path)

        self.__id = int(wid)
        self.opts = opts
        self.shortname = shortname(self.path)
        self.aborted = False
        self.__argQueue = []  # holds all argument lists that will be sent to threads
        self.GPU_SET = QtCore.QCoreApplication.instance().gpuset
        self.__CUDAthreads = {gpu: None for gpu in self.GPU_SET}
        if not len(self.GPU_SET):
            self.error.emit()
            raise err.InvalidSettingsError("No GPUs selected. Check Config Tab")

        self._logger = logging.getLogger('llspy.worker.'+type(self).__name__)

    @QtCore.pyqtSlot()
    def work(self):
        if self.E.is_compressed():
            self.status_update.emit('Decompressing {}'.format(self.E.basename))
            self.E.decompress()

        if not self.E.ready_to_process:
            if not self.E.has_lls_tiffs:
                self._logger.warning(
                    'No TIFF files to process in {}'.format(self.path))
            if not self.E.parameters.isReady():
                self._logger.warning(
                    'Incomplete parameters for: {}'.format(self.path))
                self.skipped.emit(self.path)
            return

        # this needs to go here instead of __init__ in case folder is compressed
        try:
            self.P = self.E.localParams(**self.opts)
        except Exception:
            self.error.emit()
            self.finished.emit()
            raise

        # we process one folder at a time. Progress bar updates per Z stack
        # so the maximum is the total number of timepoints * channels
        self.nFiles = len(self.P.tRange) * len(self.P.cRange)

        self._logger.info('#' * 50)
        self._logger.info('Processing {}'.format(self.E.basename))
        self._logger.info('#' * 50 + '\n')
        self._logger.debug('Full path {}'.format(self.path))
        self._logger.debug('Parameters {}\n'.format(self.E.parameters))

        if self.P.correctFlash:
            try:
                self.status_update.emit('Correcting Flash artifact on {}'.format(self.E.basename))
                self.E.path = self.E.correct_flash(**self.P)
            except llspy.llsdir.LLSpyError:
                self.error.emit()
                raise
        # if not flash correcting but there is trimming/median filter requested
        elif (self.P.medianFilter or
              any([any(i) for i in (self.P.trimX, self.P.trimY, self.P.trimZ)])):
            self.E.path = self.E.median_and_trim(**self.P)

        self.nFiles_done = 0
        self.progressValue.emit(0)
        self.progressMaxVal.emit(self.nFiles)

        self.status_update.emit(
            'Processing {}: (0 of {})'.format(self.E.basename, self.nFiles))

        # only call cudaDeconv if we need to deskew or deconvolve
        if self.P.nIters > 0 or (self.P.deskew > 0 and self.P.saveDeskewedRaw):

            try:
                # check the binary path and create object
                binary = llspy.cudabinwrapper.CUDAbin(_CUDABIN)
            except Exception:
                self.error.emit()
                raise

            self.__argQueue = divide_arg_queue(self.E, len(self.GPU_SET), binary)

            # with the argQueue populated, we can now start the workers
            if not len(self.__argQueue):
                self._logger.error('No channel arguments to process in LLSitem: %s' % self.shortname)
                self._logger.debug('LLSitemWorker FINISH: {}'.format(self.E.basename))
                self.finished.emit()
                return

            self.startCUDAWorkers()
        else:
            self.post_process()

        self.timer = QtCore.QTime()
        self.timer.restart()

    def startCUDAWorkers(self):
        # initialize the workers and threads

        for gpu in self.GPU_SET:
            # create new CUDAworker for every thread
            # each CUDAworker will control one cudaDeconv process (which only gets
            # one wavelength at a time)

            # grab the next arguments from the queue
            # THIS BREAKS the relationship between num_cuda_threads
            # and self.__CUDAworkers_done...
            # if len(self.__argQueue)== 0:
            #   return
            if not len(self.__argQueue):
                return
            args = self.__argQueue.pop(0)

            CUDAworker, thread = newWorkerThread(CudaDeconvWorker, args,
                {"CUDA_VISIBLE_DEVICES": gpu},
                wid=gpu,
                workerConnect={
                     # get progress messages from CUDAworker and pass to parent
                     'file_finished': self.on_file_finished,
                     'finished': self.on_CUDAworker_done,
                     # any messages go straight to the log window
                     # 'error': self.errorstring  # implement error signal?
                })

            # need to store worker too otherwise will be garbage collected
            self.__CUDAthreads[gpu] = (thread, CUDAworker)

            # connect mainGUI abort CUDAworker signal to the new CUDAworker
            self.sig_abort.connect(CUDAworker.abort)

            # start the thread
            thread.start()

    @QtCore.pyqtSlot()
    def on_file_finished(self):
        # update status bar
        self.nFiles_done = self.nFiles_done + 1
        self.status_update.emit('Processing {}: ({} of {})'.format(
            self.shortname, self.nFiles_done, self.nFiles))
        # update progress bar
        self.progressUp.emit()
        # update the countdown timer with estimate of remaining time
        avgTimePerFile = int(self.timer.elapsed() / self.nFiles_done)
        filesToGo = self.nFiles - self.nFiles_done + 1
        remainingTime = filesToGo * avgTimePerFile
        timeAsString = QtCore.QTime(0, 0).addMSecs(remainingTime).toString()
        self.clockUpdate.emit(timeAsString)

    @QtCore.pyqtSlot(int)
    def on_CUDAworker_done(self, worker_id):
        # a CUDAworker has finished... update the log and check if any are still going
        logger.debug("CudaDeconv Worker on GPU {} finished".format(worker_id))
        thread, _ = self.__CUDAthreads[worker_id]
        thread.quit()
        thread.wait()
        self.__CUDAthreads[worker_id] = None

        # FIXME:  this forces all GPUs to be done before ANY can continue
        # ... only as fast as the slowest GPU
        # could probably fix easily by delivering a value to startCudaWorkers
        # instead of looping through gpu inside of it
        if not any([v for v in self.__CUDAthreads.values()]):
            # if there's still stuff left in the argQueue for this item, keep going
            if self.aborted:
                self.aborted = False
                self.finished.emit()
            elif len(self.__argQueue):
                self.startCUDAWorkers()
            # otherwise send the signal that this item is done
            else:
                self.post_process()

    def post_process(self):

        if self.P.doReg:
            self.status_update.emit(
                'Doing Channel Registration: {}'.format(self.E.basename))
            try:
                self.E.register(self.P.regRefWave, self.P.regMode,
                    self.P.regCalibPath, discard=self.P.deleteUnregistered)
            except Exception:
                self._logger.error("REGISTRATION FAILED")
                raise

        if self.P.mergeMIPs:
            self.status_update.emit(
                'Merging MIPs: {}'.format(self.E.basename))
            self.E.mergemips()
        else:
            for mipfile in self.E.path.glob('**/*comboMIP_*'):
                mipfile.unlink()  # clean up any combo MIPs from previous runs

        # if self.P.mergeMIPsraw:
        #   if self.E.path.joinpath('Deskewed').is_dir():
        #       self.status_update.emit(
        #           'Merging raw MIPs: {}'.format(self.E.basename))
        #       self.E.mergemips('Deskewed')

        # if we did camera correction, move the resulting processed folders to
        # the parent folder, and optionally delete the corrected folder
        if self.P.moveCorrected and self.E.path.name == 'Corrected':
            llspy.llsdir.move_corrected(str(self.E.path))
            self.E.path = self.E.path.parent

        if not self.P.keepCorrected:
            shutil.rmtree(str(self.E.path.joinpath('Corrected')), ignore_errors=True)

        if self.P.compressRaw:
            self.status_update.emit(
                'Compressing Raw: {}'.format(self.E.basename))
            self.E.compress()

        if self.P.writeLog:
            outname = str(self.E.path.joinpath('{}_{}'.format(self.E.basename,
                                llspy.config.__OUTPUTLOG__)))
            try:
                with open(outname, 'w') as outfile:
                    json.dump(self.P, outfile, cls=llspy.util.paramEncoder)
            except FileNotFoundError:
                self._logger.error('Could not write processing log file.')

        self.finished.emit()

    @QtCore.pyqtSlot()
    def abort(self):
        self._logger.info('LLSworker #{} notified to abort'.format(self.__id))
        if any([v for v in self.__CUDAthreads.values()]):
            self.aborted = True
            self.__argQueue = []
            self.sig_abort.emit()
        # self.processButton.setDisabled(True) # will be reenabled when workers done
        else:
            self.finished.emit()


class TimePointWorker(QtCore.QObject):
    """docstring for TimePointWorker"""

    finished = QtCore.pyqtSignal()
    previewReady = QtCore.pyqtSignal(np.ndarray, float, float, dict)
    updateCrop = QtCore.pyqtSignal(int, int)

    def __init__(self, lls_dir, tRange, cRange, opts, ditch_partial=True, **kwargs):
        super(TimePointWorker, self).__init__()

        if isinstance(lls_dir, llspy.LLSdir):
            self.E = lls_dir
            self.path = str(self.E.path)
        else:
            # assume it's a string
            self.path = str(lls_dir)
            self.E = llspy.LLSdir(self.path, ditch_partial)

        self.tRange = tRange
        self.cRange = cRange
        self.opts = opts
        self._logger = logging.getLogger('llspy.worker.'+type(self).__name__)

    @QtCore.pyqtSlot()
    def work(self):
        if not self.E.parameters.isReady():
            self.finished.emit()
            raise err.InvalidSettingsError("Parameters are incomplete for this item. "
                "Please add any missing/higlighted parameters.")

        try:
            previewStack = self.E.preview(self.tRange, self.cRange, **self.opts)
            if previewStack is not None:
                self.previewReady.emit(previewStack, self.E.parameters.dx, self.E.parameters.dzFinal, self.E._localParams)

                # TODO: this needs to be a signal, but shold only be emitted when the caller
                # was the preview button (not a watcher)
                if self.opts['cropMode'] == 'auto':
                    wd = self.E.get_feature_width(pad=self.opts['cropPad'], t=np.min(self.tRange))
                    self.updateCrop.emit(wd['width'], wd['offset'])
            else:
                raise err.InvalidSettingsError("No stacks to preview... check tRange")

        except Exception:
            self.finished.emit()
            raise

        self.finished.emit()
