from PyQt5 import QtCore, QtGui, QtWidgets, uic
import sys
import os
import inspect
from click import get_app_dir
from re import finditer
from enum import Enum
from llspy import imgprocessors as imgp
from llspy import __appname__

framepath = os.path.join(os.path.dirname(__file__), 'frame.ui')
Ui_ImpFrame = uic.loadUiType(framepath)[0]
PLAN_DIR = os.path.join(get_app_dir(__appname__), 'process_plans')


def camel_case_split(identifier):
    """ split CamelCaseWord into Camel Case Word """
    matches = finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
    return " ".join([m.group(0) for m in matches])


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
        signal = widg.stateChanged
        getter = widg.isChecked
    elif dtype == int:
        widg = NoScrollSpin(val)
        signal = widg.valueChanged
        getter = widg.value
    elif dtype == float:
        widg = NoScrollDoubleSpin(val)
        signal = widg.valueChanged
        getter = widg.value
    elif dtype == str:
        # 'file' is a special value that will create a browse button
        if val == 'file' or 'file' in key or val == '':
            widg = FileDialogLineEdit(val if val != 'file' else '')
        # 'path' is a special value: browse button only accepts directories
        elif val == 'dir' or 'dir' in key:
            widg = DirDialogLineEdit(val if val != 'dir' else '')
        else:
            widg = QtWidgets.QLineEdit(str(val))
        signal = widg.textChanged
        getter = widg.text
    elif isinstance(val, Enum):
        widg = QtWidgets.QComboBox()
        [widg.addItem(option.value) for option in val.__class__]
        widg.setCurrentText(val.value)
        signal = widg.currentTextChanged
        getter = widg.currentText
    elif isinstance(val, (tuple, list)):
        widg = TupleWidgetFrame(val)
        signal = widg.valueChanged
        getter = widg.value
    else:
        return None
    return widg, signal, getter


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
            self.textChanged.emit()

    def text(self):
        return self._lineEdit.text()


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
        for i, val in enumerate(tup):
            stuff = val_to_widget(val)
            if not stuff:
                continue
            widg, signal, getter = stuff
            signal.connect(self.set_param(i, getter, type(val)))
            self._layout.addWidget(widg)

    def set_param(self, i, getter, dtype):
        """ update the parameter dict when the widg has changed """
        def func():
            self._values[i] = dtype(getter())
            self.valueChanged.emit()
        return func

    def value(self):
        return tuple(self._values)


