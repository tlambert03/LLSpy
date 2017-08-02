# -*- coding: utf-8 -*-
from __future__ import print_function, division

import os.path as osp
from PyQt5 import QtCore, QtGui, uic
from PyQt5 import QtWidgets as QtW
# import sys
# sys.path.append(osp.join(osp.dirname(osp.abspath(__file__)),'..'))
import llspy
import imdisplay
import logging
from functools import partial
import inspect
import sys

import time # for testing

form_class = uic.loadUiType(osp.join(osp.dirname(osp.abspath(__file__)), 'main_gui.ui'))[0]
# form_class = uic.loadUiType('./llspy/gui/main_gui.ui')[0]  # for debugging

# platform independent settings file
QtCore.QCoreApplication.setOrganizationName("LLSpy")
QtCore.QCoreApplication.setOrganizationDomain("llspy.com")
QtCore.QCoreApplication.setApplicationName("LLSpyGUI")
settings = QtCore.QSettings()
# located at settings.fileName()


def trap_exc_during_debug(*args):
	# when app raises uncaught exception, print info
	print(args)


# install exception hook: without this, uncaught exception would cause application to exit
sys.excepthook = trap_exc_during_debug


def byteArrayToString(bytearr):
	if sys.version_info.major < 3:
		return str(bytearr)
	else:
		return str(bytearr, encoding='utf-8')


