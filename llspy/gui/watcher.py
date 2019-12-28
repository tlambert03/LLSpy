import fnmatch
import logging
import os
import os.path as osp
import time

import numpy as np
from PyQt5 import QtCore

import llspy
from llspy.gui import workers
from llspy.gui.helpers import (
    newWorkerThread,
    shortname,
    wait_for_file_close,
    wait_for_folder_finished,
)

_watchdog = False
ActiveWatcher = None
MainHandler = None
Observer = None
try:
    from watchdog import events
    from watchdog.observers import Observer

    _watchdog = True
except ImportError:
    pass

logger = logging.getLogger()  # set root logger
logger.setLevel(logging.DEBUG)
lhStdout = logger.handlers[0]  # grab console handler so we can delete later
ch = logging.StreamHandler()  # create new console handler
ch.setLevel(logging.ERROR)  # with desired logging level
# ch.addFilter(logging.Filter('llspy'))  # and any filters
logger.addHandler(ch)  # add it to the root logger
logger.removeHandler(lhStdout)  # and delete the original streamhandler


if _watchdog:

    class ActiveWatcher(QtCore.QObject):
        """docstring for ActiveWatcher"""

        finished = QtCore.pyqtSignal()
        stalled = QtCore.pyqtSignal()
        status_update = QtCore.pyqtSignal(str, int)

        def __init__(self, path, timeout=30):
            super(ActiveWatcher, self).__init__()
            self.path = path
            self.timeout = timeout  # seconds to wait for new file before giving up
            self.inProcess = False
            settext = llspy.util.find_filepattern(path, "*Settings.txt")
            wait_for_file_close(settext)
            time.sleep(1)  # give the settings file a minute to write
            self.E = llspy.LLSdir(path, False)
            # TODO:  probably need to check for files that are already there
            self.tQueue = []
            self.allReceived = False
            self.worker = None

            try:
                app = QtCore.QCoreApplication.instance()
                gui = next(
                    w for w in app.topLevelWidgets() if w.objectName == "main_GUI"
                )
                self.opts = gui.getValidatedOptions()
            except Exception:
                raise

            # timeout clock to make sure this directory doesn't stagnate
            self.timer = QtCore.QTimer()
            self.timer.timeout.connect(self.stall)
            self.timer.start(self.timeout * 1000)

            # Too strict?
            fpattern = "^.+_ch\d_stack\d{4}_\D*\d+.*_\d{7}msec_\d{10}msecAbs.*.tif"
            # fpattern = '.*.tif'
            handler = ActiveHandler(
                str(self.E.path),
                self.E.parameters.nc,
                self.E.parameters.nt,
                regexes=[fpattern],
                ignore_directories=True,
            )
            handler.tReady.connect(self.add_ready)
            handler.allReceived.connect(self.all_received)
            handler.newfile.connect(self.newfile)
            handler.check_for_existing_files()

            self.observer = Observer()
            self.observer.schedule(handler, self.path, recursive=False)
            self.observer.start()

            logger.info("New LLS directory now being watched: " + self.path)

        @QtCore.pyqtSlot(str)
        def newfile(self, path):
            self.restart_clock()
            self.status_update.emit(shortname(path), 2000)

        def all_received(self):
            self.allReceived = True
            if not self.inProcess and len(self.tQueue):
                self.terminate()

        def restart_clock(self):
            # restart the kill timer, since the handler is still alive
            self.timer.start(self.timeout * 1000)

        def add_ready(self, t):
            # add the new timepoint to the Queue
            self.tQueue.append(t)
            # start processing
            self.process()

        def process(self):
            if not self.inProcess and len(self.tQueue):
                self.inProcess = True
                timepoints = []
                while len(self.tQueue):
                    timepoints.append(self.tQueue.pop())
                timepoints = sorted(timepoints)
                cRange = None  # TODO: plug this in
                self.tQueue = []

                # note: it was important NOT to ditch partial tiffs with the activate
                # watcher since the files aren't finished yet...
                w, thread = newWorkerThread(
                    workers.TimePointWorker,
                    self.path,
                    timepoints,
                    cRange,
                    self.opts,
                    False,
                    workerConnect={"previewReady": self.writeFile},
                    start=True,
                )
                self.worker = (timepoints, w, thread)
            elif not any((self.inProcess, len(self.tQueue), not self.allReceived)):
                self.terminate()

        @QtCore.pyqtSlot(np.ndarray, float, float)
        def writeFile(self, stack, dx, dz):
            timepoints, worker, thread = self.worker

            def write_stack(s, c=0, t=0):
                if self.opts["nIters"] > 0:
                    outfolder = "GPUdecon"
                    proctype = "_decon"
                else:
                    outfolder = "Deskewed"
                    proctype = "_deskewed"
                if not self.E.path.joinpath(outfolder).exists():
                    self.E.path.joinpath(outfolder).mkdir()

                corstring = "_COR" if self.opts["correctFlash"] else ""
                basename = os.path.basename(self.E.get_files(c=c, t=t)[0])
                filename = basename.replace(".tif", corstring + proctype + ".tif")
                outpath = str(self.E.path.joinpath(outfolder, filename))
                llspy.util.imsave(
                    llspy.util.reorderstack(np.squeeze(s), "zyx"),
                    outpath,
                    dx=self.E.parameters.dx,
                    dz=self.E.parameters.dzFinal,
                )

            if stack.ndim == 5:
                if not stack.shape[0] == len(timepoints):
                    raise ValueError(
                        "Processed stacks length not equal to requested"
                        " number of timepoints processed"
                    )
                for t in range(stack.shape[0]):
                    for c in range(stack.shape[1]):
                        s = stack[t][c]
                        write_stack(s, c, timepoints[t])
            elif stack.ndim == 4:
                for c in range(stack.shape[0]):
                    write_stack(stack[c], c, timepoints[0])
            else:
                write_stack(stack, t=timepoints[0])

            thread.quit()
            thread.wait()
            self.inProcess = False
            self.process()  # check to see if there's more waiting in the queue

        def stall(self):
            self.stalled.emit()
            logger.debug("WATCHER TIMEOUT REACHED!")
            self.terminate()

        @QtCore.pyqtSlot()
        def terminate(self):
            logger.debug("TERMINATING WATCHER")
            self.observer.stop()
            self.observer.join()
            self.finished.emit()

    class MainHandler(events.FileSystemEventHandler, QtCore.QObject):
        foundLLSdir = QtCore.pyqtSignal(str)
        lostListItem = QtCore.pyqtSignal(str)

        def __init__(self):
            super(MainHandler, self).__init__()

        def on_created(self, event):
            # Called when a file or directory is created.
            if event.is_directory:
                pass
            else:
                if "Settings.txt" in event.src_path:
                    wait_for_folder_finished(osp.dirname(event.src_path))
                    self.foundLLSdir.emit(osp.dirname(event.src_path))

        def on_deleted(self, event):
            # Called when a file or directory is created.
            if event.is_directory:
                app = QtCore.QCoreApplication.instance()
                gui = next(
                    w for w in app.topLevelWidgets() if w.objectName == "main_GUI"
                )

                # TODO:  Is it safe to directly access main gui listbox here?
                if len(gui.listbox.findItems(event.src_path, QtCore.Qt.MatchExactly)):
                    self.lostListItem.emit(event.src_path)

    class ActiveHandler(events.RegexMatchingEventHandler, QtCore.QObject):
        tReady = QtCore.pyqtSignal(int)
        allReceived = QtCore.pyqtSignal()  # don't expect to receive anymore
        newfile = QtCore.pyqtSignal(str)

        def __init__(self, path, nC, nT, **kwargs):
            super(ActiveHandler, self).__init__(**kwargs)
            self.path = path
            self.nC = nC
            self.nT = nT
            # this assumes the experiment hasn't been stopped mid-stream
            self.counter = np.zeros(self.nT)

        def check_for_existing_files(self):
            # this is here in case files already exist in the directory...
            # we don't want the handler to miss them
            # this is called by the parent after connecting the tReady signal
            for f in os.listdir(self.path):
                if fnmatch.fnmatch(f, "*tif"):
                    self.register_file(osp.join(self.path, f))

        def on_created(self, event):
            # Called when a file or directory is created.
            self.register_file(event.src_path)

        def register_file(self, path):
            self.newfile.emit(path)
            p = llspy.parse.parse_filename(osp.basename(path))
            self.counter[p["stack"]] += 1
            ready = np.where(self.counter == self.nC)[0]
            # break counter for those timepoints
            self.counter[ready] = np.nan
            # can use <100 as a sign of timepoints still not finished
            if len(ready):
                # try to see if file has finished writing... does this work?
                wait_for_file_close(path)
                [self.tReady.emit(t) for t in ready]

            # once all nC * nT has been seen emit allReceived
            if all(np.isnan(self.counter)):
                logger.debug("All Timepoints Received")
                self.allReceived.emit()
