# -*- coding: utf-8 -*-
from __future__ import print_function, division

import os
import os.path as osp
import shutil
import glob
import logging
import inspect
import sys
import time
import numpy as np
import traceback
import re

thisDirectory = osp.dirname(osp.abspath(__file__))
sys.path.append(osp.dirname(osp.dirname(thisDirectory)))
import llspy
import imdisplay

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyQt5 import QtCore, QtGui, uic
from PyQt5 import QtWidgets as QtW
# import sys
# sys.path.append(osp.join(osp.dirname(osp.abspath(__file__)),'..'))

thisDirectory = osp.dirname(osp.abspath(__file__))
form_class = uic.loadUiType(osp.join(thisDirectory, 'main_gui.ui'))[0]
# form_class = uic.loadUiType('./llspy/gui/main_gui.ui')[0]  # for debugging

# platform independent settings file
QtCore.QCoreApplication.setOrganizationName("LLSpy")
QtCore.QCoreApplication.setOrganizationDomain("llspy.com")
GUIsettings = QtCore.QSettings("LLSpy", "LLSpyGUI")
defaultSettings = QtCore.QSettings("LLSpy", 'LLSpyDefaults')


# def trap_exc_during_debug(errorType, errValue, tback):
# 	import traceback
# 	# when app raises uncaught exception, print info
# 	# traceback.print_exc()
# 	if errorType.__module__ == 'voluptuous.error':
# 		handleSchemaError(errValue, tback)
# 		return
# 	print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
# 	print(traceback.print_tb(tback) + "\n")
# 	print(errValue)
# 	print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")


# def handleSchemaError(errMsg, tback):
# 	import traceback
# 	import re
# 	print("SCHEMA ERROR")
# 	schemaDefaults = llspy.schema.__defaults__
# 	schemaerrRX = re.compile(r'.*data\[(?P<dictItem>.+)\]. Got (?P<gotValue>.+)')
# 	gd = schemaerrRX.search(str(errMsg)).groupdict()
# 	item = gd['dictItem']
# 	value = gd['gotValue']
# 	msg = QtW.QMessageBox(app)
# 	msg.setIcon(QtW.QMessageBox.Warning)
# 	msg.setText("Validation Error")
# 	msg.setInformativeText(
# 		"Not a valid entry for {}.\nGot: {}\n\nDescription: {}\nDefault: {}".format(
# 			item, value, schemaDefaults[item.strip("'")][1], schemaDefaults[item.strip("'")][0]))
# 	msg.setWindowTitle("Schema Error Window")
# 	msg.setDetailedText("".join(traceback.format_tb(tback)))
# 	msg.exec_()


# # install exception hook: without this, uncaught exception would cause application to exit
# sys.excepthook = trap_exc_during_debug


class ExceptionHandler(QtCore.QObject):

	errorSignal = QtCore.pyqtSignal()
	silentSignal = QtCore.pyqtSignal()
	schemaError = QtCore.pyqtSignal(str, str)

	def __init__(self):
		super(ExceptionHandler, self).__init__()

	def handler(self, errorType, errValue, tback):
		self.errorSignal.emit()
		self.trap_exc_during_debug(errorType, errValue, tback)

	def trap_exc_during_debug(self, errorType, errValue, tback):
		# when app raises uncaught exception, print info
		# traceback.print_exc()
		if errorType.__module__ == 'voluptuous.error':
			self.schemaError.emit(str(errValue), "".join(traceback.format_tb(tback)))
			return
		print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
		print(traceback.print_tb(tback) + "\n")
		print(errValue)
		print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")


def byteArrayToString(bytearr):
	if sys.version_info.major < 3:
		return str(bytearr)
	else:
		return str(bytearr, encoding='utf-8')


def pathHasPattern(path, pattern='*Settings.txt'):
	return bool(len(glob.glob(osp.join(path, pattern))))


# FIXME: temporary
def channel_args(E, P, chan, binary=None):
	opts = {
		'background': P.background[chan] if not P.bFlashCorrect else 0,
		'drdata': P.drdata,
		'dzdata': P.dzdata,
		'wavelength': float(P.wavelength[chan])/1000,
		'deskew': P.deskew,
		'saveDeskewedRaw': P.bSaveDeskewedRaw,
		'MIP': P.MIP,
		'rMIP': P.MIPraw,
		'uint16': P.buint16,
		'bleachCorrection': P.bBleachCor,
		'RL': P.nIters,
		'rotate': P.rotate,
		'width': P.width,
		'shift': P.shift,
		# 'quiet': bool(quiet),
		# 'verbose': bool(verbose),
	}

	# filter by channel and trange
	if len(list(P.tRange)) == E.parameters.nt:
		filepattern = 'ch{}_'.format(chan)
	else:
		filepattern = 'ch{}_stack{}'.format(chan,
			llspy.util.pyrange_to_perlregex(P.tRange))
	args = llspy.cudabinwrapper.assemble_args(binary,
		str(E.path), filepattern, P.otfs[chan], **opts)
	return args


def string_to_iterable(string):
	"""convert a string into an iterable
	note: ranges are inclusive

	>>> string_to_iterable('0,3,5-10,15-30-3,40')
	[0,3,5,6,7,8,9,10,15,18,21,24,27,30,40]
	"""
	import re
	if re.search('[^\d^,^-]', string) is not None:
		raise ValueError('Iterable string must contain only digits, commas, and dashes')
	it = []
	splits = [tuple(s.split('-')) for s in string.split(',')]
	for item in splits:
		if len(item) == 1:
			it.append(int(item[0]))
		elif len(item) == 2:
			it.extend(list(range(int(item[0]), int(item[1])+1)))
		elif len(item) == 3:
			it.extend(list(range(int(item[0]), int(item[1])+1, int(item[2]))))
		else:
			raise ValueError("Iterable string items must be of length <= 3")
	return sorted(list(set(it)))


