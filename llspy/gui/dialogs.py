from PyQt5 import QtWidgets, QtCore


class MemorableMessageBox(QtWidgets.QMessageBox):
    def __init__(self, prefname, mem_msg="Remember my preference", *args, **kwargs):
        super(MemorableMessageBox, self).__init__(*args, **kwargs)
        self.prefname = prefname
        self.pref = QtWidgets.QCheckBox(mem_msg)
        self.pref.stateChanged.connect(self.update_pref)
        self.setCheckBox(self.pref)

    @QtCore.pyqtSlot(int)
    def update_pref(self, value):
        print(value)
