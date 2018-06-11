from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets as QtW
from llspy import util, llsdir
from llspy.gui.helpers import shortname
import logging
import llspy.gui.exceptions as err
from os import path as osp
logger = logging.getLogger(__name__)

sessionSettings = QtCore.QSettings("llspy", "llspyGUI")


class LLSDragDropTable(QtW.QTableWidget):
    colHeaders = ['path', 'name', 'nC', 'nT', 'nZ', 'nY', 'nX', 'angle', 'dz', 'dx']
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
        self.setEditTriggers(QtW.QAbstractItemView.DoubleClicked)
        self.setGridStyle(3)  # dotted grid line
        self.llsObjects = {}  # dict to hold LLSdir Objects when instantiated

        self.setHorizontalHeaderLabels(self.colHeaders)
        self.hideColumn(0)  # column 0 is a hidden col for the full pathname
        header = self.horizontalHeader()
        header.setSectionResizeMode(1, QtW.QHeaderView.Stretch)
        header.resizeSection(2, 27)
        header.resizeSection(3, 45)
        header.resizeSection(4, 40)
        header.resizeSection(5, 40)
        header.resizeSection(6, 40)
        header.resizeSection(7, 40)
        header.resizeSection(8, 48)
        header.resizeSection(9, 48)
        self.cellChanged.connect(self.onCellChanged)

    @QtCore.pyqtSlot(int, int)
    def onCellChanged(self, row, col):
        # if it's not one of the last few columns that changed, ignore
        if col < 7:
            return
        # must be the ACTIVE column that changed...
        if col == self.currentColumn():
            self.cellChanged.disconnect(self.onCellChanged)
            try:
                val = float(self.currentItem().text())
            except ValueError:
                self.currentItem().setText('0.0')
                raise err.InvalidSettingsError('Value entered was not a number')
            try:
                if col == 7:
                    if not (-90 < val < 90):
                        self.currentItem().setText('0.0')
                        raise err.InvalidSettingsError('angle must be between -90 and 90')
                    self.getLLSObjectByIndex(row).params['angle'] = val
                if col == 8:
                    if not (0 < val < 20):
                        self.currentItem().setText('0.0')
                        raise err.InvalidSettingsError('dz must be between 0 and 20 (microns)')
                    self.getLLSObjectByIndex(row).params['dz'] = val
                if col == 9:
                    if not (0 < val < 5):
                        self.currentItem().setText('0.0')
                        raise err.InvalidSettingsError('dx must be between 0 and 5 (microns)')
                    self.getLLSObjectByIndex(row).params['dx'] = val
                # change color once updated
            finally:
                if ((col == 7 and not (-90 < val < 90)) or
                        (col == 8 and not (0 < val < 20)) or
                        (col == 9 and not (0 < val < 5))):
                    self.currentItem().setForeground(QtCore.Qt.white)
                    self.currentItem().setBackground(QtCore.Qt.red)
                else:
                    self.currentItem().setForeground(QtCore.Qt.black)
                    self.currentItem().setBackground(QtCore.Qt.white)
                self.cellChanged.connect(self.onCellChanged)

    @QtCore.pyqtSlot(str)
    def addPath(self, path):
        try:
            self.cellChanged.disconnect(self.onCellChanged)
        except TypeError:
            pass
        if not (osp.exists(path) and osp.isdir(path)):
            return

        # FIXMEL bad reference method
        mainGUI = self.parent().parent().parent().parent().parent().parent()
        # If this folder is not on the list yet, add it to the list:
        if not util.pathHasPattern(path, '*Settings.txt'):
            if not mainGUI.allowNoSettingsCheckBox.isChecked():
                logger.warning('No Settings.txt! Ignoring: {}'.format(path))
                return

        # if it's already on the list, don't add it
        if len(self.findItems(path, QtCore.Qt.MatchExactly)):
            return

        # if it's a folder containing files with "_Iter_"  warn the user...
        if util.pathHasPattern(path, '*Iter_*'):
            if sessionSettings.value('warnIterFolder', True, type=bool):
                box = QtW.QMessageBox()
                box.setWindowTitle('Note')
                box.setText('You have added a folder that appears to have been acquired'
                            ' in Script Editor: it has "Iter_" in the filenames.\n\n'
                            'LLSpy generally assumes that each folder contains '
                            'a single position timelapse dataset (see docs for assumptions '
                            'about data format).  Hit PROCESS ANYWAY to process this folder as is, '
                            'but it may yield unexpected results. You may also RENAME ITERS, '
                            'this will RENAME all files as if they were single experiments '
                            'acquired at different positions and place them into their own '
                            'folders (cannot be undone). Hit CANCEL to prevent adding this '
                            'item to the queue.')
                box.setIcon(QtW.QMessageBox.Warning)
                box.addButton(QtW.QMessageBox.Cancel)
                box.addButton("Process Anyway", QtW.QMessageBox.YesRole)
                box.addButton("Rename Iters", QtW.QMessageBox.ActionRole)
                box.setDefaultButton(QtW.QMessageBox.Cancel)
                # pref = QtW.QCheckBox("Remember my answer")
                # box.setCheckBox(pref)

                reply = box.exec_()

                if reply > 1000:  # cancel hit
                    return
                elif reply == 1:  # rename iters hit
                    if not hasattr(self, 'renamedPaths'):
                        self.renamedPaths = []
                    newfolders = llsdir.rename_iters(path)
                    self.renamedPaths.append(path)
                    # self.removePath(path)
                    [self.addPath(osp.join(path, p)) for p in newfolders]
                    return
                elif reply == 0:  # process anyway hit
                    pass

        E = llsdir.LLSdir(path)
        logger.info('Adding to queue: %s' % shortname(path))

        rowPosition = self.rowCount()
        self.insertRow(rowPosition)
        item = [path,
                shortname(str(E.path)),
                str(E.params.nc),
                str(E.params.nt),
                str(E.params.nz),
                str(E.params.ny),
                str(E.params.nx),
                "{:2.1f}".format(E.params.get('deskew') or mainGUI.defaultAngleSpin.value()),
                "{:0.3f}".format(E.params.get('dz') or mainGUI.defaultDzSpin.value()),
                "{:0.3f}".format(E.params.get('dx') or mainGUI.defaultDxSpin.value())]
        for col, elem in enumerate(item):
            entry = QtW.QTableWidgetItem(elem)
            if col < 7:
                entry.setFlags(QtCore.Qt.ItemIsSelectable |
                               QtCore.Qt.ItemIsEnabled)
            else:
                entry.setFlags(QtCore.Qt.ItemIsSelectable |
                               QtCore.Qt.ItemIsEnabled |
                               QtCore.Qt.ItemIsEditable)
                if not E.settings:
                    faintRed = QtGui.QBrush(QtGui.QColor(255, 0, 0, 30))
                    lightGray = QtGui.QBrush(QtGui.QColor(160, 160, 160))
                    entry.setForeground(lightGray)
                    entry.setBackground(faintRed)
            self.setItem(rowPosition, col, entry)
            if col > 7 and float(elem) == 0:
                entry.setForeground(QtCore.Qt.white)
                entry.setBackground(QtCore.Qt.red)
        self.llsObjects[path] = E
        self.cellChanged.connect(self.onCellChanged)

    def selectedPaths(self):
        selectedRows = self.selectionModel().selectedRows()
        return [self.getPathByIndex(i.row()) for i in selectedRows]

    def selectedObjects(self):
        return [self.getLLSObjectByPath(p) for p in self.selectedPaths()]

    @QtCore.pyqtSlot(str)
    def removePath(self, path):
        try:
            self.llsObjects.pop(path)
        except KeyError:
            logger.warning('Could not remove path {} ... not in queue'.format(path))
            return
        items = self.findItems(path, QtCore.Qt.MatchExactly)
        for item in items:
            self.removeRow(item.row())
        if hasattr(self, 'skipped_items'):
            if path in self.skipped_items:
                self.skipped_items.remove(path)

    def getPathByIndex(self, index):
        return self.item(index, 0).text()

    def getLLSObjectByPath(self, path):
        return self.llsObjects[path]

    def getLLSObjectByIndex(self, index):
        return self.llsObjects[self.getPathByIndex(index)]

    def setRowBackgroudColor(self, row, color):
        try:
            self.cellChanged.disconnect(self.onCellChanged)
        except TypeError:
            pass
        if isinstance(color, QtGui.QColor):
            brush = QtGui.QBrush(color)
        else:
            brush = QtGui.QBrush(QtGui.QColor(color))
        for col in range(self.nCOLS):
            self.item(row, col).setBackground(brush)
            if col > 7 and float(self.item(row, col).text()) == 0:
                self.item(row, col).setForeground(QtCore.Qt.white)
                self.item(row, col).setBackground(QtCore.Qt.red)
        self.cellChanged.connect(self.onCellChanged)

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
            #   self.listbox.addPath(url)
        else:
            event.ignore()

    def keyPressEvent(self, event):
        super(LLSDragDropTable, self).keyPressEvent(event)
        if (event.key() == QtCore.Qt.Key_Delete or event.key() == QtCore.Qt.Key_Backspace):
            indices = self.selectionModel().selectedRows()
            i = 0
            for index in sorted(indices):
                removerow = index.row() - i
                path = self.getPathByIndex(removerow)
                logger.info('Removing from queue: %s' % shortname(path))
                self.removePath(path)
                i += 1
