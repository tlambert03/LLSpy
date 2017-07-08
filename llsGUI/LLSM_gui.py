import os
import subprocess
from PyQt5 import QtGui, QtCore, QtWidgets
import numpy as N

class DragDropListView(QtWidgets.QListWidget):

    # A signal needs to be defined on class level:
    dropSignal = QtCore.pyqtSignal(list, name="dropped")
    # This signal emits when a URL is dropped onto this list,
    # and triggers handler defined in parent widget.

    def __init__(self, type, parent=None):
        super(DragDropListView, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

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
            links = []
            for url in event.mimeData().urls():
                print str(url.toLocalFile())
                links.append(str(url.toLocalFile()))
            self.dropSignal.emit(links)
        else:
            event.ignore()

    def keyPressEvent(self, event):
        super(DragDropListView, self).keyPressEvent(event)
        if event.key() == QtCore.Qt.Key_Delete:
            itemList = self.selectedItems()
            for i in itemList:
                item = self.takeItem(self.row(i))
                del item
            self.setCurrentItem(self.currentItem())


class main_GUI(QtWidgets.QFrame):
    ''' '''

    def __init__(self):
        QtWidgets.QFrame.__init__(self)
        self.setWindowTitle("Lattice Light Sheet")
        self.setMinimumSize(360, 300)

        layout = QtWidgets.QVBoxLayout()

        # 1. The listview to be populated with directories:
        self.listbox = DragDropListView(self)
        label = QtWidgets.QLabel("Directories to be processed (drag and drop here):")
        layout.addWidget(label)
        layout.addWidget(self.listbox)
        self.listbox.setToolTip('Drag data folders and drop here;\nfiles will be ignored;\npress "Delete" key to remove selected folders;\nCtrl-A to select all')

        # 2. Text input fields for the "-i", "-x" and "-w" flags:
        gridGroupBox = QtWidgets.QGroupBox("Deconv Options:")
        layout1 = QtWidgets.QGridLayout()

        label = QtWidgets.QLabel("# of iterations:")
        row = 0
        layout1.addWidget(label, row, 0)

        self.nItersValidator = QtGui.QIntValidator(0, 20, self)
        self.nItersEdit = QtWidgets.QLineEdit(self)
        self.nItersEdit.setMinimumWidth(30)
        self.nItersEdit.setText("12")
        self.nItersEdit.setValidator(self.nItersValidator)
        self.nItersEdit.setToolTip("Enter the number of deconv iterations")
        layout1.addWidget(self.nItersEdit, row, 1)

        row += 1
        label = QtWidgets.QLabel("Width after deskew:")
        layout1.addWidget(label, row, 0)

        # An input validator to confine width input between 1 and 2000 (wide enough?)
        self.widthValidator = QtGui.QIntValidator(1, 2000, self)

        self.deskewWidthEdit = QtWidgets.QLineEdit(self)
        self.deskewWidthEdit.setText("0")
        self.deskewWidthEdit.setValidator(self.widthValidator)
        self.deskewWidthEdit.setToolTip("Enter the desired image width after deskewing;\n0 for auto determine")
        layout1.addWidget(self.deskewWidthEdit, row, 1)
        # layout1.setAlignment (self.deskewWidthEdit, QtCore.Qt.AlignLeft)

        row += 1
        label = QtWidgets.QLabel("Shift in X:")
        layout1.addWidget(label, row, 0)
        # layout1.setAlignment(label, QtCore.Qt.AlignRight)

        self.xShiftEdit = QtWidgets.QLineEdit(self)
        self.xShiftEdit.setText("0")
        self.xShiftEdit.setValidator(self.widthValidator)
        self.xShiftEdit.setToolTip("Enter the number of pixel to shift in X; positive number shifts sample to left")
        layout1.addWidget(self.xShiftEdit, row, 1)
        # layout1.setAlignment (self.xShiftEdit, QtCore.Qt.AlignLeft)

        row += 1
        label = QtWidgets.QLabel("Do MIP:")
        layout1.addWidget(label, row, 0)
        self.MIPedit = QtWidgets.QLineEdit(self)
        self.MIPedit.setText("0 0 0")
        self.MIPedit.setToolTip("Save max-intensity projection after deconvolution along x, y, or z axis;\ntakes 3 binary numbers separated by space representing 3 axes; e.g.: 0 0 1")
        layout1.addWidget(self.MIPedit, row, 1)

        # 3. Checkboxes
        row = 0
        col = 2
        self.rotResultCheck = QtWidgets.QCheckBox ("Rotate result?", self)
        self.rotResultCheck.setToolTip("Check this to rotate result around Y so that cover slip is paralle to X-Y plane")
        layout1.addWidget(self.rotResultCheck, row, col)

        row += 1
        self.saveFloatCheck = QtWidgets.QCheckBox ("Save in 32-bit float?", self)
        self.saveFloatCheck.setToolTip("Check this to save results in single-precision floating point")
        layout1.addWidget(self.saveFloatCheck, row, col)
        # layout1.setAlignment(self.saveFloatCheck, QtCore.Qt.AlignHCenter)

        row += 1
        self.bleachCorrCheck = QtWidgets.QCheckBox ("Bleach correction?", self)
        self.bleachCorrCheck.setToolTip("Check this to correct photobleaching")
        layout1.addWidget(self.bleachCorrCheck, row, col)
        # layout1.setAlignment(self.bleachCorrCheck, QtCore.Qt.AlignHCenter)
        # layout.addLayout(layout2)

        row += 1
        self.flashCorrCheck = QtWidgets.QCheckBox ("Flash correction?", self)
        self.flashCorrCheck.setToolTip("Check this to correct flash pixels")
        layout1.addWidget(self.flashCorrCheck, row, col)

        # Let the column with edit fields stretch:
        layout1.setColumnStretch(1, 10)
        gridGroupBox.setLayout(layout1)
        layout.addWidget(gridGroupBox)

        # 4. Button to start processing all data folders:
        layout3 = QtWidgets.QHBoxLayout()
        previewBut = QtWidgets.QPushButton('Preview', self)
        previewBut.clicked.connect(self.onPreview)
        processBut = QtWidgets.QPushButton('Process', self)
        processBut.clicked.connect(self.onProcess)

        layout3.addWidget(previewBut)
        layout3.addWidget(processBut)
        layout.addLayout(layout3)

        self.statbar = QtWidgets.QStatusBar(self)
        self.statbar.showMessage('Ready')
        layout.addWidget(self.statbar)

        self.setLayout(layout)

        self.listbox.dropSignal.connect(self.onFolderDropped)
        processBut.setFocus()

    def onPreview(self):
        '''
        Try the parameters with only the first time point and
        display result on a popup viewer
        '''
        self.validateParams()
        print "To do"
        return

    def onProcess(self):
        '''
        Responds to "Process" button pressed
        1. Check validity of Wiener constant inputs
        2. Check if "TIRF" is checked
        3. Loop over the listed folders and launch sirecon subprocess for each
        '''
        if self.listbox.count() == 0:
            QtWidgets.QMessageBox.warning(self, "Stop",
                                      "No data folder has been selected",
                                      QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton)
            return

        nItersStr = self.nItersEdit.text()
        finalWidthStr = self.deskewWidthEdit.text()
        xShiftStr = self.xShiftEdit.text()
        if self.widthValidator.validate(wiener488Str, 0)[0] != 2 or \
           self.widthValidator.validate(wiener560Str, 0)[0] != 2:
            QtWidgets.QMessageBox.critical(self, "Error",
                                       "Wiener constant needs to be within [%.5f, %.5f]" %
                                       (self.widthValidator.bottom(), self.widthValidator.top()),
                                       QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton)
            return

        bRotResult = self.rotResultCheck.isChecked()
        bSaveFloat = self.saveFloatCheck.isChecked()
        bBleachCorr = self.bleachCorrCheck.isChecked()
        

        # The following was done for SIM; needs to be changed
        for ind in xrange(self.listbox.count()):
            curdir = str(self.listbox.item(ind).text())
            #"execGPU" defined in settings.py, loaded into globals() dict
            commandline = [execGPU, curDir, OTFfile]
            self.statbar.showMessage( 'Processing #%d folder...' % (int + 1) )
            self.statbar.repaint()
            QtWidgets.qApp.processEvents()
            subprocess.call(commandline, stdout=outputTextFile)
            outputTextFile.close()
        self.statbar.showMessage('Ready')

    def onFolderDropped(self, links):
        '''
        Triggered after URLs are dropped onto self.listbox
        '''
        for url in links:
            if os.path.exists(url) and os.path.isdir(url):

                # If this folder is not on the list yet, add it to the list:

                if len(self.listbox.findItems(url, QtCore.Qt.MatchExactly)) == 0:
                    item = QtWidgets.QListWidgetItem(url, self.listbox)


if __name__ == '__main__':
    # Load defaults, such as Windows batch file names, into global namespace:
    execfile(os.path.dirname(os.path.abspath(__file__))+'/settings.py', globals())

    app = QtWidgets.QApplication([])
    window = main_GUI()
    window.show()
    app.exec_()
