import sys
import os
import logging
import inspect
import pickle
from click import get_app_dir
from llspy import __appname__, ImgProcessor, ImgWriter, imgprocessors
from llspy.gui.helpers import camel_case_split, val_to_widget
from PyQt5 import QtCore, QtGui, QtWidgets, uic

SETTINGS  = QtCore.QSettings()

logger = logging.getLogger(__name__)
framepath = os.path.join(os.path.dirname(__file__), 'frame.ui')
Ui_ImpFrame = uic.loadUiType(framepath)[0]
IMP_DIR = os.path.join(get_app_dir(__appname__), 'plugins')
if os.path.exists(IMP_DIR):
    if IMP_DIR not in sys.path:
        sys.path.insert(0, IMP_DIR)
    for fname in os.listdir(IMP_DIR):
        if fname.endswith('.py'):
            try:
                __import__(os.path.splitext(fname)[0])
            except Exception as e:
                logger.error('Could not load plugin "{}" due to {}: {}'
                             .format(fname, type(e).__name__, str(e)))
"""
This is the better way to import plugins, but currently i can't pickle
objects that are imported this way... so instead, I add plugins path to
sys.path.  That has the downside of potential namespace conflicts if
someone names a file the same as a builtin
"""
# try:
#     import importlib.util

#     def import_plugin(fullpath, namespace='plugins'):
#         fname = os.path.splitext(os.path.basename(fullpath))[0]
#         mod_name = namespace + '.' + fname
#         spec = importlib.util.spec_from_file_location(mod_name, fullpath)
#         foo = importlib.util.module_from_spec(spec)
#         spec.loader.exec_module(foo)
#         sys.modules[mod_name] = foo
#         sys.path.append(mod_name)
#         return foo

# except ImportError:
#     import imp

#     def import_plugin(fullpath, namespace='plugins'):
#         fname = os.path.splitext(os.path.basename(fullpath))[0]
#         mod_name = namespace + '.' + fname
#         foo = imp.load_source(mod_name, fullpath)
#         sys.modules[mod_name] = foo
#         return foo


# def import_plugins(folder, namespace='plugins'):
#     if not os.path.exists(folder):
#         return
#     if folder not in sys.path:
#         sys.path.append(folder)
#     for fname in os.listdir(folder):
#         fullpath = os.path.join(folder, fname)
#         try:
#             yield import_plugin(fullpath)
#         except AttributeError:
#             pass


def imp_settings_key(imp, key):
    return 'imps/{}/{}'.format(imp.__name__, key)


