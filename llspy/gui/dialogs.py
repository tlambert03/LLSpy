from PyQt5 import QtWidgets, QtCore
from functools import partial
from llspy.gui import SETTINGS, helpers, settings
from llspy import __version__


class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()


class PreferencesWindow(QtWidgets.QDialog):
    def __init__(self,):
        super(PreferencesWindow, self).__init__()
        self.setLayout(QtWidgets.QGridLayout())

        title = QtWidgets.QLabel('LLSpy Preferences')
        title.setStyleSheet('font-weight: bold; font-size: 20px;')
        self.layout().addWidget(title, 0, 0, 1, 2)
        for i, settup in enumerate(settings.SETTUPS.values()):
            val = SETTINGS.value(settup.key)
            stuff = helpers.val_to_widget(val, settup.key)
            if not stuff:
                continue
            widg, signal, getter, dtype = stuff
            signal.connect(self.set_param(settup.key, getter, type(val)))
            label = ClickableLabel(settup.description)
            label.clicked.connect(widg.toggle)
            self.layout().addWidget(widg, i + 1, 0)
            self.layout().addWidget(label, i + 1, 1)
            self.layout().setSpacing(16)
            self.layout().setContentsMargins(50, 25, 70, 40)
        self.layout().setColumnStretch(1, 1)
        self.setFixedSize(self.sizeHint())

    def set_param(self, key, getter, dtype):
        """ update the parameter dict when the widg has changed """
        def func():
            SETTINGS.setValue(key, dtype(getter()))
        return func


class DontConfirmMsgBox(QtWidgets.QMessageBox):
    def __init__(self, prefname, chk_msg=None, title=None, text=None, btns=None,
                 default_btn=None, icon=None):
        icon = icon or QtWidgets.QMessageBox.Question
        title = title or ''
        text = text or ''
        btns = btns or (QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        super(DontConfirmMsgBox, self).__init__(icon, title, text, btns)
        if default_btn:
            self.setDefaultButton(default_btn)
        self.prefname = prefname
        self.chkBox = QtWidgets.QCheckBox(chk_msg)
        self._remember = self.chkBox.isChecked()
        self.chkBox.stateChanged.connect(self.remember_pref)
        self.setCheckBox(self.chkBox)
        self.msg = QtWidgets.QLabel('(This can be changed in the Preferences window)')
        self.msg.setStyleSheet('font-style: italic;')

    @QtCore.pyqtSlot(int)
    def remember_pref(self, value):
        if value:
            SETTINGS.setValue(self.prefname, False)
            _lay = self.layout()
            _lay.addWidget(self.msg, _lay.rowCount() - 2, _lay.columnCount() - 1)
        else:
            SETTINGS.setValue(self.prefname, True)


confirm_quit_msgbox = partial(
    DontConfirmMsgBox,
    settings.CONFIRM_ON_QUIT.key,
    'Always quit without asking',
    'Unprocessed items!',
    'You have unprocessed items.  Are you sure you want to quit?',
    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
    QtWidgets.QMessageBox.Yes)


class RenameItersMsgBox(DontConfirmMsgBox):
    def __init__(self):
        super(RenameItersMsgBox, self).__init__(
            settings.WARN_ITERS.key,
            'Never ask to rename files',
            'Scripted Aquisition Detected',
            'This folder appears to have been aquired in Script Editor mode, '
            '(it has "Iter_" in the filenames).  Do you want to rename the files '
            'to match the standard naming convention? \n\nThis can (usually) be undone '
            'by selecting "Undo Rename Iters_" in the Process menu',
            QtWidgets.QMessageBox.Cancel)
        self.addButton("Process Anyway", self.YesRole)
        self.addButton("Rename Iters", self.ActionRole)
        self.setDefaultButton(self.Cancel)


class NewVersionDialog(DontConfirmMsgBox):
    def __init__(self, newversion):
        super(NewVersionDialog, self).__init__(
            settings.CHECK_UPDATES.key,
            "Don't check for new updates",
            'New Version Available',
            'Update available: v%s\n\nYou are using v%s'
            .format(newversion, __version__) +
            'You may update by typing "conda update -c talley llspy" '
            'at the anaconda prompt.',
            QtWidgets.QMessageBox.OK, QtWidgets.QMessageBox.OK,
            QtWidgets.QMessageBox.Information)