class ImpFrame(QtWidgets.QFrame, Ui_ImpFrame):
    """ Class for each image processor in the ImpList

    builds a gui from the ImgProcessor class __init__ default params
    """
    stateChanged = QtCore.pyqtSignal()

    def __init__(self, proc, parent=None, collapsed=False, initial={},
                 active=True, *args, **kwargs):
        super(ImpFrame, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.proc = proc
        self.listWidgetItem = parent
        self.is_collapsed = collapsed
        if not active:
            self.activeBox.setChecked(False)
        self.parameters = {}  # to store widget state
        self.content.setVisible(not self.is_collapsed)
        if hasattr(proc, 'verbose_name'):
            # look for class attribute first...
            self.title.setText(proc.verbose_name)
        else:
            # get title form name of ImgProcessor Class
            self.title.setText(camel_case_split(proc.__name__))

        # arrow to collapse frame
        self.arrow = self.Arrow(self.arrowFrame, collapsed=collapsed)
        self.arrow.clicked.connect(self.toggleCollapsed)

        # close button
        self.closeButton = QtWidgets.QPushButton()
        self.closeButton.setFlat(True)
        self.closeButton.setObjectName('closeButton')
        self.closeButton.setText('×')
        self.closeButton.clicked.connect(self.removeItemFromList)
        self.titleLayout.addWidget(self.closeButton)
        self.buildFrame(initial)

    def buildFrame(self, initial={}):
        ''' create an input widget for each item in the class __init__ signature '''

        sig = inspect.signature(self.proc)
        self.parameters = {key: (None if val.default == inspect._empty
                                 else val.default)
                           for key, val in sig.parameters.items()}
        self.parameters.update(initial)
        for i, (key, val) in enumerate(self.parameters.items()):
            stuff = val_to_widget(val, key)
            if not stuff:
                continue
            widg, signal, getter = stuff
            signal.connect(self.set_param(key, getter, type(val)))

            # look for gui_layout class attribute
            if hasattr(self.proc, 'gui_layout'):
                if key not in self.proc.gui_layout:
                    raise self.proc.ImgProcessorInvalid(
                        'All parameters must be represented when '
                        'using gui_layout.  Missing key: "{}".'
                        .format(key))
                layout = self.proc.gui_layout[key]
                row, col = layout
                label_index = (row, col * 2)
                widget_index = (row, col * 2 + 1)
            else:
                label_index = (i, 0)
                widget_index = (i, 1)
            label = QtWidgets.QLabel(key.replace('_', ' ').title())
            self.contentLayout.addWidget(label, *label_index)
            self.contentLayout.addWidget(widg, *widget_index)

        doc = inspect.getdoc(self.proc)
        if 'guidoc' in doc:
            docstring = doc.split('guidoc:')[1].split('\n')[0].strip()
            doclabel = QtWidgets.QLabel(docstring)
            doclabel.setStyleSheet('font-style: italic; color: #777;')
            self.contentLayout.addWidget(doclabel, self.contentLayout.rowCount(), 0, 1, self.contentLayout.columnCount())

        self.contentLayout.setColumnStretch(self.contentLayout.columnCount() - 1, 1)
        self.contentLayout.setColumnMinimumWidth(0, 90)

    def removeItemFromList(self):
        implistwidget = self.parent().parent()
        implistwidget.takeItem(implistwidget.row(self.listWidgetItem))

    def toggleCollapsed(self):
        self.content.setVisible(self.is_collapsed)
        self.is_collapsed = not self.is_collapsed
        self.arrow.setArrow(self.is_collapsed)
        self.listWidgetItem.setSizeHint(self.sizeHint())

    def set_param(self, key, getter, dtype):
        """ update the parameter dict when the widg has changed """
        def func():
            self.parameters[key] = dtype(getter())
            self.stateChanged.emit()
        return func

    class Arrow(QtWidgets.QFrame):
        """ small arrow to collapse/expand the frame details """
        clicked = QtCore.pyqtSignal()

        def __init__(self, parent=None, collapsed=False):
            super(ImpFrame.Arrow, self).__init__(parent=parent)
            self.setArrow(collapsed)

        def setArrow(self, collapsed):
            v = 2
            if collapsed:  # horizontal
                self._arrow = (QtCore.QPointF(8, 5 + v),
                               QtCore.QPointF(13, 10 + v),
                               QtCore.QPointF(8, 15 + v))
            else:  # vertical
                self._arrow = (QtCore.QPointF(7, 7 + v),
                               QtCore.QPointF(17, 7 + v),
                               QtCore.QPointF(12, 12 + v))
            self.update()

        def paintEvent(self, event):
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setBrush(QtGui.QColor(0, 0, 0))
            painter.setPen(QtGui.QColor(0, 0, 0))
            painter.drawPolygon(*self._arrow)
            painter.end()

        def mousePressEvent(self, event):
            self.clicked.emit()
            return super(ImpFrame.Arrow, self).mousePressEvent(event)


class ImpListWidget(QtWidgets.QListWidget):
    """ The full list of image processors.

    ultimately, this members list will be used to determine what
    processing is done to the data
    """
    def __init__(self, imps=[], *args, **kwargs):
        super(ImpListWidget, self).__init__(*args, **kwargs)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setDragEnabled(True)
        self.setDragDropMode(self.InternalMove)
        self.setAcceptDrops(True)
        self.setSpacing(1)
        self.setMinimumHeight(1)

        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                           QtWidgets.QSizePolicy.MinimumExpanding)
        for imp in imps:
            self.addImp(imp)

    def addImp(self, imp, **kwargs):
        assert issubclass(imp, imgp.ImgProcessor), 'Not an image processor'
        item = QtWidgets.QListWidgetItem(self)
        widg = ImpFrame(imp, parent=item, **kwargs)
        item.setSizeHint(widg.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widg)
        self.setMinimumWidth(self.sizeHintForColumn(0))

    def getImpList(self):
        items = []
        for index in range(self.count()):
            imp = self.itemWidget(self.item(index))
            items.append((imp.proc, imp.parameters,
                          imp.activeBox.isChecked(), imp.is_collapsed))
        return items

    def setImpList(self, implist):
        self.clear()
        for imp, params, active, collapsed in implist:
            self.addImp(imp, initial=params, active=active, collapsed=collapsed)

    # def startDrag(self, supportedActions):
    #     # drag_item = self.currentItem()
    #     # drag = QtGui.QDrag(self)
    #     # dragMimeData = QtCore.QMimeData()
    #     # drag.setMimeData(dragMimeData)
    #     # drag.setPixmap(self.itemWidget(drag_item).grab())
    #     # drag.setHotSpot(self._mouse_pos)
    #     # drag.exec_()
    #     super(ImpListWidget, self).startDrag(supportedActions)