class ImpFrame(QtWidgets.QFrame, Ui_ImpFrame):
    """ Class for each image processor in the ImpList

    builds a gui from the ImgProcessor class __init__ default params
    """
    stateChanged = QtCore.pyqtSignal()

    def __init__(self, imp, parent=None, collapsed=False, initial=None,
                 active=True, *args, **kwargs):
        super(ImpFrame, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.imp = imp
        self.listWidgetItem = parent
        self.is_collapsed = collapsed
        if not active:
            self.activeBox.setChecked(False)
        self.parameters = {}  # to store widget state
        self.content.setVisible(not self.is_collapsed)
        self.title.setText(imp.name())
        self.mouseDoubleClickEvent = self.toggleCollapsed
        self.activeBox.toggled.connect(self.stateChanged.emit)
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
        self.buildFrame(initial or {})

    def buildFrame(self, initial):
        ''' create an input widget for each item in the class __init__ signature '''

        sig = inspect.signature(self.imp)
        self.parameters = {key: (None if val.default == inspect._empty
                                 else val.default)
                           for key, val in sig.parameters.items()}
        for key in self.parameters:
            # values provided in initial take priority
            if key in initial:
                self.parameters[key] = initial[key]
            # otherwise use any previously used value
            elif SETTINGS.contains(imp_settings_key(self.imp, key)):
                self.parameters[key] = SETTINGS.value(imp_settings_key(self.imp, key))
        for i, (key, val) in enumerate(self.parameters.items()):
            stuff = val_to_widget(val, key)
            if not stuff:
                continue
            widg, signal, getter, setter = stuff

            if isinstance(val, (int, float)):
                if hasattr(self.imp, 'valid_range'):
                    r = self.imp.valid_range.get(key, [])
                    if len(r) == 2:
                        widg.setRange(*r)
            signal.connect(self.set_param(key, getter, type(val)))

            # look for gui_layout class attribute
            if hasattr(self.imp, 'gui_layout'):
                if key not in self.imp.gui_layout:
                    raise self.imp.ImgProcessorInvalid(
                        'Invalid ImgProcessor class: \n\n'
                        'All parameters must be represented when '
                        'using gui_layout.  Missing key: "{}".'
                        .format(key))
                layout = self.imp.gui_layout[key]
                row, col = layout
                label_index = (row, col * 2)
                widget_index = (row, col * 2 + 1)
            else:
                label_index = (i, 0)
                widget_index = (i, 1)
            label = QtWidgets.QLabel(key.replace('_', ' ').title())
            self.contentLayout.addWidget(label, *label_index)
            self.contentLayout.addWidget(widg, *widget_index)

        doc = inspect.getdoc(self.imp)
        if 'guidoc' in doc:
            docstring = doc.split('guidoc:')[1].split('\n')[0].strip()
            doclabel = QtWidgets.QLabel(docstring)
            doclabel.setStyleSheet('font-style: italic; color: #777;')
            self.contentLayout.addWidget(
                doclabel, self.contentLayout.rowCount(), 0, 1,
                self.contentLayout.columnCount())

        self.contentLayout.setColumnStretch(
            self.contentLayout.columnCount() - 1, 1)
        self.contentLayout.setColumnMinimumWidth(0, 90)

    def removeItemFromList(self):
        implistwidget = self.parent().parent()
        implistwidget.takeItem(implistwidget.row(self.listWidgetItem))
        self.stateChanged.emit()

    def toggleCollapsed(self, *args):
        self.content.setVisible(self.is_collapsed)
        self.is_collapsed = not self.is_collapsed
        self.arrow.setArrow(self.is_collapsed)
        self.listWidgetItem.setSizeHint(self.sizeHint())
        self.stateChanged.emit()

    def set_param(self, key, getter, dtype):
        """ update the parameter dict when the widg has changed """
        def func():
            self.parameters[key] = dtype(getter())
            self.stateChanged.emit()
            _key = imp_settings_key(self.imp, key)
            SETTINGS.setValue(_key, dtype(getter()))
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
    planChanged = QtCore.pyqtSignal()
    PLAN_DIR = os.path.join(get_app_dir(__appname__), 'process_plans')
    LAST_PLAN = os.path.join(PLAN_DIR, '_lastused.plan')
    DEFAULT = os.path.join(os.path.dirname(__file__), 'default.plan')

    def __init__(self, imps=[], *args, **kwargs):
        super(ImpListWidget, self).__init__(*args, **kwargs)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setDragEnabled(True)
        self.setDragDropMode(self.InternalMove)
        self.setAcceptDrops(True)
        self.setSpacing(1)
        self.setMinimumHeight(1)
        self.planChanged.connect(lambda: self.savePlan(self.LAST_PLAN))
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                           QtWidgets.QSizePolicy.MinimumExpanding)
        if imps:
            for imp in imps:
                self.addImp(imp)
        else:
            self.loadPlan(self.LAST_PLAN)
        if not self.count():
            self.loadPlan(self.DEFAULT)

    def addImp(self, imp, **kwargs):
        assert issubclass(imp, ImgProcessor), 'Not an image processor'
        item = QtWidgets.QListWidgetItem(self)
        widg = ImpFrame(imp, parent=item, **kwargs)
        widg.stateChanged.connect(self.planChanged.emit)
        item.setSizeHint(widg.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widg)
        self.setMinimumWidth(self.sizeHintForColumn(0))
        self.planChanged.emit()

    def getImpList(self):
        items = []
        for index in range(self.count()):
            frame = self.itemWidget(self.item(index))
            items.append((frame.imp, frame.parameters,
                          frame.activeBox.isChecked(), frame.is_collapsed))
        return items

    def setImpList(self, implist):
        self.clear()
        for imp, params, active, collapsed in implist:
            self.addImp(imp, initial=params, active=active, collapsed=collapsed)

    def savePlan(self, path=None):
        if not os.path.exists(self.PLAN_DIR):
            os.mkdir(self.PLAN_DIR)
        if not path:
            path = QtWidgets.QFileDialog.getSaveFileName(
                self, 'Save Plan', self.PLAN_DIR,
                "Plan Files (*.plan)")[0]
        if path is None or path == '':
            return
        with open(path, 'wb') as fout:
            pickle.dump(self.getImpList(), fout, pickle.HIGHEST_PROTOCOL)

    def loadPlan(self, path=None):
        if not path:
            path = QtWidgets.QFileDialog.getOpenFileName(
                self, 'Choose Plan', self.PLAN_DIR,
                "Plan Files (*.plan)")[0]
        if path is None or path == '':
            return
        else:
            try:
                with open(path, 'rb') as infile:
                    plan = pickle.load(infile)
            except Exception:
                plan = None
        if plan:
            self.setImpList(plan)

    def dropEvent(self, *args):
        super(ImpListWidget, self).dropEvent(*args)
        self.savePlan(self.LAST_PLAN)

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
        self.savePlanButton.clicked.connect(self.list.savePlan)
        self.loadPlanButton = QtWidgets.QPushButton('Load Plan')
        self.loadPlanButton.clicked.connect(self.list.loadPlan)
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
        self.d = ImgProcessSelector()
        self.d.selected.connect(self.list.addImp)
        self.d.exec_()


