from PyQt5 import QtWidgets, QtCore


class MemorableMessageBox(QtWidgets.QMessageBox):
    def __init__(self, prefname, mem_msg="Remember my preference", *args, **kwargs):
        super(MemorableMessageBox, self).__init__(*args, **kwargs)
        self.prefname = prefname
        pref = QtWidgets.QCheckBox(mem_msg)
        pref.stateChanged.connect(self.update_pref)
        self.setCheckBox(pref)

    @QtCore.pyqtSlot(int)
    def update_pref(self, value):
        print(value)


def confirm_quit():
    msgbox = MemorableMessageBox(
        'confirmOnQuit',
        "Always quit without confirmation",
        QtWidgets.QMessageBox.Question,
        'Unprocessed items!',
        'You have unprocessed items.  Are you sure you want to quit?',
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
    )
    msgbox.setDefaultButton(msgbox.No)
    return msgbox