def guisave(widget, settings):
	print("Saving settings: {}".format(settings.fileName()))
	# Save geometry
	selfName = widget.objectName()
	settings.setValue(selfName + '_size', widget.size())
	settings.setValue(selfName + '_pos', widget.pos())
	for name, obj in inspect.getmembers(widget):
		# if type(obj) is QComboBox:  # this works similar to isinstance, but missed some field... not sure why?
		value = None
		if isinstance(obj, QtW.QComboBox):
			index = obj.currentIndex()  # get current index from combobox
			value = obj.itemText(index)  # get the text for current index
		if isinstance(obj, QtW.QLineEdit):
			value = obj.text()
		if isinstance(obj,
			(QtW.QCheckBox, QtW.QRadioButton, QtW.QGroupBox)):
			value = obj.isChecked()
		if isinstance(obj, (QtW.QSpinBox, QtW.QSlider)):
			value = obj.value()
		if value is not None:
			settings.setValue(name, value)
	settings.sync()  # required in some cases to write settings before quit


def guirestore(widget, settings):
	print("Restoring settings: {}".format(settings.fileName()))
	# Restore geometry
	selfName = widget.objectName()
	if 'LLSpyDefaults' not in settings.fileName():
		widget.resize(settings.value(selfName + '_size', QtCore.QSize(500, 500)))
		widget.move(settings.value(selfName + '_pos', QtCore.QPoint(60, 60)))
	for name, obj in inspect.getmembers(widget):
		try:
			if isinstance(obj, QtW.QComboBox):
				value = (settings.value(name))
				if value == "":
					continue
				index = obj.findText(value)  # get the corresponding index for specified string in combobox
				if index == -1:  # add to list if not found
					obj.insertItems(0, [value])
					index = obj.findText(value)
					obj.setCurrentIndex(index)
				else:
					obj.setCurrentIndex(index)  # preselect a combobox value by index
			if isinstance(obj, QtW.QLineEdit):
				value = settings.value(name, type=str)  # get stored value from registry
				obj.setText(value)  # restore lineEditFile
			if isinstance(obj,
				(QtW.QCheckBox, QtW.QRadioButton, QtW.QGroupBox)):
				value = settings.value(name, type=bool)  # get stored value from registry
				if value is not None:
					obj.setChecked(value)  # restore checkbox
			if isinstance(obj, (QtW.QSlider, QtW.QSpinBox)):
				value = settings.value(name, type=int)    # get stored value from registry
				if value is not None:
					obj.setValue(value)   # restore value from registry
			if isinstance(obj, (QtW.QDoubleSpinBox,)):
				value = settings.value(name, type=float)    # get stored value from registry
				if value is not None:
					obj.setValue(value)   # restore value from registry
		except Exception:
			logging.warn('Unable to restore settings for object: {}'.format(name))


class QPlainTextEditLogger(logging.Handler):
	def __init__(self, parent=None):
		super(QPlainTextEditLogger, self).__init__()
		self.widget = QtW.QPlainTextEdit(parent)
		self.widget.setReadOnly(True)

	def emit(self, record):
		msg = self.format(record)
		self.widget.appendPlainText(msg)


class LogWindow(QtW.QDialog, QPlainTextEditLogger):
	def __init__(self, parent=None):
		super(LogWindow, self).__init__(parent)
		self.setMinimumSize(800, 300)
		self.move(0, 0)

		logTextBox = QPlainTextEditLogger(self)
		# You can format what is printed to text box
		logTextBox.setFormatter(logging.Formatter(
			'%(asctime)s - %(levelname)s - %(message)s',
			datefmt="%H:%M:%S"))
		logging.getLogger().addHandler(logTextBox)
		# You can control the logging level
		logging.getLogger().setLevel(logging.DEBUG)

		self._button = QtW.QPushButton(self)
		self._button.setText('Test Me')

		layout = QtW.QVBoxLayout()
		# Add the new logging box widget to the layout
		layout.addWidget(logTextBox.widget)
		layout.addWidget(self._button)
		self.setLayout(layout)

		# Connect signal to slot
		self._button.clicked.connect(self.test)

	def test(self):
		logging.debug('damn, a bug')
		logging.info('something to remember')
		logging.warning('that\'s not right')
		logging.error('foobar')