class ImgProcessSelector(QtWidgets.QDialog):
    """ Popup dialog to select new widgets to add to the list

    will search llspy.imgprocessors by default, will add plugins later
    """
    selected = QtCore.pyqtSignal(object)
    import_error = QtCore.pyqtSignal(str, str, str, str)

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
        # add built-in imageprocessors
        self._search_module(imgprocessors)

        # check plugins dir
        # for module in import_plugins(self.IMP_DIR):
        if os.path.exists(IMP_DIR):
            if IMP_DIR not in sys.path:
                sys.path.insert(0, IMP_DIR)
            for fname in os.listdir(IMP_DIR):
                if fname.endswith('.py'):
                    module = __import__(os.path.splitext(fname)[0])
                    self._search_module(module)

        lay.addWidget(self.lstwdg)
        lay.addWidget(self.buttonBox)

    def _search_module(self, module, _raise=False):
        for name, obj in inspect.getmembers(module):
            try:
                self._try_import_imgp(obj)
            except self.PluginImportError as e:
                if _raise:
                    if obj not in (ImgProcessor, ImgWriter):
                        print(e)
                        logger.warning(e)
                        self.import_error.emit(str(e), '', '', '')

    def _try_import_imgp(self, obj):
        try:
            if issubclass(obj, ImgProcessor):
                if inspect.isabstract(obj):
                    raise self.PluginImportError(
                        'Detected an ImgProcessor plugin named "{}", '
                        .format(obj.__name__) +
                        'but could not import. Did you implement the "process" '
                        'method?')
                name = obj.name()  # look for verbose name
                self.D[camel_case_split(name)] = obj
                itemN = QtWidgets.QListWidgetItem(camel_case_split(name))
                self.lstwdg.addItem(itemN)

        except TypeError:
            pass

    def accept(self, *args):
        for item in self.lstwdg.selectedItems():
            self.selected.emit(self.D[item.text()])
        return super(ImgProcessSelector, self).accept()

    class PluginImportError(Exception):
        pass


if __name__ == '__main__':
    APP = QtWidgets.QApplication([])
    container = ImpListContainer()
    container.show()
    a = container.list.getImpList()
    container.list.setImpList(a)
    sys.exit(APP.exec_())
