from qtpy import QtWidgets, QtGui, QtCore


# first use APP.setStyle(QtW.QStyleFactory.create("fusion"))
DarkPalette = QtGui.QPalette()
DarkPalette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
DarkPalette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.lightGray)
DarkPalette.setColor(QtGui.QPalette.Base, QtGui.QColor(15, 15, 15))
DarkPalette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
DarkPalette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.lightGray)
DarkPalette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.lightGray)
DarkPalette.setColor(QtGui.QPalette.Text, QtCore.Qt.gray)
DarkPalette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
DarkPalette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.gray)
DarkPalette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
DarkPalette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(142, 45, 197).lighter())
DarkPalette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
