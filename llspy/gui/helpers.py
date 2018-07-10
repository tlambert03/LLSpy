import time
import os
import sys
import re
import logging
from enum import Enum
from PyQt5 import QtCore, QtWidgets

logger = logging.getLogger(__name__)


# TODO: add timer?
def newWorkerThread(workerClass, *args, **kwargs):
    worker = workerClass(*args, **kwargs)
    thread = QtCore.QThread()
    worker.moveToThread(thread)
    # all workers started using this function must implement work() func
    thread.started.connect(worker.work)
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


class IgnoreMouseWheel(QtCore.QObject):
    """ mixin to prevent mouse wheel from changing spinboxes """
    def __init__(self, val=None, *args, **kwargs):
        super(IgnoreMouseWheel, self).__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        if val is not None:
            self.setValue(val)

    def wheelEvent(self, event):
        event.ignore()


class NoScrollSpin(QtWidgets.QSpinBox, IgnoreMouseWheel):
    pass


class NoScrollDoubleSpin(QtWidgets.QDoubleSpinBox, IgnoreMouseWheel):
    pass


class FileDialogLineEdit(QtWidgets.QFrame):
    textChanged = QtCore.pyqtSignal()

    def __init__(self, val='', *args, **kwargs):
        super(FileDialogLineEdit, self).__init__(*args, **kwargs)
        self.setFrameStyle(self.NoFrame | self.Plain)
        self._layout = QtWidgets.QHBoxLayout()
        self.setLayout(self._layout)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._lineEdit = QtWidgets.QLineEdit(str(val))
        self._lineEdit.textChanged.connect(self.textChanged.emit)
        self._browseButton = QtWidgets.QPushButton('Browse')
        self._browseButton.clicked.connect(self.setPath)
        self._layout.addWidget(self._lineEdit)
        self._layout.addWidget(self._browseButton)

    def setPath(self):
        path = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Choose File or Directory')[0]
        if path is None or path == '':
            return
        else:
            self._lineEdit.setText(path)

    def text(self):
        return self._lineEdit.text()

    def setText(self, value):
        self._lineEdit.setText(value)


class DirDialogLineEdit(FileDialogLineEdit):

    def setPath(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Select Directory',
            '', QtWidgets.QFileDialog.ShowDirsOnly)
        if path is None or path == '':
            return
        else:
            self._lineEdit.setText(path)
            self.textChanged.emit()


class TupleWidgetFrame(QtWidgets.QFrame):
    valueChanged = QtCore.pyqtSignal()

    def __init__(self, tup, *args, **kwargs):
        super(TupleWidgetFrame, self).__init__(*args, **kwargs)
        self.setFrameStyle(self.Panel | self.Raised)
        self._layout = QtWidgets.QHBoxLayout()
        self.setLayout(self._layout)
        self._values = list(tup)
        self._layout.setContentsMargins(2, 2, 2, 2)
        self._setters = []
        for i, val in enumerate(tup):
            stuff = val_to_widget(val)
            if not stuff:
                continue
            widg, signal, getter, setter = stuff
            signal.connect(self.set_param(i, getter, type(val)))
            self._layout.addWidget(widg)
            self._setters.append(setter)

    def set_param(self, i, getter, dtype):
        """ update the parameter dict when the widg has changed """
        def func():
            self._values[i] = dtype(getter())
            self.valueChanged.emit()
        return func

    def value(self):
        return tuple(self._values)

    def setValue(self, value):
        if not (isinstance(value, (list, tuple)) and
                len(value) == self._layout.count()):
            raise ValueError('invalid arugment length to set TupleWidgetFrame')
        for i, v in enumerate(value):
            self._setters[i](v)


def val_to_widget(val, key=None):
    """ helper function for ImpFrame, to generate a widget that works for
    a given value type.

    Returns a tuple:
        widg: the widget object itself
        signal: the signal to listen for when the object has changed
        getter: the getter function to retrieve the object value
    """
    dtype = type(val)
    if dtype == bool:
        widg = QtWidgets.QCheckBox()
        widg.setChecked(val)
        setter = widg.setChecked
        changed = widg.stateChanged
        getter = widg.isChecked
    elif dtype == int:
        widg = NoScrollSpin(val)
        setter = widg.setValue
        changed = widg.valueChanged
        getter = widg.value
    elif dtype == float:
        widg = NoScrollDoubleSpin(val)
        setter = widg.setValue
        changed = widg.valueChanged
        getter = widg.value
    elif dtype == str:
        # 'file' is a special value that will create a browse button
        if val == 'dir' or 'dir' in key:
            widg = DirDialogLineEdit(val if val != 'dir' else '')
        elif val == 'file' or 'file' in key or val == '':
            widg = FileDialogLineEdit(val if val != 'file' else '')
            # 'path' is a special value: browse button only accepts directories
        else:
            widg = QtWidgets.QLineEdit(str(val))
        setter = widg.setText
        changed = widg.textChanged
        getter = widg.text
    elif isinstance(val, Enum):
        widg = QtWidgets.QComboBox()
        [widg.addItem(option.value) for option in val.__class__]
        widg.setCurrentText(val.value)
        setter = widg.setCurrentText
        changed = widg.currentTextChanged
        getter = widg.currentText
    elif isinstance(val, (tuple, list)):
        widg = TupleWidgetFrame(val)
        setter = widg.setValue
        changed = widg.valueChanged
        getter = widg.value
    else:
        return None
    return widg, changed, getter, setter