class LLSDragDropTable(QtW.QTableWidget):

	colHeaders = ['path', 'name', 'nC', 'nT', 'nZ', 'nY', 'nX', 'desQ']
	nCOLS = len(colHeaders)

	# A signal needs to be defined on class level:
	dropSignal = QtCore.pyqtSignal(list, name="dropped")
	# This signal emits when a URL is dropped onto this list,
	# and triggers handler defined in parent widget.

	def __init__(self, parent=None):
		super(LLSDragDropTable, self).__init__(0, self.nCOLS, parent)
		self.setAcceptDrops(True)
		self.setSelectionMode(QtW.QAbstractItemView.ExtendedSelection)
		self.setSelectionBehavior(QtW.QAbstractItemView.SelectRows)
		self.setGridStyle(3)  # dotted grid line

		self.setHorizontalHeaderLabels(self.colHeaders)
		self.hideColumn(0)  # column 0 is a hidden col for the full pathname
		header = self.horizontalHeader()
		header.setSectionResizeMode(1, QtW.QHeaderView.Stretch)
		header.resizeSection(2, 30)
		header.resizeSection(3, 50)
		header.resizeSection(4, 50)
		header.resizeSection(5, 50)
		header.resizeSection(6, 50)
		header.resizeSection(7, 40)

	@QtCore.pyqtSlot(str)
	def addPath(self, path):
		if not (osp.exists(path) and osp.isdir(path)):
			return
		# If this folder is not on the list yet, add it to the list:
		if not pathHasPattern(path, '*Settings.txt'):
			logging.warn('No Settings.txt! Ignoring: {}'.format(path))
			return
		# if it's already on the list, don't add it
		if len(self.findItems(path, QtCore.Qt.MatchExactly)):
			return

		E = llspy.LLSdir(path)
		shortname = osp.sep.join(E.path.parts[-2:])
		logging.info('Add: {}'.format(shortname))
		rowPosition = self.rowCount()
		self.insertRow(rowPosition)
		item = [path,
				shortname,
				str(E.parameters.nc),
				str(E.parameters.nt),
				str(E.parameters.nz),
				str(E.parameters.ny),
				str(E.parameters.nx),
				'✅' if E.parameters.samplescan else '-']
		for col, elem in enumerate(item):
			entry = QtW.QTableWidgetItem(elem)
			entry.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
			self.setItem(rowPosition, col, entry)

	def selectedPaths(self):
		selectedRows = self.selectionModel().selectedRows()
		return [self.item(i.row(), 0).text() for i in selectedRows]

	@QtCore.pyqtSlot(str)
	def removePath(self, path):
		items = self.findItems(path, QtCore.Qt.MatchExactly)
		for item in items:
			self.removeRow(item.row())

	def setRowBackgroudColor(self, row, color):
		grayBrush = QtGui.QBrush(QtGui.QColor(color))
		for col in range(self.nCOLS):
			self.item(row, col).setBackground(grayBrush)

	def dragEnterEvent(self, event):
		if event.mimeData().hasUrls:
			event.accept()
		else:
			event.ignore()

	def dragMoveEvent(self, event):
		if event.mimeData().hasUrls:
			event.setDropAction(QtCore.Qt.CopyAction)
			event.accept()
		else:
			event.ignore()

	def dropEvent(self, event):
		if event.mimeData().hasUrls:
			event.setDropAction(QtCore.Qt.CopyAction)
			event.accept()
			# links = []
			for url in event.mimeData().urls():
				# links.append(str(url.toLocalFile()))
				self.addPath(str(url.toLocalFile()))
			# self.dropSignal.emit(links)
			# for url in links:
			# 	self.listbox.addPath(url)
		else:
			event.ignore()

	def keyPressEvent(self, event):
		super(LLSDragDropTable, self).keyPressEvent(event)
		if (event.key() == QtCore.Qt.Key_Delete or
			event.key() == QtCore.Qt.Key_Backspace):
			indices = self.selectionModel().selectedRows()
			i = 0
			for index in sorted(indices):
				self.removeRow(index.row()-i)
				i += 1


# ################# WORKERS ################

# TODO: add timer?
def newWorkerThread(workerClass, *args, **kwargs):
	worker = workerClass(*args)
	thread = QtCore.QThread()
	worker.moveToThread(thread)
	# all workers started using this function must implement work() func
	thread.started.connect(worker.work)
	# all workers started using this function must emit finished signal
	worker.finished.connect(thread.quit)
	worker.finished.connect(worker.deleteLater)
	thread.finished.connect(thread.deleteLater)

	# connect dict from calling object to worker signals
	worker_connections = kwargs.get('workerConnect', None)
	if worker_connections:
		[getattr(worker, key).connect(val) for key, val in worker_connections.items()]
	# optionally, can supply onfinish callable when thread finishes
	if kwargs.get('onfinish', None):
		thread.finished.connect(kwargs.get('onfinish'))
	if kwargs.get('start', False) is True:
		thread.start()  # usually need to connect stuff before starting
	return worker, thread


class CudaDeconvWorker(QtCore.QObject):

	file_finished = QtCore.pyqtSignal(int, str)  # worker id, filename
	finished = QtCore.pyqtSignal(int)  # worker id: emitted at end of work()
	logUpdate = QtCore.pyqtSignal(str)  # message to be shown to user

	def __init__(self, id, args):
		super(CudaDeconvWorker, self).__init__()
		self.__id = int(id)
		self.__args = args
		self.__abort = False

		# QProcess object for external app
		self.process = QtCore.QProcess(self)
		self.binary = mainGUI.cudaDeconvPathLineEdit.text()
		# self.process.setProcessEnvironment(env)

		# QProcess emits `readyRead` when there is data to be read
		self.process.readyRead.connect(self.procOutputReady)
		self.process.readyReadStandardError.connect(self.handleError)

	@QtCore.pyqtSlot()
	def work(self):
		"""
		this worker method does work that takes a long time. During this time, the thread's
		event loop is blocked, except if the application's processEvents() is called: this gives every
		thread (incl. main) a chance to process events, which means processing signals
		received from GUI (such as abort).
		"""
		# thread_name = QtCore.QThread.currentThread().objectName()
		# thread_id = int(QtCore.QThread.currentThreadId())  # cast to int() is necessary

		# TODO: create err signal
		if self.__args[2] == '' or self.__args[2] is None:
			raise Exception('ALERT!!  NO OTF FILE ... WILL CAUSE CRASH')
			self.process.terminate()
			self.process.waitForFinished()
			self.finished.emit(self.__id)
			return

		self.logUpdate.emit('='*20 + '\nRunning cudaDeconv thread_{} with args: '
			'\n{}\n'.format(self.__id, " ".join(self.__args)) + '='*20)

		# DO WORK
		self.process.finished.connect(self.onFinished)
		self.process.start(self.binary, self.__args)

		while self.process.state() > 0:
			time.sleep(0.1)
			# check if we need to abort the loop; need to process events to receive signals;
			app.processEvents()  # this could cause change to self.__abort
			if self.__abort:
				self.process.terminate()
				# note that "step" value will not necessarily be same for every thread
				self.logUpdate.emit('aborting CUDAworker #{}'.format(self.__id))
				break
		self.process.waitForFinished()

	def procOutputReady(self):
		while self.process.canReadLine():
			line = self.process.readLine()
			line = byteArrayToString(line)
			if "Output:" in line:
				path = line.split("Output:")[1]
				base = osp.basename(path.strip())
				self.file_finished.emit(self.__id, base)
			else:
				self.logUpdate.emit(line.rstrip())

	def handleError(self):
		self.logUpdate.emit("!!!!!! cudaDeconv Error !!!!!!")
		self.process.setReadChannel(QtCore.QProcess.StandardError)
		while self.process.canReadLine():
			line = self.process.readLine()
			line = byteArrayToString(line)
			self.logUpdate.emit(line.rstrip())

	def onFinished(self, exitCode,  exitStatus):
		self.logUpdate.emit('cudaDeconv process #{} finished with code({}) and '
			'status: {}'.format(self.__id, exitCode,  exitStatus))
		self.finished.emit(self.__id)

	def abort(self):
		self.logUpdate.emit('CUDAWorker #{} notified to abort'.format(self.__id))
		self.__abort = True


