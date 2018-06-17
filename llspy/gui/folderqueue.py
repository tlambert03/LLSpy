import logging
import llspy.gui.exceptions as err
import os
from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets as QtW
from llspy import util, llsdir, processplan
from llspy.gui.helpers import shortname, newWorkerThread

logger = logging.getLogger(__name__)
sessionSettings = QtCore.QSettings("llspy", "llspyGUI")


class ProcessPlan(processplan.ProcessPlan, QtCore.QObject):
    imp_starting = QtCore.pyqtSignal(object, dict)
    imp_finished = QtCore.pyqtSignal(dict)
    t_finished = QtCore.pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        QtCore.QObject.__init__(self)
        super(ProcessPlan, self).__init__(*args)

    def _preimp(self, imp, meta):
        self.imp_starting.emit(imp, meta)

    def _postimp(self, meta):
        self.imp_finished.emit(meta)

    def _iterimps(self, data, meta):
        for imp in self.imps:
            if self.aborted:
                break
            self.imp_starting.emit(imp, meta)
            data, meta = imp(data, meta)
            self.imp_finished.emit(meta)

    def _execute_t(self, meta, *args):
        super(ProcessPlan, self)._execute_t(meta, *args)
        self.t_finished.emit(meta['t'])

    def abort(self):
        self.aborted = True


class QueueItemWorker(QtCore.QObject):
    work_starting = QtCore.pyqtSignal(int)  # set progressbar maximum
    item_errored = QtCore.pyqtSignal(object)
    finished = QtCore.pyqtSignal()

    def __init__(self, plan, **kwargs):
        super(QueueItemWorker, self).__init__()
        self.plan = plan

    def work(self):
        self.work_starting.emit(len(self.plan.t_range))
        try:
            self.plan.execute()
        except Exception as e:
            self.item_errored.emit(e)
        else:
            self.finished.emit()