def wait_for_file_close(file, delay=0.05):
    s_now = 0
    while True:
        # check to see if the file is the same size as it was 30 ms ago
        # if so... we assume it is done being written
        s_last = s_now
        try:
            s_now = os.path.getsize(file)
            if s_now == s_last and s_now > 0:
                break
        except FileNotFoundError:
            print("WARNING: watched file disappeared: " + file)
            return
        time.sleep(delay)
    return


def wait_for_folder_finished(path, delay=0.1):
    size_now = 0
    while True:
        # check to see if the file is the same size as it was 30 ms ago
        # if so... we assume it is done being written
        size_last = size_now
        size_now = sum(os.path.getsize(f) for f in os.listdir(path) if os.path.isfile(f))
        if size_now == size_last and size_now > 0:
            break
        time.sleep(delay)
    return


def byteArrayToString(bytearr):
    if sys.version_info.major < 3:
        return str(bytearr)
    else:
        return str(bytearr, encoding='utf-8')


def shortname(path, parents=2):
    return os.path.sep.join(os.path.normpath(path).split(os.path.sep)[-parents:])


def camel_case_split(identifier):
    """ split CamelCaseWord into Camel Case Word """
    matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)',
                          identifier)
    return " ".join([m.group(0) for m in matches])


def string_to_iterable(string):
    """convert a string into an iterable
    note: ranges are inclusive

    >>> string_to_iterable('0,3,5-10,15-30-3,40')
    [0,3,5,6,7,8,9,10,15,18,21,24,27,30,40]
    """
    if re.search('[^\d^,^-]', string) is not None:
        raise ValueError('Iterable string must contain only digits, commas, and dashes')
    it = []
    splits = [tuple(s.split('-')) for s in string.split(',')]
    for item in splits:
        if len(item) == 1:
            it.append(int(item[0]))
        elif len(item) == 2:
            it.extend(list(range(int(item[0]), int(item[1]) + 1)))
        elif len(item) == 3:
            it.extend(list(range(int(item[0]), int(item[1]) + 1, int(item[2]))))
        else:
            raise ValueError("Iterable string items must be of length <= 3")
    return sorted(list(set(it)))


def getter_setter_onchange(widget):
    getter, setter, change = (None, None, None)
    if isinstance(widget, QtWidgets.QComboBox):
        getter = widget.currentText
        setter = widget.setCurrentText
        change = widget.currentTextChanged  # (str)
    elif isinstance(widget, QtWidgets.QStatusBar):
        getter = widget.currentMessage
        setter = widget.showMessage
        change = widget.messageChanged  # (str)
    elif isinstance(widget, QtWidgets.QLineEdit):
        getter = widget.text
        setter = widget.setText
        change = widget.textChanged  # (str)
    elif isinstance(widget, (QtWidgets.QAbstractButton, QtWidgets.QGroupBox)):
        getter = widget.isChecked
        setter = widget.setChecked
        change = widget.toggled  # (bool checked)
    elif isinstance(widget, QtWidgets.QDateTimeEdit):
        getter = widget.dateTime
        setter = widget.setDateTime
        change = widget.dateTimeChanged  # (&datetime)
    elif isinstance(widget, (QtWidgets.QAbstractSpinBox, QtWidgets.QAbstractSlider)):
        getter = widget.value
        setter = widget.setValue
        change = widget.valueChanged  # (number)
    elif isinstance(widget, QtWidgets.QTabWidget):
        getter = widget.currentIndex
        setter = widget.setCurrentIndex
        change = widget.currentChanged  # (number)
    elif isinstance(widget, QtWidgets.QSplitter):
        getter = widget.sizes
        setter = widget.setSizes  # (list)
        change = widget.splitterMoved  # (int, int)
    return getter, setter, change


def reveal(path):
    proc = QtCore.QProcess()
    if sys.platform.startswith('darwin'):
        proc.startDetached('open', ['--', path])
    elif sys.platform.startswith('linux'):
        proc.startDetached('xdg-open', ['--', path])
    elif sys.platform.startswith('win32'):
        proc.startDetached('explorer', [path.replace('/', '\\')])