#FIXME: temporary testing
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
			llspy.util.util.pyrange_to_perlregex(P.tRange))

	args = llspy.core.cudabinwrapper.assemble_args(binary,
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


def guirestore(widget, settings):
	# Restore geometry
	selfName = widget.objectName()
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


class DragDropTableView(QtW.QTableWidget):

	colHeaders = ['path', 'name', 'nC', 'nT', 'nZ', 'nY', 'nX', 'desQ']
	nCOLS = len(colHeaders)

	# A signal needs to be defined on class level:
	dropSignal = QtCore.pyqtSignal(list, name="dropped")
	# This signal emits when a URL is dropped onto this list,
	# and triggers handler defined in parent widget.

	def __init__(self, parent=None):
		super(DragDropTableView, self).__init__(0, self.nCOLS, parent)
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

	def addLLSitem(self, E):
		shortname = osp.sep.join(E.path.parts[-2:])
		logging.info('Add: {}'.format(shortname))
		rowPosition = self.rowCount()
		self.insertRow(rowPosition)
		item = [str(E.path),
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
			links = []
			for url in event.mimeData().urls():
				links.append(str(url.toLocalFile()))
			self.dropSignal.emit(links)
		else:
			event.ignore()

	def keyPressEvent(self, event):
		super(DragDropTableView, self).keyPressEvent(event)
		if (event.key() == QtCore.Qt.Key_Delete or
			event.key() == QtCore.Qt.Key_Backspace):
			indices = self.selectionModel().selectedRows()
			i = 0
			for index in sorted(indices):
				self.removeRow(index.row()-i)
				i += 1


class CudaDeconvWorker(QtCore.QObject):

	sig_file_finished = QtCore.pyqtSignal(int, str)  # worker id, step description: emitted every step through work() loop
	sig_CUDA_done = QtCore.pyqtSignal(int)  # worker id: emitted at end of work()
	sig_msg = QtCore.pyqtSignal(str)  # message to be shown to user

	def __init__(self, id, args):
		super(CudaDeconvWorker, self).__init__()
		self.__id = int(id)
		self.__args = args
		self.__abort = False

		# QProcess object for external app
		self.process = QtCore.QProcess(self)
		self.binary = 'cudaDeconv'
		# self.process.setProcessEnvironment(env)

		# QProcess emits `readyRead` when there is data to be read
		self.process.readyRead.connect(self.procOutputReady)
		# Just to prevent accidentally running multiple times

	# TODO: make pickup something other than <<<FINISHED>>>
	def procOutputReady(self):
		while self.process.canReadLine():
			line = self.process.readLine()
			line = byteArrayToString(line)
			if "<<<FINISHED>>>" in line:
				path = line.split("<<<FINISHED>>>")[1]
				base = osp.basename(path.strip())
				gd = llspy.core.parse.parse_filename(base)
				report = "finished {}: channel: {} time: {}".format(
					gd['basename'], gd['channel'], gd['stack'])
				self.sig_file_finished.emit(self.__id, report)
			else:
				self.sig_msg.emit(line.rstrip())

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
		self.sig_msg.emit('='*20 + '\nRunning cudaDeconv thread_{} with args: '
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
				self.sig_msg.emit('aborting worker #{}'.format(self.__id))
				break
		self.process.waitForFinished()

	def onFinished(self, exitCode,  exitStatus):
		self.sig_msg.emit('cudaDeconv process finished with code({}) and '
			'status: {}'.format(exitCode,  exitStatus))
		self.sig_CUDA_done.emit(self.__id)

	def abort(self):
		self.sig_msg.emit('Worker #{} notified to abort'.format(self.__id))
		self.__abort = True


class LLSpreprocessor(QtCore.QObject):
	pass


class main_GUI(QtW.QMainWindow, form_class):
	"""docstring for main_GUI"""

	sig_abort_CUDAworkers = QtCore.pyqtSignal()
	sig_processing_starting = QtCore.pyqtSignal()
	sig_item_finished = QtCore.pyqtSignal()
	sig_processing_done = QtCore.pyqtSignal()
	NUM_CUDA_THREADS = 1

	def __init__(self, parent=None):
		super(main_GUI, self).__init__(parent)
		self.setupUi(self)  # method inherited from form_class to init UI
		self.setWindowTitle("Lattice Light Sheet")
		self.argQueue = []  # holds all argument lists that will be sent to threads
		self.aborted = False  # current abort status
		self.inProcess = False

		# delete  reintroduce custom DragDropTableView
		self.listbox.setParent(None)
		self.listbox = DragDropTableView(self.tab_process)
		self.process_tab_layout.insertWidget(0, self.listbox)
		self.listbox.dropSignal.connect(self.onFolderDroppedTable)

		# connect buttons
		self.processButton.clicked.connect(self.onProcess)
		self.previewButton.clicked.connect(self.onPreview)

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
		self.sig_processing_starting.connect(self.on_proc_starting)
		self.sig_processing_done.connect(self.on_proc_finished)

		# Restore settings from previous session and show ready status
		guirestore(self, settings)
		self.clock.display("00:00:00")
		self.statusBar.showMessage('Ready')

	def onFolderDroppedTable(self, links):
		''' Triggered after URLs are dropped onto self.listbox '''
		for url in links:
			if osp.exists(url) and osp.isdir(url):
				# If this folder is not on the list yet, add it to the list:
				E = llspy.LLSdir(url)
				shortname = osp.sep.join(E.path.parts[-2:])
				if not E.has_settings:
					logging.warn('No Settings.txt! Ignoring: {}'.format(shortname))
					return
				# if it's not already on the list, add it
				if len(self.listbox.findItems(shortname, QtCore.Qt.MatchExactly)) == 0:
					self.listbox.addLLSitem(E)

	def onPreview(self):
		if self.listbox.rowCount() == 0:
			QtW.QMessageBox.warning(self, "Nothing Added!",
				'Nothing to preview! Drag and drop folders into the list',
				QtW.QMessageBox.Ok, QtW.QMessageBox.NoButton)
			return

		if self.listbox.rowCount() == 1:
			firstRowSelected = 0
		else:
			selectedRows = self.listbox.selectionModel().selectedRows()
			if not len(selectedRows):
					QtW.QMessageBox.warning(self, "Nothing Selected!",
						"Please select an item (row) from the table to preview",
						QtW.QMessageBox.Ok, QtW.QMessageBox.NoButton)
					return
			else:
				firstRowSelected = selectedRows[0].row()

		procTRangetext = self.previewTRangeLineEdit.text()
		if procTRangetext:
			tRange = string_to_iterable(procTRangetext)
		else:
			tRange = 0

		E = llspy.LLSdir(self.listbox.item(firstRowSelected, 0).text())
		previewStack = llspy.core.llsdir.preview(E, tRange, **self.validatedOptions)

		# for some reason... if this import is put at the top, it crashes with:
		# [QNSApplication _setup:]: unrecognized selector sent to instance
		import matplotlib.pyplot as plt
		imdisplay.imshow3D(previewStack, title="Previewing: {}".format(E.basename),
			cmap='gray', interpolation='nearest')
		plt.show()

		# imdisplay.slices3D(previewStack[0])
		# win = pg.GraphicsWindow()
		# vb = win.addViewBox()
		# for stack in previewStack:
		# 	s = stack.transpose(0, 2, 1)
		# 	pg.image(s, levels=(s.min() - 20, s.max() * 0.5))

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
		self.optionsOnProcessClick = self.validatedOptions

		self.sig_processing_starting.emit()
		self.process_next_item()

	def process_next_item(self):
		# get path from first row and create a new LLSdir object
		nextitem = self.listbox.item(0, 0).text()
		E = llspy.LLSdir(nextitem)  # create new LLSdir object

		# calculate parameters specific to this LLSdir based on options when
		# process button was originally clicked
		P = E.localParams(**self.optionsOnProcessClick)

		# #### PREPROCESS THREADS ######### <<<<<<<<<<<

		# we process one folder at a time. Progress bar updates per Z stack
		# so the maximum is the total number of timepoints * channels
		self.cur_nFiles = len(P.tRange) * len(P.cRange)
		self.cur_File = E.basename

		self.log.append('\n' + '#' * 65)
		self.log.append('Processing {}'.format(self.cur_File))
		self.log.append('#' * 65 + '\n')

		self.progressBar.setMaximum(self.cur_nFiles)
		self.progressBar.setValue(0)
		self.statusBar.showMessage('Processing {} ... stack {} of {}'.format(
			self.cur_File, 0, self.cur_nFiles))
		self.listbox.setRowBackgroudColor(0, '#484DE7')
		self.listbox.clearSelection()

		# generate all the channel specific cudaDeconv arguments for this item
		for chan in P.cRange:
			self.argQueue.append(channel_args(E, P, chan))
		# with the argQueue populated, we can now start the workers
		self.startCUDAWorkers()

		# start timer for estimation of time left
		self.timer = QtCore.QTime()
		self.timer.restart()

	def startCUDAWorkers(self):
		# initialize the workers and threads
		self.__CUDAworkers_done = 0
		self.__threads = []
		for idx in range(self.NUM_CUDA_THREADS):
			# create new CUDAworker for every thread
			# each CUDAworker will control one cudaDeconv process (which only gets
			# one wavelength at a time)

			# grab the next arguments from the queue
			args = self.argQueue.pop(0)
			CUDAworker = CudaDeconvWorker(idx, args)
			thread = QtCore.QThread()
			thread.setObjectName('thread_' + str(idx))
			# need to store worker too otherwise will be garbage collected
			self.__threads.append((thread, CUDAworker))
			# transfer the thread to the worker
			CUDAworker.moveToThread(thread)

			# get progress messages from CUDAworker:
			CUDAworker.sig_file_finished.connect(self.on_file_finished)
			CUDAworker.sig_CUDA_done.connect(self.on_CUDAworker_done)
			# any messages go straight to the log window
			CUDAworker.sig_msg.connect(self.log.append)

			# connect mainGUI abort CUDAworker signal to the new CUDAworker
			self.sig_abort_CUDAworkers.connect(CUDAworker.abort)

			# get ready to start CUDAworker:
			thread.started.connect(CUDAworker.work)
			thread.start()  # this will emit 'started' and start thread's event loop

	@QtCore.pyqtSlot(int, str)
	def on_file_finished(self, worker_id, data):
		# a file has been finished ... update the progressbar and the log
		self.log.append('thread_{}: {}'.format(int(worker_id), data))
		numFilesSoFar = self.progressBar.value()
		self.progressBar.setValue(numFilesSoFar + 1)
		self.statusBar.showMessage('Processing {} ... stack {} of {}'.format(
			self.cur_File, numFilesSoFar, self.cur_nFiles))
		# update the LCD with estimate of remaining time
		avgTimePerFile = int(self.timer.elapsed() / (numFilesSoFar+1))
		remainingTime = (self.cur_nFiles - numFilesSoFar) * avgTimePerFile
		self.clock.display(QtCore.QTime(0, 0).addMSecs(remainingTime).toString())

	@QtCore.pyqtSlot(int)
	def on_CUDAworker_done(self, worker_id):
		# a CUDAworker has finished... update the log and check if any are still going
		self.log.append('worker #{} done\n'.format(worker_id))
		self.__CUDAworkers_done += 1
		if self.__CUDAworkers_done == self.NUM_CUDA_THREADS:
			# all the workers are finished, cleanup thread(s) and start again
			for thread, _ in self.__threads:
				thread.quit()
				thread.wait()
			# if there's still stuff left in the argQueue for this item, keep going
			if self.aborted:
				self.aborted = False
				self.progressBar.setValue(0)
				self.statusBar.showMessage('Aborting ...')
				self.sig_processing_done.emit()
			elif len(self.argQueue):
				self.startCUDAWorkers()
			# otherwise send the signal that this item is done
			else:
				self.sig_item_finished.emit()

	@QtCore.pyqtSlot()
	def on_proc_starting(self):
		self.inProcess = True
		# turn Process button into a Cancel button
		self.processButton.clicked.disconnect()
		self.processButton.setText('CANCEL')
		self.processButton.clicked.connect(self.abort_workers)
		self.processButton.setEnabled(True)

	@QtCore.pyqtSlot()
	def on_proc_finished(self):
		# change Process button back to "Process" and reinit progressBar
		self.processButton.clicked.disconnect()
		self.processButton.clicked.connect(self.onProcess)
		self.processButton.setText('Process')
		# self.processButton.setEnabled(True)
		self.statusBar.showMessage('Ready')
		self.clock.display("00:00:00")

		self.__threads = []
		self.inProcess = False

	@QtCore.pyqtSlot()
	def on_item_finished(self):
		self.listbox.removeRow(0)
		self.clock.display("00:00:00")
		if self.listbox.rowCount() > 0:
			self.process_next_item()
		else:
			self.sig_processing_done.emit()

	@QtCore.pyqtSlot()
	def abort_workers(self):
		if len(self.__threads):
			self.aborted = True
			self.argQueue = []
			self.sig_abort_workers.emit()
			self.listbox.setRowBackgroudColor(0, '#FFFFFF')
			# self.processButton.setDisabled(True) # will be reenabled when workers done
		else:
			self.sig_processing_done.emit()

	@property
	def validatedOptions(self):
		options = {
			'bFlashCorrect': self.camcorCheckBox.isChecked(),
			'bMedianCorrect': self.medianFilterCheckBox.isChecked(),
			'edgeTrim': ((self.trimZ0SpinBox.value(), self.trimZ1SpinBox.value()),
						(self.trimY0SpinBox.value(), self.trimY1SpinBox.value()),
						(self.trimX0SpinBox.value(), self.trimX1SpinBox.value())),
			'nIters': self.iterationsSpinBox.value() if self.doDeconGroupBox.isChecked() else 0,
			'nApodize': self.apodizeSpinBox.value(),
			'nZblend': self.zblendSpinBox.value(),
			# if rotate == True and rotateAngle is not none: rotate based on sheet angle
			# this will be done in the LLSdir function
			'bRotate': self.rotateGroupBox.isChecked(),
			'rotate': (self.rotateOverrideSpinBox.value() if
							self.rotateOverrideCheckBox.isChecked() else None),
			'bSaveDeskewedRaw': self.saveDeskewedCheckBox.isChecked(),
			#'bsaveDecon': self.saveDeconvolvedCheckBox.isChecked(),
			'MIP': tuple([int(i) for i in (self.deconXMIPCheckBox.isChecked(),
								self.deconYMIPCheckBox.isChecked(),
								self.deconZMIPCheckBox.isChecked())]),
			'MIPraw': tuple([int(i) for i in (self.deskewedXMIPCheckBox.isChecked(),
								self.deskewedYMIPCheckBox.isChecked(),
								self.deskewedZMIPCheckBox.isChecked())]),
			'bMergeMIPs': self.deconJoinMIPCheckBox.isChecked(),
			'bMergeMIPsraw': self.deskewedJoinMIPCheckBox.isChecked(),
			'buint16': ('16' in self.deconvolvedBitDepthCombo.currentText()),
			'buint16raw': ('16' in self.deskewedBitDepthCombo.currentText()),
			'bBleachCor': self.bleachCorrectionCheckBox.isChecked(),
			'bDoRegistration': self.doRegistrationGroupBox.isChecked(),
			'regRefWave': int(self.channelRefCombo.currentText()),
			'regMode': self.channelRefModeCombo.currentText(),
			'regCalibDir': self.RegCalibPathLineEdit.text(),
			'otfDir': self.otfFolderLineEdit.text(),
			'bCompress': True,
			'bReprocess': False,
			'width': self.cropWidthSpinBox.value(),
			'shift': self.cropShiftSpinBox.value(),
			'bAutoBackground': self.backgroundAutoRadio.isChecked(),
			'background': self.backgroundFixedSpinBox.value(),
			# 'bRollingBall': self.backgroundRollingRadio.isChecked(),
			# 'rollingBall': self.backgroundRollingSpinBox.value()
		}

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
		guisave(self, settings)

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
	window = main_GUI()
	window.show()
	window.raise_()
	sys.exit(app.exec_())
