from PyQt5 import QtCore, QtWidgets
import time
import os
import sys
import re
import logging
import inspect


# TODO: add timer?
def newWorkerThread(workerClass, *args, **kwargs):
    worker = workerClass(*args, **kwargs)
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


def guisave(widget, settings):
    print("Saving settings: {}".format(settings.fileName()))
    # Save geometry
    selfName = widget.objectName()
    settings.setValue(selfName + '_size', widget.size())
    settings.setValue(selfName + '_pos', widget.pos())
    for name, obj in inspect.getmembers(widget):
        # if type(obj) is QComboBox:  # this works similar to isinstance, but missed some field... not sure why?
        value = None
        if isinstance(obj, QtWidgets.QComboBox):
            index = obj.currentIndex()  # get current index from combobox
            value = obj.itemText(index)  # get the text for current index
        if isinstance(obj, QtWidgets.QLineEdit):
            value = obj.text()
        if isinstance(obj,
                      (QtWidgets.QCheckBox, QtWidgets.QRadioButton, QtWidgets.QGroupBox)):
            value = obj.isChecked()
        if isinstance(obj, (QtWidgets.QSpinBox, QtWidgets.QSlider)):
            value = obj.value()
        if value is not None:
            settings.setValue(name, value)
    settings.sync()  # required in some cases to write settings before quit


def guirestore(widget, settings, default):
    print("Restoring settings: {}".format(settings.fileName()))
    # Restore geometry
    selfName = widget.objectName()
    if 'LLSpyDefaults' not in settings.fileName():
        widget.resize(settings.value(selfName + '_size', QtCore.QSize(500, 500)))
        widget.move(settings.value(selfName + '_pos', QtCore.QPoint(60, 60)))
    for name, obj in inspect.getmembers(widget):
        try:
            if isinstance(obj, QtWidgets.QComboBox):
                value = settings.value(name, default.value(name), type=str)
                if value == "":
                    continue
                index = obj.findText(value)  # get the corresponding index for specified string in combobox
                if index == -1:  # add to list if not found
                    obj.insertItems(0, [value])
                    index = obj.findText(value)
                    obj.setCurrentIndex(index)
                else:
                    obj.setCurrentIndex(index)
            if isinstance(obj, QtWidgets.QLineEdit):
                value = settings.value(name, default.value(name), type=str)
                obj.setText(value)
            if isinstance(obj,
                          (QtWidgets.QCheckBox, QtWidgets.QRadioButton, QtWidgets.QGroupBox)):
                value = settings.value(name, default.value(name), type=bool)
                if value is not None:
                    obj.setChecked(value)
            if isinstance(obj, (QtWidgets.QSlider, QtWidgets.QSpinBox)):
                value = settings.value(name, default.value(name), type=int)
                if value is not None:
                    obj.setValue(value)
            if isinstance(obj, (QtWidgets.QDoubleSpinBox,)):
                value = settings.value(name, default.value(name), type=float)
                if value is not None:
                    obj.setValue(value)
        except Exception:
            logging.warn('Unable to restore settings for object: {}'.format(name))

