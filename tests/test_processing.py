import os
import shutil

from qtpy import QtCore

from llspy.gui.mainwindow import main_GUI
from llspy.llsdir import LLSdir

from .conftest import requires_cuda


@requires_cuda
def test_basic_processing(qtbot):
    testdata = os.path.join(os.path.dirname(__file__), "testdata", "sample")
    deconFolder = os.path.join(testdata, "GPUdecon")
    if os.path.isdir(deconFolder):
        shutil.rmtree(deconFolder)
    LLSdir(testdata).reduce_to_raw(keepmip=False)
    n_testfiles = len(os.listdir(testdata))
    otfdir = os.path.join(os.path.dirname(__file__), "testdata", "otfs")
    mainGUI = main_GUI()
    qtbot.addWidget(mainGUI)
    mainGUI.loadProgramDefaults()
    mainGUI.setOTFdirPath(otfdir)
    assert mainGUI.listbox.rowCount() == 0
    mainGUI.listbox.addPath(testdata)
    assert mainGUI.listbox.rowCount() == 1
    with qtbot.waitSignal(mainGUI.sig_processing_done, timeout=60000):
        mainGUI.onProcess()
    MIPfolder = os.path.join(deconFolder, "MIPs")
    assert os.path.isdir(deconFolder)
    assert os.path.isdir(MIPfolder)
    assert len(os.listdir(deconFolder)) == 3
    assert len(os.listdir(MIPfolder)) == 1

    LLSdir(testdata).reduce_to_raw(keepmip=False)
    assert not os.path.isdir(deconFolder)
    assert not os.path.isdir(MIPfolder)
    assert len(os.listdir(testdata)) == n_testfiles
    mainGUI.quitProgram(save=False)


# def test_spimagine_preview(qtbot):
#     testdata = os.path.join(os.path.dirname(__file__), 'testdata', 'sample')
#     otfdir = os.path.join(os.path.dirname(__file__), 'testdata', 'otfs')
#     APP = QtWidgets.QApplication([])
#     mainGUI = main_GUI()
#     mainGUI.loadProgramDefaults()
#     mainGUI.setOTFdirPath(otfdir)
#     assert mainGUI.listbox.rowCount() == 0
#     mainGUI.listbox.addPath(testdata)
#     assert mainGUI.listbox.rowCount() == 1

#     def preview_exists():
#         assert len(mainGUI.spimwins)
#     mainGUI.prevBackendSpimagineRadio.setChecked(True)
#     qtbot.mouseClick(mainGUI.previewButton, QtCore.Qt.LeftButton)
#     qtbot.waitUntil(preview_exists, timeout=10000)
#     mainGUI.close_all_previews()
#     assert len(mainGUI.spimwins) == 0
#     mainGUI.quitProgram(save=False)


@requires_cuda
def test_matplotlib_preview(qtbot):
    testdata = os.path.join(os.path.dirname(__file__), "testdata", "sample")
    otfdir = os.path.join(os.path.dirname(__file__), "testdata", "otfs")
    mainGUI = main_GUI()
    qtbot.addWidget(mainGUI)
    mainGUI.loadProgramDefaults()
    mainGUI.setOTFdirPath(otfdir)
    assert mainGUI.listbox.rowCount() == 0
    mainGUI.listbox.addPath(testdata)
    assert mainGUI.listbox.rowCount() == 1

    def preview_exists():
        assert len(mainGUI.spimwins)

    mainGUI.prevBackendMatplotlibRadio.setChecked(True)
    qtbot.mouseClick(mainGUI.previewButton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(preview_exists, timeout=10000)
    mainGUI.close_all_previews()
    assert len(mainGUI.spimwins) == 0
    mainGUI.quitProgram(save=False)