class TimePointWorker(QtCore.QObject):
	"""docstring for TimePointWorker"""

	finished = QtCore.pyqtSignal()
	previewReady = QtCore.pyqtSignal(np.ndarray)

	def __init__(self, path, tRange, opts):
		super(TimePointWorker, self).__init__()
		self.path = path
		self.tRange = tRange
		self.opts = opts

	@QtCore.pyqtSlot()
	def work(self):
		E = llspy.LLSdir(self.path)
		previewStack = llspy.llsdir.preview(E, self.tRange, **self.opts)
		self.previewReady.emit(previewStack)
		self.finished.emit()


class LLSitemWorker(QtCore.QObject):
	NUM_CUDA_THREADS = 1
	sig_abort = QtCore.pyqtSignal()
	file_finished = QtCore.pyqtSignal(int, str)  # worker id, filename
	sig_starting_item = QtCore.pyqtSignal(str, int)  # item path, numfiles
	finished = QtCore.pyqtSignal()
	statusUpdate = QtCore.pyqtSignal(str)  # update mainGUI status
	logUpdate = QtCore.pyqtSignal(str)  # message to be shown to user
	progressUp = QtCore.pyqtSignal()  # set progressbar value
	progressValue = QtCore.pyqtSignal(int)  # set progressbar value
	progressMaxVal = QtCore.pyqtSignal(int)  # set progressbar maximum
	clockUpdate = QtCore.pyqtSignal(str)  # set progressbar value
	error = QtCore.pyqtSignal()

	def __init__(self, id, path, opts):
		super(LLSitemWorker, self).__init__()
		self.__id = int(id)
		self.opts = opts
		self.E = llspy.LLSdir(path)
		self.shortname = osp.sep.join(self.E.path.parts[-2:])
		self.aborted = False
		self.__argQueue = []  # holds all argument lists that will be sent to threads
		self.__CUDAthreads = []

	@QtCore.pyqtSlot()
	def work(self):
		if self.E.is_compressed():
			self.statusUpdate.emit('Decompressing {}'.format(self.E.basename))
			self.E.decompress()

		if not self.E.ready_to_process:
			if not self.E.has_lls_tiffs:
				self.logUpdate.emit(
					'No TIFF files to process in {}'.format(self.E.path))
			if not self.E.has_settings:
				self.logUpdate.emit(
					'Could not find Settings.txt file in {}'.format(self.E.path))
			return

		try:
			self.P = self.E.localParams(**self.opts)
		except Exception:
			(excepttype, value, traceback) = sys.exc_info()
			sys.excepthook(excepttype, value, traceback)
			self.error.emit()
			return

		# we process one folder at a time. Progress bar updates per Z stack
		# so the maximum is the total number of timepoints * channels
		self.nFiles = len(self.P.tRange) * len(self.P.cRange)

		self.logUpdate.emit('\n' + '#' * 50)
		self.logUpdate.emit('Processing {}'.format(self.E.basename))
		self.logUpdate.emit('#' * 50 + '\n')

		if self.P.bFlashCorrect:
			self.statusUpdate.emit('Correcting Flash artifact on {}'.format(self.E.basename))
			self.E.correct_flash(trange=self.P.tRange,
				median=self.P.bMedianCorrect, target=self.P.flashCorrectTarget)
			self.E.path = self.E.path.joinpath('Corrected')

		self.nFiles_done = 0
		self.progressValue.emit(0)
		self.progressMaxVal.emit(self.nFiles)

		self.statusUpdate.emit(
			'Processing {}: (0 of {})'.format(self.E.basename, self.nFiles))

		# only call cudaDeconv if we need to deskew or deconvolve
		if self.P.nIters > 0 or (self.P.deskew > 0 and self.P.bSaveDeskewedRaw):
			# generate all the channel specific cudaDeconv arguments for this item
			for chan in self.P.cRange:
				self.__argQueue.append(channel_args(self.E, self.P, chan,
					binary=mainGUI.cudaDeconvPathLineEdit.text()))
			# with the argQueue populated, we can now start the workers
			if not len(self.__argQueue):
				self.logUpdate.emit('ERROR: no channel arguments to process in LLSitem')
				self.finished.emit()
				return
			self.startCUDAWorkers()
		else:
			self.post_process()

		self.timer = QtCore.QTime()
		self.timer.restart()

	def startCUDAWorkers(self):
		# initialize the workers and threads
		self.__CUDAworkers_done = 0
		self.__CUDAthreads = []

		for idx in range(self.NUM_CUDA_THREADS):
			# create new CUDAworker for every thread
			# each CUDAworker will control one cudaDeconv process (which only gets
			# one wavelength at a time)

			# grab the next arguments from the queue
			# THIS BREAKS the relationship between num_cuda_threads
			# and self.__CUDAworkers_done...
			# if len(self.__argQueue)== 0:
			# 	return
			if not len(self.__argQueue):
				return
			args = self.__argQueue.pop(0)

			CUDAworker, thread = newWorkerThread(CudaDeconvWorker, idx, args,
				workerConnect={
					# get progress messages from CUDAworker and pass to parent
					'file_finished': self.on_file_finished,
					'finished': self.on_CUDAworker_done,
					# any messages go straight to the log window
					'logUpdate': self.logUpdate.emit,
					# 'error': self.errorstring  # implement error signal?
				})

			# need to store worker too otherwise will be garbage collected
			self.__CUDAthreads.append((thread, CUDAworker))
			# connect mainGUI abort CUDAworker signal to the new CUDAworker
			self.sig_abort.connect(CUDAworker.abort)

			# start the thread
			thread.start()

	def on_file_finished(self, worker_id, filename):
		# send report to the log window
		gd = llspy.parse.parse_filename(filename)
		report = "finished {}: channel: {} time: {}".format(
			gd['basename'], gd['channel'], gd['stack'])
		self.logUpdate.emit(report)
		# update status bar
		self.nFiles_done = self.nFiles_done+1
		self.statusUpdate.emit('Processing {}: ({} of {})'.format(
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
		self.logUpdate.emit('CUDAworker #{} done\n'.format(worker_id))
		self.__CUDAworkers_done += 1
		if self.__CUDAworkers_done == self.NUM_CUDA_THREADS:
			# all the workers are finished, cleanup thread(s) and start again
			for thread, _ in self.__CUDAthreads:
				thread.quit()
				thread.wait()
			self.__CUDAthreads = []
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

		if self.P.bDoRegistration:
			self.statusUpdate.emit(
				'Doing Channel Registration: {}'.format(self.E.basename))
			self.E.register(self.P.regRefWave, self.P.regMode, self.P.regCalibDir)

		if self.P.bMergeMIPs:
			self.statusUpdate.emit(
				'Merging MIPs: {}'.format(self.E.basename))
			self.E.mergemips()
		else:
			for mipfile in self.E.path.glob('**/*comboMIP_*'):
				mipfile.unlink()  # clean up any combo MIPs from previous runs

		# if self.P.bMergeMIPsraw:
		# 	if self.E.path.joinpath('Deskewed').is_dir():
		# 		self.statusUpdate.emit(
		# 			'Merging raw MIPs: {}'.format(self.E.basename))
		# 		self.E.mergemips('Deskewed')

		# if we did camera correction, move the resulting processed folders to
		# the parent folder, and optionally delete the corrected folder
		if self.P.bFlashCorrect:
			if self.E.path.name == 'Corrected':
				parent = self.E.path.parent
				for d in ['GPUdecon', 'Deskewed', 'CPPdecon']:
					subd = self.E.path.joinpath(d)
					if subd.exists():
						target = parent.joinpath(d)
						if target.exists():
							shutil.rmtree(target)
						subd.rename(target)
				if not self.P.bSaveCorrected:
					shutil.rmtree(self.E.path)
					self.E.path = parent

		if self.P.bCompress:
			self.statusUpdate.emit(
				'Compressing Raw: {}'.format(self.E.basename))
			self.E.compress()

		self.finished.emit()

	@QtCore.pyqtSlot()
	def abort(self):
		self.logUpdate.emit('LLSworker #{} notified to abort'.format(self.__id))
		if len(self.__CUDAthreads):
			self.aborted = True
			self.__argQueue = []
			self.sig_abort.emit()
			# self.processButton.setDisabled(True) # will be reenabled when workers done
		else:
			self.finished.emit()


class MyHandler(FileSystemEventHandler, QtCore.QObject):

	foundLLSdir = QtCore.pyqtSignal(str)
	lostListItem = QtCore.pyqtSignal(str)
	processRequest = QtCore.pyqtSignal()

	def __init__(self):
		super(MyHandler, self).__init__()

	def on_created(self, event):
		# Called when a file or directory is created.
		if event.is_directory:
			pass
		else:
			if 'Settings.txt' in event.src_path:
				self.foundLLSdir.emit(osp.dirname(event.src_path))
				self.processRequest.emit()

	def on_deleted(self, event):
		# Called when a file or directory is created.
		if event.is_directory:
			# TODO:  Is it safe to directly access main gui listbox here?
			if len(mainGUI.listbox.findItems(event.src_path, QtCore.Qt.MatchExactly)):
				self.lostListItem.emit(event.src_path)


class main_GUI(QtW.QMainWindow, form_class):
	"""docstring for main_GUI"""

	sig_abort_LLSworkers = QtCore.pyqtSignal()
	sig_item_finished = QtCore.pyqtSignal()
	sig_processing_done = QtCore.pyqtSignal()

	def __init__(self, parent=None):
		super(main_GUI, self).__init__(parent)
		self.setupUi(self)  # method inherited from form_class to init UI
		self.setWindowTitle("Lattice Light Sheet")
		self.LLSItemThreads = []
		self.argQueue = []  # holds all argument lists that will be sent to threads
		self.aborted = False  # current abort status
		self.inProcess = False
		self.observer = None  # for watching the watchdir

		# delete  reintroduce custom LLSDragDropTable
		self.listbox.setParent(None)
		self.listbox = LLSDragDropTable(self.tab_process)
		self.process_tab_layout.insertWidget(0, self.listbox)

		# connect buttons
		self.previewButton.clicked.connect(self.onPreview)
		self.processButton.clicked.connect(self.onProcess)

		self.watchDirToolButton.clicked.connect(self.changeWatchDir)
		self.watchDirCheckBox.stateChanged.connect(
			lambda st: self.startWatcher() if st else self.stopWatcher())

		# connect actions
		self.actionOpen_LLSdir.triggered.connect(self.openLLSdir)
		self.actionRun.triggered.connect(self.onProcess)
		self.actionAbort.triggered.connect(self.abort_workers)
		self.actionPreview.triggered.connect(self.onPreview)
		self.actionSave_Settings_as_Default.triggered.connect(
			self.saveCurrentAsDefault)
		self.actionLoad_Default_Settings.triggered.connect(
			self.loadDefaultSettings)

		self.actionReduce_to_Raw.triggered.connect(self.reduceSelected)
		self.actionCompress_Folder.triggered.connect(self.compressSelected)
		self.actionDecompress_Folder.triggered.connect(self.decompressSelected)
		self.actionConcatenate.triggered.connect(self.concatenateSelected)
		self.actionRename_Scripted.triggered.connect(self.renameSelected)

		# set validators for cRange and tRange fields
		ctrangeRX = QtCore.QRegExp("(\d[\d-]*,?)*")  # could be better
		ctrangeValidator = QtGui.QRegExpValidator(ctrangeRX)
		self.processCRangeLineEdit.setValidator(ctrangeValidator)
		self.processTRangeLineEdit.setValidator(ctrangeValidator)
		self.previewTRangeLineEdit.setValidator(ctrangeValidator)

		self.cudaDeconvPathToolButton.clicked.connect(lambda:
			self.cudaDeconvPathLineEdit.setText(
				QtW.QFileDialog.getOpenFileName(
					self, 'Choose cudaDeconv Binary', '/usr/local/bin/')[0]))

		self.radialftPathToolButton.clicked.connect(lambda:
			self.radialftPathLineEdit.setText(
				QtW.QFileDialog.getOpenFileName(
					self, 'Choose radialft Binary', '/usr/local/bin/')[0]))

		self.otfFolderToolButton.clicked.connect(lambda:
			self.otfFolderLineEdit.setText(
				QtW.QFileDialog.getExistingDirectory(
					self, 'Set OTF Directory', '', QtW.QFileDialog.ShowDirsOnly)))

		self.camParamTiffToolButton.clicked.connect(lambda:
			self.camParamTiffLineEdit.setText(
				QtW.QFileDialog.getOpenFileName(
					self, 'Chose Camera Parameters Tiff', '',
					"Image Files (*.png *.tif *.tiff)")[0]))

		self.defaultRegCalibPathToolButton.clicked.connect(lambda:
			self.defaultRegCalibPathLineEdit.setText(
				QtW.QFileDialog.getExistingDirectory(
					self, 'Set default Registration Calibration Directory',
					'', QtW.QFileDialog.ShowDirsOnly)))

		self.RegCalibPathToolButton.clicked.connect(lambda:
			self.RegCalibPathLineEdit.setText(
				QtW.QFileDialog.getExistingDirectory(
					self, 'Set Registration Calibration Directory',
					'', QtW.QFileDialog.ShowDirsOnly)))

		# connect worker signals and slots
		self.sig_item_finished.connect(self.on_item_finished)
		self.sig_processing_done.connect(self.on_proc_finished)

		# Restore settings from previous session and show ready status
		if not osp.isfile(GUIsettings.fileName()):
			defaultINI = osp.join(thisDirectory, 'guiDefaults.ini')
			programDefaults = QtCore.QSettings(defaultINI, QtCore.QSettings.IniFormat)
			guirestore(self, programDefaults)
		else:
			guirestore(self, GUIsettings)

		self.watcherStatus = QtW.QLabel()
		self.statusBar.insertPermanentWidget(0, self.watcherStatus)
		if self.watchDirCheckBox.isChecked():
			self.startWatcher()

		self.clock.display("00:00:00")
		self.statusBar.showMessage('Ready')

	@QtCore.pyqtSlot()
	def startWatcher(self):
		self.watchdir = self.watchDirLineEdit.text()
		if osp.isdir(self.watchdir):
			self.log.append('Starting watcher on {}'.format(self.watchdir))
			self.watcherStatus.setText("👁 {}".format(osp.basename(self.watchdir)))
			self.watchHandler = MyHandler()
			self.watchHandler.foundLLSdir.connect(self.listbox.addPath)
			self.watchHandler.lostListItem.connect(self.listbox.removePath)
			self.watchHandler.processRequest.connect(self.onProcess)
			self.observer = Observer()
			self.observer.schedule(self.watchHandler, self.watchdir, recursive=True)
			self.observer.start()

	@QtCore.pyqtSlot()
	def stopWatcher(self):
		if self.observer is not None and self.observer.is_alive():
			self.observer.stop()
			self.observer.join()
			self.observer = None
			self.log.append('Stopped watcher on {}'.format(self.watchdir))
			self.watchdir = None
		if not self.observer:
			self.watcherStatus.setText("")

	@QtCore.pyqtSlot()
	def changeWatchDir(self):
		self.watchDirLineEdit.setText(QtW.QFileDialog.getExistingDirectory(
			self, 'Choose directory to monitor for new LLSdirs', '',
			QtW.QFileDialog.ShowDirsOnly))
		if self.watchDirCheckBox.isChecked():
			self.stopWatcher()
			self.startWatcher()

	def saveCurrentAsDefault(self):
		if osp.isfile(defaultSettings.fileName()):
			reply = QtW.QMessageBox.question(self, 'Save Settings',
				"Overwrite existing default GUI settings?",
				QtW.QMessageBox.Yes | QtW.QMessageBox.No,
				QtW.QMessageBox.No)
			if reply != QtW.QMessageBox.Yes:
				return
		guisave(self, defaultSettings)

	def loadDefaultSettings(self):
		if not osp.isfile(defaultSettings.fileName()):
			reply = QtW.QMessageBox.information(self, 'Load Settings',
				"Default settings have not yet been saved.  Use Save Settings")
			if reply != QtW.QMessageBox.Yes:
				return
		guirestore(self, defaultSettings)

	def openLLSdir(self):
		path = QtW.QFileDialog.getExistingDirectory(self,
				'Choose LLSdir to add to list', '', QtW.QFileDialog.ShowDirsOnly)
		if path is not None:
			self.listbox.addPath(path)

	def incrementProgress(self):
		# with no values, simply increment progressbar
		self.progressBar.setValue(self.progressBar.value()+1)

	def onPreview(self):
		self.previewButton.setDisabled(True)
		if self.listbox.rowCount() == 0:
			QtW.QMessageBox.warning(self, "Nothing Added!",
				'Nothing to preview! Drop LLS experiment folders into the list',
				QtW.QMessageBox.Ok, QtW.QMessageBox.NoButton)
			return

		# if there's only one item on the list show it
		if self.listbox.rowCount() == 1:
			firstRowSelected = 0
		# otherwise, prompt the user to select one
		else:
			selectedRows = self.listbox.selectionModel().selectedRows()
			if not len(selectedRows):
					QtW.QMessageBox.warning(self, "Nothing Selected!",
						"Please select an item (row) from the table to preview",
						QtW.QMessageBox.Ok, QtW.QMessageBox.NoButton)
					return
			else:
				# if they select multiple, chose the first one
				firstRowSelected = selectedRows[0].row()

		procTRangetext = self.previewTRangeLineEdit.text()
		if procTRangetext:
			tRange = string_to_iterable(procTRangetext)
		else:
			tRange = 0

		itemPath = self.listbox.item(firstRowSelected, 0).text()
		opts = self.getValidatedOptions()
		w, thread = newWorkerThread(TimePointWorker, itemPath, tRange, opts,
			workerConnect={'previewReady': self.displayPreview}, start=True)

		self.previewthreads = (w, thread)

	@QtCore.pyqtSlot(np.ndarray)
	def displayPreview(self, array):
		# FIXME:  pyplot should not be imported in pyqt
		# use https://matplotlib.org/2.0.0/api/backend_qt5agg_api.html
		import matplotlib.pyplot as plt
		imdisplay.imshow3D(array, cmap='gray', interpolation='nearest')
		plt.show()
		self.previewButton.setEnabled(True)

	def onProcess(self):
		# prevent additional button clicks which processing
		self.processButton.setDisabled(True)

		if self.listbox.rowCount() == 0:
			QtW.QMessageBox.warning(self, "Nothing Added!",
				'Nothing to process! Drag and drop folders into the list',
				QtW.QMessageBox.Ok, QtW.QMessageBox.NoButton)
			self.processButton.setEnabled(True)
			return

		# store current options for this processing run.  ??? Unecessary?
		self.optionsOnProcessClick = self.getValidatedOptions()

		if not self.inProcess:  # so far, only one item allowed processing at a time
			self.inProcess = True
			self.disableProcessButton()
			self.process_next_item()
			self.statusBar.showMessage('Starting processing ...')
			self.inProcess = True
		else:
			self.log.append('ignoring request to process, already processing...')

	def process_next_item(self):
		# get path from first row and create a new LLSdir object
		self.currentItem = self.listbox.item(0, 1).text()
		self.currentPath = self.listbox.item(0, 0).text()
		idx = 0  # might use this later to spawn more threads
		opts = self.optionsOnProcessClick
		LLSworker, thread = newWorkerThread(LLSitemWorker, idx, self.currentPath,
			opts, workerConnect={
				'finished': self.on_item_finished,
				'statusUpdate': self.statusBar.showMessage,
				'logUpdate': self.log.append,
				'progressMaxVal': self.progressBar.setMaximum,
				'progressValue': self.progressBar.setValue,
				'progressUp': self.incrementProgress,
				'clockUpdate': self.clock.display,
				'error': self.abort_workers,
				# 'error': self.errorstring  # implement error signal?
			})

		self.LLSItemThreads.append((thread, LLSworker))

		# connect mainGUI abort LLSworker signal to the new LLSworker
		self.sig_abort_LLSworkers.connect(LLSworker.abort)

		# prepare and start LLSworker:
		# thread.started.connect(LLSworker.work)
		thread.start()  # this will emit 'started' and start thread's event loop

		# recolor the first row to indicate processing
		self.listbox.setRowBackgroudColor(0, '#E9E9E9')
		self.listbox.clearSelection()
		# start a timer in the main GUI to measure item processing time
		self.timer = QtCore.QTime()
		self.timer.restart()

	def disableProcessButton(self):
		# turn Process button into a Cancel button and udpate menu items
		self.processButton.clicked.disconnect()
		self.processButton.setText('CANCEL')
		self.processButton.clicked.connect(self.abort_workers)
		self.processButton.setEnabled(True)
		self.actionRun.setDisabled(True)
		self.actionAbort.setEnabled(True)

	@QtCore.pyqtSlot()
	def on_proc_finished(self):
		# change Process button back to "Process" and udpate menu items
		self.processButton.clicked.disconnect()
		self.processButton.clicked.connect(self.onProcess)
		self.processButton.setText('Process')
		self.actionRun.setEnabled(True)
		self.actionAbort.setDisabled(True)

		# reinit statusbar and clock
		self.statusBar.showMessage('Ready')
		self.clock.display("00:00:00")
		self.inProcess = False
		self.aborted = False

		self.log.append("Processing Finished")

	@QtCore.pyqtSlot()
	def on_item_finished(self):
		thread, worker  = self.LLSItemThreads.pop(0)
		thread.quit()
		thread.wait()
		self.clock.display("00:00:00")
		self.progressBar.setValue(0)
		if self.aborted:
			self.sig_processing_done.emit()
		else:
			itemTime = QtCore.QTime(0, 0).addMSecs(self.timer.elapsed()).toString()
			self.log.append(">" * 4 + " Item {} finished in {} ".format(
				self.currentItem, itemTime) + "<" * 4)
			self.listbox.removePath(self.currentPath)
			self.currentPath = None
			self.currentItem = None
			if self.listbox.rowCount() > 0:
				self.process_next_item()
			else:
				self.sig_processing_done.emit()

	@QtCore.pyqtSlot()
	def abort_workers(self):
		self.statusBar.showMessage('Aborting ...')
		self.log.append('Message sent to abort ...')
		if len(self.LLSItemThreads):
			self.aborted = True
			self.sig_abort_LLSworkers.emit()
			if self.listbox.rowCount():
				self.listbox.setRowBackgroudColor(0, '#FFFFFF')
			# self.processButton.setDisabled(True) # will be reenabled when workers done
		else:
			self.sig_processing_done.emit()

	def getValidatedOptions(self):
		options = {
			'bFlashCorrect': self.camcorCheckBox.isChecked(),
			'flashCorrectTarget': self.camcorTargetCombo.currentText(),
			'bMedianCorrect': self.medianFilterCheckBox.isChecked(),
			'bSaveCorrected': self.saveCamCorrectedCheckBox.isChecked(),
			'edgeTrim': ((self.trimZ0SpinBox.value(), self.trimZ1SpinBox.value()),
						(self.trimY0SpinBox.value(), self.trimY1SpinBox.value()),
						(self.trimX0SpinBox.value(), self.trimX1SpinBox.value())),
			'nIters': self.iterationsSpinBox.value() if self.doDeconGroupBox.isChecked() else 0,
			'nApodize': self.apodizeSpinBox.value(),
			'nZblend': self.zblendSpinBox.value(),
			# if bRotate == True and rotateAngle is not none: rotate based on sheet angle
			# this will be done in the LLSdir function
			'bRotate': self.rotateGroupBox.isChecked(),
			'rotate': (self.rotateOverrideSpinBox.value() if
							self.rotateOverrideCheckBox.isChecked() else None),
			'bSaveDeskewedRaw': self.saveDeskewedCheckBox.isChecked(),
			# 'bsaveDecon': self.saveDeconvolvedCheckBox.isChecked(),
			'MIP': tuple([int(i) for i in (self.deconXMIPCheckBox.isChecked(),
								self.deconYMIPCheckBox.isChecked(),
								self.deconZMIPCheckBox.isChecked())]),
			'MIPraw': tuple([int(i) for i in (self.deskewedXMIPCheckBox.isChecked(),
								self.deskewedYMIPCheckBox.isChecked(),
								self.deskewedZMIPCheckBox.isChecked())]),
			'bMergeMIPs': self.deconJoinMIPCheckBox.isChecked(),
			# 'bMergeMIPsraw': self.deskewedJoinMIPCheckBox.isChecked(),
			'buint16': ('16' in self.deconvolvedBitDepthCombo.currentText()),
			'buint16raw': ('16' in self.deskewedBitDepthCombo.currentText()),
			'bBleachCor': self.bleachCorrectionCheckBox.isChecked(),
			'bDoRegistration': self.doRegistrationGroupBox.isChecked(),
			'regRefWave': int(self.channelRefCombo.currentText()),
			'regMode': self.channelRefModeCombo.currentText(),
			'otfDir': self.otfFolderLineEdit.text(),
			'bCompress': self.compressRawCheckBox.isChecked(),
			'bReprocess': False,
			'width': self.cropWidthSpinBox.value(),
			'shift': self.cropShiftSpinBox.value(),
			'bAutoBackground': self.backgroundAutoRadio.isChecked(),
			'background': self.backgroundFixedSpinBox.value(),

			# 'bRollingBall': self.backgroundRollingRadio.isChecked(),
			# 'rollingBall': self.backgroundRollingSpinBox.value()
		}

		rCalibText = self.RegCalibPathLineEdit.text()
		dCalibText = self.defaultRegCalibPathLineEdit.text()
		if rCalibText and rCalibText is not '':
			options['regCalibDir'] = rCalibText
		else:
			if dCalibText and dCalibText is not '':
				options['regCalibDir'] = dCalibText
			else:
				options['regCalibDir'] = None

		if self.cropAutoRadio.isChecked():
			options['cropMode'] = 'auto'
		elif self.cropManualRadio.isChecked():
			options['cropMode'] = 'manual'
		else:
			options['cropMode'] = 'none'

		procCRangetext = self.processCRangeLineEdit.text()
		if procCRangetext:
			options['cRange'] = string_to_iterable(procCRangetext)
		else:
			options['cRange'] = None

		procTRangetext = self.processTRangeLineEdit.text()
		if procTRangetext:
			options['tRange'] = string_to_iterable(procTRangetext)
		else:
			options['tRange'] = None

		return options

	def reduceSelected(self):
		for item in self.listbox.selectedPaths():
			llspy.LLSdir(item).reduce_to_raw()

	def compressSelected(self):
		for item in self.listbox.selectedPaths():
			llspy.LLSdir(item).compress()

	def decompressSelected(self):
		for item in self.listbox.selectedPaths():
			llspy.LLSdir(item).decompress()

	def concatenateSelected(self):
		selectedPaths = self.listbox.selectedPaths()
		llspy.llsdir.concatenate_folders(selectedPaths)
		[self.listbox.removePath(p) for p in selectedPaths]
		[self.listbox.addPath(p) for p in selectedPaths]

	def renameSelected(self):
		for item in self.listbox.selectedPaths():
			llspy.llsdir.rename_iters(item)
			self.listbox.removePath(item)
			[self.listbox.addPath(osp.join(item, p)) for p in os.listdir(item)]

	@QtCore.pyqtSlot(str, str)
	def post_validation_error(self, errMsg, tbackstring):
		schemaDefaults = llspy.schema.__defaults__
		schemaerrRX = re.compile(r'.*data\[(?P<dictItem>.+)\]. Got (?P<gotValue>.+)')
		gd = schemaerrRX.search(errMsg)
		self.msgBox = QtW.QMessageBox()
		self.msgBox.setIcon(QtW.QMessageBox.Warning)
		self.msgBox.setText("Validation Error")

		if gd:
			item = gd.groupdict()['dictItem']
			value = gd.groupdict()['gotValue']
			msgtext = "Not a valid entry for {}.\nGot: {}\n\nDescription: {}\nDefault: {}".format(
					item, value, schemaDefaults[item.strip("'")][1], schemaDefaults[item.strip("'")][0])
		else:
			msgtext = errMsg

		self.msgBox.setInformativeText(msgtext)
		self.msgBox.setWindowTitle("Schema Error Window")
		self.msgBox.setDetailedText(tbackstring)
		self.msgBox.show()

	def closeEvent(self, event):
		''' triggered when close button is clicked on main window '''
		if self.listbox.rowCount():
			reply = QtW.QMessageBox.question(self, 'Unprocessed items!',
				"You have unprocessed items.  Are you sure you want to quit?",
				QtW.QMessageBox.Yes | QtW.QMessageBox.No,
				QtW.QMessageBox.No)
			if reply != QtW.QMessageBox.Yes:
				event.ignore()
				return
		guisave(self, GUIsettings)

		# if currently processing, need to shut down threads...
		if self.inProcess:
			self.abort_workers()
			self.sig_processing_done.connect(QtW.QApplication.quit)
		else:
			QtW.QApplication.quit()


if __name__ == "__main__":
	app = QtW.QApplication(sys.argv)
	# dlg = LogWindow()
	# dlg.show()
	mainGUI = main_GUI()
	mainGUI.show()
	mainGUI.raise_()

	exceptionHandler = ExceptionHandler()
	sys.excepthook = exceptionHandler.handler
	exceptionHandler.schemaError.connect(mainGUI.post_validation_error)

	sys.exit(app.exec_())