class LLSDragDropTable(QtW.QTableWidget):
    col_headers = ['path', 'name', 'nC', 'nT', 'nZ', 'nY', 'nX', 'angle', 'dz', 'dx']
    n_cols = len(col_headers)

    status_update = QtCore.pyqtSignal(str)
    item_starting = QtCore.pyqtSignal(int)
    step_finished = QtCore.pyqtSignal(int)
    work_finished = QtCore.pyqtSignal(int, int, int)  # return_code, numgood, numskipped,
    abort_request = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(LLSDragDropTable, self).__init__(0, self.n_cols, parent)
        self.lls_objects = {}  # dict to hold LLSdir Objects when instantiated
        self.inProcess = False
        self.worker_threads = []
        self.aborted = False

        self.setAcceptDrops(True)
        self.setSelectionMode(QtW.QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QtW.QAbstractItemView.SelectRows)
        self.setEditTriggers(QtW.QAbstractItemView.DoubleClicked)
        self.setGridStyle(3)  # dotted grid line
        self.setHorizontalHeaderLabels(self.col_headers)
        self.hideColumn(0)  # column 0 is a hidden col for the full pathname
        header = self.horizontalHeader()
        header.setSectionResizeMode(1, QtW.QHeaderView.Stretch)
        for t in enumerate((27, 45, 40, 40, 40, 40, 48, 48), 2):
            header.resizeSection(*t)
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
                        raise err.InvalidSettingsError(
                            'angle must be between -90 and 90')
                    self.getLLSObjectByIndex(row).params['angle'] = val
                if col == 8:
                    if not (0 < val < 20):
                        self.currentItem().setText('0.0')
                        raise err.InvalidSettingsError(
                            'dz must be between 0 and 20 (microns)')
                    self.getLLSObjectByIndex(row).params['dz'] = val
                if col == 9:
                    if not (0 < val < 5):
                        self.currentItem().setText('0.0')
                        raise err.InvalidSettingsError(
                            'dx must be between 0 and 5 (microns)')
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
        if not (os.path.exists(path) and os.path.isdir(path)):
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
                box.setText(
                    'You have added a folder that appears to have been acquired'
                    ' in Script Editor: it has "Iter_" in the filenames.\n\n'
                    'LLSpy generally assumes that each folder contains a '
                    'single position timelapse dataset (see docs for '
                    'assumptions about data format).  Hit PROCESS ANYWAY to '
                    'process this folder as is, but it may yield unexpected '
                    'results. You may also RENAME ITERS, this will RENAME all '
                    'files as if they were single experiments acquired at '
                    'different positions and place them into their own folders '
                    '(cannot be undone). Hit CANCEL to prevent adding this '
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
                    [self.addPath(os.path.join(path, p)) for p in newfolders]
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
                str(E.params.nx)]
        for frmt, key, widg in [('{:2.1f}', 'deskew', 'defaultAngleSpin'),
                                ('{:0.3f}', 'dz', 'defaultDzSpin'),
                                ('{:0.3f}', 'dx', 'defaultDxSpin')]:
            val = E.params.get(key)
            if not val:
                val = getattr(mainGUI, widg).value()
                E.params[key if key != 'deskew' else 'angle'] = val
            item.append(frmt.format(val))
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
        self.lls_objects[path] = E
        self.cellChanged.connect(self.onCellChanged)

    def selectedPaths(self):
        selectedRows = self.selectionModel().selectedRows()
        return [self.getPathByIndex(i.row()) for i in selectedRows]

    def selectedObjects(self):
        return [self.getLLSObjectByPath(p) for p in self.selectedPaths()]

    @QtCore.pyqtSlot(str)
    def removePath(self, path):
        try:
            self.lls_objects.pop(path)
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
        return self.lls_objects[path]

    def getLLSObjectByIndex(self, index):
        return self.lls_objects[self.getPathByIndex(index)]

    def setRowBackgroundColor(self, row, color):
        try:
            self.cellChanged.disconnect(self.onCellChanged)
        except TypeError:
            pass
        if isinstance(color, QtGui.QColor):
            brush = QtGui.QBrush(color)
        else:
            brush = QtGui.QBrush(QtGui.QColor(color))
        for col in range(self.n_cols):
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
                self.addPath(str(url.toLocalFile()))
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

    @QtCore.pyqtSlot()
    def startProcessing(self, implist):
        self.currentImps = implist
        self.skipped_items = set()
        self.numProcessed = 0
        if self.rowCount() == 0:
            QtW.QMessageBox.warning(
                self, "Nothing Added!",
                'Nothing to process! Drag and drop folders into the list',
                QtW.QMessageBox.Ok, QtW.QMessageBox.NoButton)
            return

        # for now, only one item allowed processing at a time
        if not self.inProcess:
            self.planNextItem()
        else:
            logger.warning('Ignoring request to process, already processing...')

    def planNextItem(self):
        # get path from first row and create a new LLSdir object
        numskipped = len(self.skipped_items)
        self.currentIndex = self.item(numskipped, 1)
        self.currentPath = self.getPathByIndex(numskipped)
        llsdir = self.getLLSObjectByPath(self.currentPath)

        def skip():
            self.removePath(self.currentPath)
            self.look_for_next_item()
            return

        if not os.path.exists(self.currentPath):
            msg = 'Skipping! path no longer exists: {}'.format(self.currentPath)
            logger.info(msg)
            self.statusBar.showMessage(msg, 5000)
            skip()
            return

        # check if already processed
        # if util.pathHasPattern(self.currentPath, '*' + llspy.config.__OUTPUTLOG__):
        #     if not self.reprocessCheckBox.isChecked():
        #         msg = 'Skipping! Path already processed: {}'.format(self.currentPath)
        #         logger.info(msg)
        #         self.statusBar.showMessage(msg, 5000)
        #         skip()
        #         return

        plan = ProcessPlan(llsdir, self.currentImps)
        try:
            if not self.inProcess:
                plan.plan()  # do sanity check here
            else:
                plan.plan(skip_warnings=True)
        except plan.PlanWarning as e:
            msg = QtW.QMessageBox()
            msg.setIcon(QtW.QMessageBox.Information)
            msg.setText(str(e) + '\n\nContinue anyway?')
            msg.setStandardButtons(QtW.QMessageBox.Ok | QtW.QMessageBox.Cancel)
            if msg.exec_() == QtW.QMessageBox.Ok:
                plan.plan(skip_warnings=True)
            else:
                return
        except plan.PlanError as e:
            if self.inProcess:
                self.on_item_error(e)
                return
            else:
                msg = QtW.QMessageBox()
                msg.setIcon(QtW.QMessageBox.Information)
                msg.setText(str(e))
                _skip = msg.addButton('Skip Item', QtW.QMessageBox.YesRole)
                msg.addButton('Cancel Process', QtW.QMessageBox.NoRole)
                msg.exec_()
                if msg.clickedButton() == _skip:
                    self.on_item_error(e)
                    return
                else:
                    self.on_work_aborted()
                    return

        # Create worker thread
        worker, thread = newWorkerThread(QueueItemWorker, plan)
        worker.work_starting.connect(self.item_starting.emit)
        worker.finished.connect(self.on_item_finished)
        worker.item_errored.connect(self.on_item_error)
        worker.plan.t_finished.connect(self.step_finished.emit)
        worker.plan.imp_starting.connect(self.emit_update)
        self.worker_threads.append((thread, worker))
        self.abort_request.connect(worker.plan.abort)
        self.inProcess = True
        thread.start()

        # recolor the first row to indicate processing
        self.setRowBackgroundColor(numskipped, QtGui.QColor(0, 0, 255, 30))
        self.clearSelection()

    @QtCore.pyqtSlot(object, dict)
    def emit_update(self, imp, meta):
        updatestring = 'Timepoint {} of {}: {}...'.format(meta.get('t'), meta.get('nt'), imp.verb())
        self.status_update.emit(updatestring)

    @QtCore.pyqtSlot(object)
    def on_item_error(self, e):
        self.cleanup_last_worker()
        self.setRowBackgroundColor(len(self.skipped_items), QtGui.QColor(255, 0, 0, 60))
        self.skipped_items.add(self.currentPath)
        self.look_for_next_item()

    @QtCore.pyqtSlot()
    def on_item_finished(self):
        self.cleanup_last_worker()
        self.numProcessed += 1
        if self.aborted:
            self.on_work_aborted()
        else:
            try:
                itemTime = QtCore.QTime(0, 0).addMSecs(self.timer.elapsed()).toString()
                logger.info(">" * 4 + " Item {} finished in {} ".format(
                    self.currentIndex.text(), itemTime) + "<" * 4)
            except AttributeError:
                pass
            self.removePath(self.currentPath)
            self.currentPath = None
            self.currentIndex = None
            self.look_for_next_item()

    def cleanup_last_worker(self):
        if len(self.worker_threads):
            thread, worker = self.worker_threads.pop(0)
            worker.deleteLater()
            thread.quit()
            thread.wait()

    def look_for_next_item(self):
        if self.rowCount() > len(self.skipped_items):
            self.planNextItem()
        else:
            if self.rowCount() <= len(self.skipped_items):
                self.on_work_finished()

    def on_work_finished(self):
        self.inProcess = False
        self.work_finished.emit(1, self.numProcessed, len(self.skipped_items))

    def abort_workers(self):
        logger.info('Message sent to abort ...')
        if len(self.worker_threads):
            self.aborted = True
            self.abort_request.emit()
        else:
            self.on_work_aborted()

    def on_work_aborted(self):
        self.inProcess = False
        self.work_finished.emit(0, self.numProcessed, len(self.skipped_items))
        self.setRowBackgroundColor(0, '#FFFFFF')
        self.aborted = False