class ImpListContainer(QtWidgets.QWidget):
    """ Just a container for the listWidget and the buttons """
    def __init__(self, *args, **kwargs):
        super(ImpListContainer, self).__init__(*args, **kwargs)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.list = ImpListWidget()
        self.addProcessorButton = QtWidgets.QPushButton('Add Processor')
        self.addProcessorButton.clicked.connect(self.selectImgProcessor)
        self.savePlanButton = QtWidgets.QPushButton('Save Plan')
        self.savePlanButton.clicked.connect(self.savePlan)
        self.loadPlanButton = QtWidgets.QPushButton('Load Plan')
        self.loadPlanButton.clicked.connect(self.loadPlan)
        buttonBox = QtWidgets.QFrame()
        buttonBox.setLayout(QtWidgets.QHBoxLayout())
        buttonBox.layout().setContentsMargins(0, 0, 0, 0)
        buttonBox.layout().addWidget(self.addProcessorButton)
        buttonBox.layout().addWidget(self.savePlanButton)
        buttonBox.layout().addWidget(self.loadPlanButton)
        self.layout().addWidget(self.list)
        self.layout().addWidget(buttonBox)
        self.layout().setContentsMargins(0, 4, 0, 0)

    def selectImgProcessor(self):
        d = ImgProcessSelector()
        d.selected.connect(self.list.addImp)
        d.exec_()

    def savePlan(self):
        import pickle
        if not os.path.exists(PLAN_DIR):
            os.mkdir(PLAN_DIR)
        path = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save Plan', PLAN_DIR, "Plan Files (*.plan)")[0]
        if path is None or path == '':
            return
        with open(path, 'wb') as fout:
            pickle.dump(self.list.getImpList(), fout, pickle.HIGHEST_PROTOCOL)

    def loadPlan(self):
        import pickle
        path = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Choose Plan', PLAN_DIR, "Plan Files (*.plan)")[0]
        if path is None or path == '':
            return
        else:
            try:
                with open(path, 'rb') as infile:
                    plan = pickle.load(infile)
            except Exception:
                plan = None
        if plan:
            self.list.setImpList(plan)


class ImgProcessSelector(QtWidgets.QDialog):
    """ Popup dialog to select new widgets to add to the list

    will search llspy.imgprocessors by default, will add plugins later
    """
    selected = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super(ImgProcessSelector, self).__init__(*args, **kwargs)

        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel |
                                          QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        lay = QtWidgets.QVBoxLayout()
        self.setLayout(lay)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowTitle("Select an Image Processor to add")
        self.lstwdg = QtWidgets.QListWidget()
        self.lstwdg.itemDoubleClicked.connect(self.accept)
        self.lstwdg.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.D = {}
        for name, obj in inspect.getmembers(imgp):
            if hasattr(obj, 'verbose_name'):
                # look for class attribute first...
                name = obj.verbose_name
            try:
                if (issubclass(obj, imgp.ImgProcessor) and not
                        inspect.isabstract(obj)):
                    self.D[camel_case_split(name)] = obj
                    itemN = QtWidgets.QListWidgetItem(camel_case_split(name))
                    self.lstwdg.addItem(itemN)
            except TypeError:
                pass
        lay.addWidget(self.lstwdg)
        lay.addWidget(self.buttonBox)

    def accept(self, *args):
        for item in self.lstwdg.selectedItems():
            self.selected.emit(self.D[item.text()])
        return super(ImgProcessSelector, self).accept()


if __name__ == '__main__':
    APP = QtWidgets.QApplication([])
    container = ImpListContainer()
    for imp in (imgp.CUDADeconProcessor, imgp.FlashProcessor):
        container.list.addImp(imp)
    container.show()
    a = container.list.getImpList()
    container.list.setImpList(a)
    sys.exit(APP.exec_())
