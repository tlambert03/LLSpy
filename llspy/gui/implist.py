from PyQt5 import QtCore, QtGui, QtWidgets, uic
import sys
import os
import inspect
from enum import Enum
from llspy import imgprocessors as imgp


Ui_ImpFrame = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'frame.ui'))[0]


class IgnoreWheel(QtCore.QObject):
    """ mixin to prevent mouse wheel from changing spinboxes """
    def __init__(self, val=None, *args, **kwargs):
        super(IgnoreWheel, self).__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        if val is not None:
            self.setValue(val)

    def wheelEvent(self, event):
        event.ignore()


class NoScrollSpin(QtWidgets.QSpinBox, IgnoreWheel):
    pass


class NoScrollDoubleSpin(QtWidgets.QDoubleSpinBox, IgnoreWheel):
    pass


class ImpFrame(QtWidgets.QFrame, Ui_ImpFrame):
    """ Class for each image processor in the ImpList

    builds a gui from the ImgProcessor class __init__ default params
    """
    stateChanged = QtCore.pyqtSignal()

    def __init__(self, proc, parent=None, collapsed=True,
                 *args, **kwargs):
        super(ImpFrame, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.proc = proc
        self.listWidgetItem = parent
        self.is_collapsed = collapsed
        self.parameters = {}  # to store widget state
        self.content.setVisible(not self.is_collapsed)
        if hasattr(proc, 'verbose_name'):
            # look for class attribute first...
            self.title.setText(proc.verbose_name)
        else:
            # get title form name of ImgProcessor Class
            self.title.setText(proc.__name__)

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
        self.buildFrame()

    def buildFrame(self):
        ''' create an input widget for each item in the class __init__ signature '''
        sig = inspect.signature(self.proc)
        self.parameters = {key: (None if val.default == inspect._empty
                                 else val.default)
                           for key, val in sig.parameters.items()}
        for i, (key, val) in enumerate(self.parameters.items()):
            dtype = type(val)
            if dtype == bool:
                widg = QtWidgets.QCheckBox()
                widg.stateChanged.connect(self.set_param(widg, key, dtype))
            elif dtype == int:
                widg = NoScrollSpin(val)
                widg.valueChanged.connect(self.set_param(widg, key, dtype))
            elif dtype == float:
                widg = NoScrollDoubleSpin(val)
                widg.valueChanged.connect(self.set_param(widg, key, dtype))
            elif dtype == str:
                widg = QtWidgets.QLineEdit(str(val))
                widg.textChanged.connect(self.set_param(widg, key, dtype))
            elif isinstance(val, Enum):
                widg = QtWidgets.QComboBox()
                [widg.addItem(option.value) for option in val.__class__]
                widg.setCurrentText(val.value)
                widg.currentTextChanged.connect(self.set_param(widg, key, dtype))
            else:
                continue

            # look for gui_layout class attribute
            if hasattr(self.proc, 'gui_layout'):
                if key not in self.proc.gui_layout:
                    raise KeyError('All parameters must be represented when '
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

        self.contentLayout.setColumnStretch(self.contentLayout.columnCount() - 1, 1)
        self.contentLayout.setColumnMinimumWidth(0, 115)

    def removeItemFromList(self):
        implistwidget = self.parent().parent()
        implistwidget.takeItem(implistwidget.row(self.listWidgetItem))

    def toggleCollapsed(self):
        self.content.setVisible(self.is_collapsed)
        self.is_collapsed = not self.is_collapsed
        self.arrow.setArrow(self.is_collapsed)
        self.listWidgetItem.setSizeHint(self.sizeHint())

    def set_param(self, widg, key, dtype):
        def func():
            try:
                value = widg.checkState() != 0  # for checkbox
            except AttributeError:
                try:
                    value = widg.text()  # for line edit
                except AttributeError:
                    value = widg.currentText()  # for combo
            self.parameters[key] = dtype(value)
            print(self.parameters)
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

    def addImp(self, imp):
        assert issubclass(imp, imgp.ImgProcessor), 'Not an image processor'
        item = QtWidgets.QListWidgetItem(self)
        widg = ImpFrame(imp, parent=item)
        item.setSizeHint(widg.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widg)
        self.setMinimumWidth(self.sizeHintForColumn(0))
        self.get_imp_params()

    def get_imp_params(self):
        items = []
        for index in range(self.count()):
            imp = self.itemWidget(self.item(index))
            items.append((imp.proc, imp.parameters))
        return items

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
        lay = QtWidgets.QVBoxLayout()
        self.addProcessorButton = QtWidgets.QPushButton('Add Processor')
        self.addProcessorButton.clicked.connect(self.selectImgProcessor)
        self.setLayout(lay)
        self.list = ImpListWidget()
        lay.addWidget(self.list)
        lay.addWidget(self.addProcessorButton)
        lay.setContentsMargins(0, 4, 0, 0)

    def selectImgProcessor(self):
        d = ImgProcessSelector()
        d.selected.connect(self.list.addImp)
        d.exec_()


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
            try:
                if issubclass(obj, imgp.ImgProcessor):
                    self.D[name] = obj
                    itemN = QtWidgets.QListWidgetItem(name)
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
    for imp in (imgp.CUDADeconProcessor, imgp.SelectiveMedianProcessor,
                imgp.FlashProcessor, imgp.BleachCorrectionProcessor):
        container.list.addImp(imp)
    container.show()
    sys.exit(APP.exec_())
