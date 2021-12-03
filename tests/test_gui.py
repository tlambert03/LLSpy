from llspy.gui.mainwindow import main_GUI
from llspy.gui.exceptions import MissingBinaryError
from llspy.exceptions import CUDAbinException, LibCUDAException
import contextlib
import pytest
from pathlib import Path

TEST_DATA = Path(__file__).parent / "testdata"
SAMPLE = TEST_DATA / 'sample'


@pytest.fixture
def main_window(qtbot):
    # FIXME:
    with contextlib.suppress(MissingBinaryError, CUDAbinException):
        win = main_GUI()
    qtbot.addWidget(win)
    yield win


def test_main_window(main_window):
    assert main_window


def test_add_path(main_window: main_GUI):
    main_window.listbox.addPath(str(SAMPLE))
    assert main_window.listbox.rowCount() == 1

