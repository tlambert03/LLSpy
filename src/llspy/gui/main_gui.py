# Form implementation generated from reading ui file '/Users/talley/Dropbox (HMS)/Python/LLSpy/llspy/gui/main_gui.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from qtpy import QtCore, QtGui, QtWidgets


class Ui_Main_GUI:
    def setupUi(self, Main_GUI):
        Main_GUI.setObjectName("Main_GUI")
        Main_GUI.resize(617, 861)
        Main_GUI.setMinimumSize(QtCore.QSize(0, 861))
        Main_GUI.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.centralWidget = QtWidgets.QWidget(Main_GUI)
        self.centralWidget.setObjectName("centralWidget")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.centralWidget)
        self.verticalLayout_4.setContentsMargins(11, 11, 11, 11)
        self.verticalLayout_4.setSpacing(6)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.tabWidget = QtWidgets.QTabWidget(self.centralWidget)
        self.tabWidget.setMinimumSize(QtCore.QSize(593, 500))
        self.tabWidget.setTabPosition(QtWidgets.QTabWidget.North)
        self.tabWidget.setElideMode(QtCore.Qt.ElideRight)
        self.tabWidget.setObjectName("tabWidget")
        self.tab_process = QtWidgets.QWidget()
        self.tab_process.setObjectName("tab_process")
        self.process_tab_layout = QtWidgets.QVBoxLayout(self.tab_process)
        self.process_tab_layout.setContentsMargins(11, 11, 11, 11)
        self.process_tab_layout.setSpacing(6)
        self.process_tab_layout.setObjectName("process_tab_layout")
        self.listbox = QtWidgets.QTableWidget(self.tab_process)
        self.listbox.setMinimumSize(QtCore.QSize(0, 200))
        self.listbox.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.listbox.setDragEnabled(True)
        self.listbox.setDragDropOverwriteMode(False)
        self.listbox.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.listbox.setAlternatingRowColors(True)
        self.listbox.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.listbox.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.listbox.setShowGrid(True)
        self.listbox.setGridStyle(QtCore.Qt.DashLine)
        self.listbox.setWordWrap(False)
        self.listbox.setCornerButtonEnabled(True)
        self.listbox.setColumnCount(7)
        self.listbox.setObjectName("listbox")
        self.listbox.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.listbox.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.listbox.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.listbox.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.listbox.setHorizontalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.listbox.setHorizontalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        self.listbox.setHorizontalHeaderItem(5, item)
        item = QtWidgets.QTableWidgetItem()
        self.listbox.setHorizontalHeaderItem(6, item)
        self.process_tab_layout.addWidget(self.listbox)
        self.processingToolBox = QtWidgets.QToolBox(self.tab_process)
        font = QtGui.QFont()
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        font.setStrikeOut(False)
        self.processingToolBox.setFont(font)
        self.processingToolBox.setObjectName("processingToolBox")
        self.tool_preprocess = QtWidgets.QWidget()
        self.tool_preprocess.setGeometry(QtCore.QRect(0, 0, 547, 292))
        self.tool_preprocess.setObjectName("tool_preprocess")
        self.verticalLayout_16 = QtWidgets.QVBoxLayout(self.tool_preprocess)
        self.verticalLayout_16.setContentsMargins(11, 11, 11, 11)
        self.verticalLayout_16.setSpacing(6)
        self.verticalLayout_16.setObjectName("verticalLayout_16")
        self.camcorGroupBox = QtWidgets.QGroupBox(self.tool_preprocess)
        self.camcorGroupBox.setStyleSheet(
            "QGroupBox{font-size: 14px} QGroupBox::title{subcontrol-position: top left}"
        )
        self.camcorGroupBox.setObjectName("camcorGroupBox")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.camcorGroupBox)
        self.gridLayout_2.setContentsMargins(11, 11, 11, 11)
        self.gridLayout_2.setSpacing(6)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.camcorCheckBox = QtWidgets.QCheckBox(self.camcorGroupBox)
        self.camcorCheckBox.setObjectName("camcorCheckBox")
        self.gridLayout_2.addWidget(self.camcorCheckBox, 0, 0, 1, 2)
        self.camcorTargetCombo = QtWidgets.QComboBox(self.camcorGroupBox)
        self.camcorTargetCombo.setEnabled(False)
        self.camcorTargetCombo.setObjectName("camcorTargetCombo")
        self.camcorTargetCombo.addItem("")
        self.camcorTargetCombo.addItem("")
        self.camcorTargetCombo.addItem("")
        self.gridLayout_2.addWidget(self.camcorTargetCombo, 0, 2, 1, 1)
        self.medianFilterCheckBox = QtWidgets.QCheckBox(self.camcorGroupBox)
        self.medianFilterCheckBox.setMouseTracking(True)
        self.medianFilterCheckBox.setObjectName("medianFilterCheckBox")
        self.gridLayout_2.addWidget(self.medianFilterCheckBox, 0, 4, 1, 1)
        self.saveCamCorrectedCheckBox = QtWidgets.QCheckBox(self.camcorGroupBox)
        self.saveCamCorrectedCheckBox.setEnabled(True)
        self.saveCamCorrectedCheckBox.setChecked(True)
        self.saveCamCorrectedCheckBox.setObjectName("saveCamCorrectedCheckBox")
        self.gridLayout_2.addWidget(self.saveCamCorrectedCheckBox, 0, 5, 1, 2)
        self.camParamTiffToolButton = QtWidgets.QToolButton(self.camcorGroupBox)
        self.camParamTiffToolButton.setObjectName("camParamTiffToolButton")
        self.gridLayout_2.addWidget(self.camParamTiffToolButton, 1, 6, 1, 1)
        self.camParamTiffLabel = QtWidgets.QLabel(self.camcorGroupBox)
        self.camParamTiffLabel.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter
        )
        self.camParamTiffLabel.setObjectName("camParamTiffLabel")
        self.gridLayout_2.addWidget(self.camParamTiffLabel, 1, 0, 1, 1)
        self.camParamTiffLineEdit = QtWidgets.QLineEdit(self.camcorGroupBox)
        self.camParamTiffLineEdit.setText("")
        self.camParamTiffLineEdit.setAlignment(
            QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        self.camParamTiffLineEdit.setReadOnly(True)
        self.camParamTiffLineEdit.setObjectName("camParamTiffLineEdit")
        self.gridLayout_2.addWidget(self.camParamTiffLineEdit, 1, 1, 1, 5)
        spacerItem = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.gridLayout_2.addItem(spacerItem, 0, 3, 1, 1)
        self.verticalLayout_16.addWidget(self.camcorGroupBox)
        self.trimEdgesGroupBox = QtWidgets.QGroupBox(self.tool_preprocess)
        self.trimEdgesGroupBox.setStyleSheet(
            "QGroupBox{font-size: 14px} QGroupBox::title{subcontrol-position: top left}"
        )
        self.trimEdgesGroupBox.setObjectName("trimEdgesGroupBox")
        self.gridLayout_23 = QtWidgets.QGridLayout(self.trimEdgesGroupBox)
        self.gridLayout_23.setContentsMargins(8, 8, 11, 8)
        self.gridLayout_23.setSpacing(6)
        self.gridLayout_23.setObjectName("gridLayout_23")
        self.trimZ1SpinBox = QtWidgets.QSpinBox(self.trimEdgesGroupBox)
        self.trimZ1SpinBox.setMaximum(999)
        self.trimZ1SpinBox.setObjectName("trimZ1SpinBox")
        self.gridLayout_23.addWidget(self.trimZ1SpinBox, 1, 7, 1, 1)
        self.trimX1SpinBox = QtWidgets.QSpinBox(self.trimEdgesGroupBox)
        self.trimX1SpinBox.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.trimX1SpinBox.setMaximum(999)
        self.trimX1SpinBox.setProperty("value", 1)
        self.trimX1SpinBox.setObjectName("trimX1SpinBox")
        self.gridLayout_23.addWidget(self.trimX1SpinBox, 1, 1, 1, 1)
        self.trimY1SpinBox = QtWidgets.QSpinBox(self.trimEdgesGroupBox)
        self.trimY1SpinBox.setMaximum(999)
        self.trimY1SpinBox.setObjectName("trimY1SpinBox")
        self.gridLayout_23.addWidget(self.trimY1SpinBox, 1, 4, 1, 1)
        self.trimZ0Label = QtWidgets.QLabel(self.trimEdgesGroupBox)
        self.trimZ0Label.setObjectName("trimZ0Label")
        self.gridLayout_23.addWidget(self.trimZ0Label, 0, 6, 1, 1, QtCore.Qt.AlignRight)
        self.trimX0SpinBox = QtWidgets.QSpinBox(self.trimEdgesGroupBox)
        self.trimX0SpinBox.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.trimX0SpinBox.setAutoFillBackground(False)
        self.trimX0SpinBox.setMaximum(999)
        self.trimX0SpinBox.setProperty("value", 1)
        self.trimX0SpinBox.setObjectName("trimX0SpinBox")
        self.gridLayout_23.addWidget(self.trimX0SpinBox, 0, 1, 1, 1)
        self.trimZ0SpinBox = QtWidgets.QSpinBox(self.trimEdgesGroupBox)
        self.trimZ0SpinBox.setAutoFillBackground(False)
        self.trimZ0SpinBox.setMaximum(999)
        self.trimZ0SpinBox.setProperty("value", 1)
        self.trimZ0SpinBox.setObjectName("trimZ0SpinBox")
        self.gridLayout_23.addWidget(self.trimZ0SpinBox, 0, 7, 1, 1)
        self.trimY0Label = QtWidgets.QLabel(self.trimEdgesGroupBox)
        self.trimY0Label.setObjectName("trimY0Label")
        self.gridLayout_23.addWidget(self.trimY0Label, 0, 3, 1, 1, QtCore.Qt.AlignRight)
        self.trimZ1Label = QtWidgets.QLabel(self.trimEdgesGroupBox)
        self.trimZ1Label.setObjectName("trimZ1Label")
        self.gridLayout_23.addWidget(self.trimZ1Label, 1, 6, 1, 1, QtCore.Qt.AlignRight)
        self.trimX0Label = QtWidgets.QLabel(self.trimEdgesGroupBox)
        self.trimX0Label.setObjectName("trimX0Label")
        self.gridLayout_23.addWidget(self.trimX0Label, 0, 0, 1, 1, QtCore.Qt.AlignRight)
        self.trimY1Label = QtWidgets.QLabel(self.trimEdgesGroupBox)
        self.trimY1Label.setObjectName("trimY1Label")
        self.gridLayout_23.addWidget(self.trimY1Label, 1, 3, 1, 1, QtCore.Qt.AlignRight)
        spacerItem1 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.gridLayout_23.addItem(spacerItem1, 1, 2, 1, 1)
        self.trimY0SpinBox = QtWidgets.QSpinBox(self.trimEdgesGroupBox)
        self.trimY0SpinBox.setMaximum(999)
        self.trimY0SpinBox.setObjectName("trimY0SpinBox")
        self.gridLayout_23.addWidget(self.trimY0SpinBox, 0, 4, 1, 1)
        self.trimX1Label = QtWidgets.QLabel(self.trimEdgesGroupBox)
        self.trimX1Label.setObjectName("trimX1Label")
        self.gridLayout_23.addWidget(self.trimX1Label, 1, 0, 1, 1, QtCore.Qt.AlignRight)
        spacerItem2 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.gridLayout_23.addItem(spacerItem2, 0, 2, 1, 1)
        spacerItem3 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.gridLayout_23.addItem(spacerItem3, 1, 5, 1, 1)
        spacerItem4 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.gridLayout_23.addItem(spacerItem4, 0, 5, 1, 1)
        self.trimX0Label.raise_()
        self.trimX0SpinBox.raise_()
        self.trimY0Label.raise_()
        self.trimY0SpinBox.raise_()
        self.trimZ0Label.raise_()
        self.trimZ0SpinBox.raise_()
        self.trimX1Label.raise_()
        self.trimX1SpinBox.raise_()
        self.trimY1SpinBox.raise_()
        self.trimY1Label.raise_()
        self.trimZ1SpinBox.raise_()
        self.trimZ1Label.raise_()
        self.verticalLayout_16.addWidget(self.trimEdgesGroupBox)
        self.backgroundGroupBox = QtWidgets.QGroupBox(self.tool_preprocess)
        self.backgroundGroupBox.setStyleSheet(
            "QGroupBox{font-size: 14px} QGroupBox::title{subcontrol-position: top left}"
        )
        self.backgroundGroupBox.setObjectName("backgroundGroupBox")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.backgroundGroupBox)
        self.horizontalLayout_6.setContentsMargins(8, 8, 11, 8)
        self.horizontalLayout_6.setSpacing(6)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.backgroundAutoRadio = QtWidgets.QRadioButton(self.backgroundGroupBox)
        self.backgroundAutoRadio.setChecked(True)
        self.backgroundAutoRadio.setObjectName("backgroundAutoRadio")
        self.horizontalLayout_6.addWidget(self.backgroundAutoRadio)
        spacerItem5 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_6.addItem(spacerItem5)
        self.backgroundFixedRadio = QtWidgets.QRadioButton(self.backgroundGroupBox)
        self.backgroundFixedRadio.setObjectName("backgroundFixedRadio")
        self.horizontalLayout_6.addWidget(self.backgroundFixedRadio)
        self.backgroundFixedSpinBox = QtWidgets.QSpinBox(self.backgroundGroupBox)
        self.backgroundFixedSpinBox.setEnabled(False)
        self.backgroundFixedSpinBox.setAutoFillBackground(False)
        self.backgroundFixedSpinBox.setMaximum(1000)
        self.backgroundFixedSpinBox.setProperty("value", 90)
        self.backgroundFixedSpinBox.setObjectName("backgroundFixedSpinBox")
        self.horizontalLayout_6.addWidget(self.backgroundFixedSpinBox)
        spacerItem6 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_6.addItem(spacerItem6)
        self.backgroundRollingRadio = QtWidgets.QRadioButton(self.backgroundGroupBox)
        self.backgroundRollingRadio.setEnabled(False)
        self.backgroundRollingRadio.setObjectName("backgroundRollingRadio")
        self.horizontalLayout_6.addWidget(self.backgroundRollingRadio)
        self.backgroundRollingSpinBox = QtWidgets.QSpinBox(self.backgroundGroupBox)
        self.backgroundRollingSpinBox.setEnabled(False)
        self.backgroundRollingSpinBox.setProperty("value", 10)
        self.backgroundRollingSpinBox.setObjectName("backgroundRollingSpinBox")
        self.horizontalLayout_6.addWidget(self.backgroundRollingSpinBox)
        self.verticalLayout_16.addWidget(self.backgroundGroupBox)
        spacerItem7 = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.verticalLayout_16.addItem(spacerItem7)
        self.processingToolBox.addItem(self.tool_preprocess, "")
        self.tool_deconvolution = QtWidgets.QWidget()
        self.tool_deconvolution.setGeometry(QtCore.QRect(0, 0, 477, 282))
        self.tool_deconvolution.setObjectName("tool_deconvolution")
        self.verticalLayout_14 = QtWidgets.QVBoxLayout(self.tool_deconvolution)
        self.verticalLayout_14.setContentsMargins(11, 11, 11, 11)
        self.verticalLayout_14.setSpacing(6)
        self.verticalLayout_14.setObjectName("verticalLayout_14")
        self.doDeconGroupBox = QtWidgets.QGroupBox(self.tool_deconvolution)
        self.doDeconGroupBox.setToolTip("")
        self.doDeconGroupBox.setStyleSheet(
            "QGroupBox{font-size: 14px} QGroupBox::title{subcontrol-position: top left}"
        )
        self.doDeconGroupBox.setFlat(False)
        self.doDeconGroupBox.setCheckable(True)
        self.doDeconGroupBox.setChecked(True)
        self.doDeconGroupBox.setObjectName("doDeconGroupBox")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.doDeconGroupBox)
        self.verticalLayout.setContentsMargins(6, 6, 6, 6)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setObjectName("verticalLayout")
        self.deconParamsLayout = QtWidgets.QHBoxLayout()
        self.deconParamsLayout.setContentsMargins(-1, 0, -1, -1)
        self.deconParamsLayout.setSpacing(6)
        self.deconParamsLayout.setObjectName("deconParamsLayout")
        self.iterationsLabel = QtWidgets.QLabel(self.doDeconGroupBox)
        self.iterationsLabel.setEnabled(True)
        self.iterationsLabel.setObjectName("iterationsLabel")
        self.deconParamsLayout.addWidget(self.iterationsLabel)
        self.iterationsSpinBox = QtWidgets.QSpinBox(self.doDeconGroupBox)
        self.iterationsSpinBox.setEnabled(True)
        self.iterationsSpinBox.setMaximum(20)
        self.iterationsSpinBox.setProperty("value", 10)
        self.iterationsSpinBox.setObjectName("iterationsSpinBox")
        self.deconParamsLayout.addWidget(self.iterationsSpinBox)
        spacerItem8 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.deconParamsLayout.addItem(spacerItem8)
        self.apodizeLabel = QtWidgets.QLabel(self.doDeconGroupBox)
        self.apodizeLabel.setEnabled(True)
        self.apodizeLabel.setObjectName("apodizeLabel")
        self.deconParamsLayout.addWidget(self.apodizeLabel)
        self.apodizeSpinBox = QtWidgets.QSpinBox(self.doDeconGroupBox)
        self.apodizeSpinBox.setEnabled(True)
        self.apodizeSpinBox.setMaximum(40)
        self.apodizeSpinBox.setProperty("value", 15)
        self.apodizeSpinBox.setObjectName("apodizeSpinBox")
        self.deconParamsLayout.addWidget(self.apodizeSpinBox)
        spacerItem9 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.deconParamsLayout.addItem(spacerItem9)
        self.zblendLabel = QtWidgets.QLabel(self.doDeconGroupBox)
        self.zblendLabel.setEnabled(True)
        self.zblendLabel.setObjectName("zblendLabel")
        self.deconParamsLayout.addWidget(self.zblendLabel)
        self.zblendSpinBox = QtWidgets.QSpinBox(self.doDeconGroupBox)
        self.zblendSpinBox.setEnabled(True)
        self.zblendSpinBox.setMaximum(20)
        self.zblendSpinBox.setObjectName("zblendSpinBox")
        self.deconParamsLayout.addWidget(self.zblendSpinBox)
        self.verticalLayout.addLayout(self.deconParamsLayout)
        self.deconvSaveLayout = QtWidgets.QHBoxLayout()
        self.deconvSaveLayout.setContentsMargins(-1, 0, -1, -1)
        self.deconvSaveLayout.setSpacing(6)
        self.deconvSaveLayout.setObjectName("deconvSaveLayout")
        self.saveDeconvolvedCheckBox = QtWidgets.QCheckBox(self.doDeconGroupBox)
        self.saveDeconvolvedCheckBox.setEnabled(False)
        self.saveDeconvolvedCheckBox.setChecked(True)
        self.saveDeconvolvedCheckBox.setObjectName("saveDeconvolvedCheckBox")
        self.deconvSaveLayout.addWidget(self.saveDeconvolvedCheckBox)
        spacerItem10 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.deconvSaveLayout.addItem(spacerItem10)
        self.deconvolvedMIPFrame = QtWidgets.QFrame(self.doDeconGroupBox)
        self.deconvolvedMIPFrame.setEnabled(True)
        self.deconvolvedMIPFrame.setFrameShape(QtWidgets.QFrame.Panel)
        self.deconvolvedMIPFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.deconvolvedMIPFrame.setObjectName("deconvolvedMIPFrame")
        self.horizontalLayout_25 = QtWidgets.QHBoxLayout(self.deconvolvedMIPFrame)
        self.horizontalLayout_25.setContentsMargins(5, 5, 5, 5)
        self.horizontalLayout_25.setSpacing(6)
        self.horizontalLayout_25.setObjectName("horizontalLayout_25")
        self.deconSaveMIPSLabel = QtWidgets.QLabel(self.deconvolvedMIPFrame)
        self.deconSaveMIPSLabel.setEnabled(True)
        self.deconSaveMIPSLabel.setObjectName("deconSaveMIPSLabel")
        self.horizontalLayout_25.addWidget(self.deconSaveMIPSLabel)
        self.deconXMIPCheckBox = QtWidgets.QCheckBox(self.deconvolvedMIPFrame)
        self.deconXMIPCheckBox.setEnabled(True)
        self.deconXMIPCheckBox.setObjectName("deconXMIPCheckBox")
        self.horizontalLayout_25.addWidget(self.deconXMIPCheckBox)
        self.deconYMIPCheckBox = QtWidgets.QCheckBox(self.deconvolvedMIPFrame)
        self.deconYMIPCheckBox.setEnabled(True)
        self.deconYMIPCheckBox.setObjectName("deconYMIPCheckBox")
        self.horizontalLayout_25.addWidget(self.deconYMIPCheckBox)
        self.deconZMIPCheckBox = QtWidgets.QCheckBox(self.deconvolvedMIPFrame)
        self.deconZMIPCheckBox.setEnabled(True)
        self.deconZMIPCheckBox.setChecked(True)
        self.deconZMIPCheckBox.setObjectName("deconZMIPCheckBox")
        self.horizontalLayout_25.addWidget(self.deconZMIPCheckBox)
        self.deconvSaveLayout.addWidget(self.deconvolvedMIPFrame)
        spacerItem11 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.deconvSaveLayout.addItem(spacerItem11)
        self.deconvolvedBitDepthCombo = QtWidgets.QComboBox(self.doDeconGroupBox)
        self.deconvolvedBitDepthCombo.setEnabled(True)
        self.deconvolvedBitDepthCombo.setMaximumSize(QtCore.QSize(100, 16777215))
        self.deconvolvedBitDepthCombo.setObjectName("deconvolvedBitDepthCombo")
        self.deconvolvedBitDepthCombo.addItem("")
        self.deconvolvedBitDepthCombo.addItem("")
        self.deconvSaveLayout.addWidget(self.deconvolvedBitDepthCombo)
        self.verticalLayout.addLayout(self.deconvSaveLayout)
        self.verticalLayout_14.addWidget(self.doDeconGroupBox)
        self.deskewedGroupBox = QtWidgets.QGroupBox(self.tool_deconvolution)
        self.deskewedGroupBox.setStyleSheet(
            "QGroupBox{font-size: 14px} QGroupBox::title{subcontrol-position: top left}"
        )
        self.deskewedGroupBox.setObjectName("deskewedGroupBox")
        self.gridLayout_7 = QtWidgets.QGridLayout(self.deskewedGroupBox)
        self.gridLayout_7.setContentsMargins(4, 4, 8, 8)
        self.gridLayout_7.setSpacing(6)
        self.gridLayout_7.setObjectName("gridLayout_7")
        spacerItem12 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.gridLayout_7.addItem(spacerItem12, 0, 1, 1, 1)
        self.deskewedMIPFrame = QtWidgets.QFrame(self.deskewedGroupBox)
        self.deskewedMIPFrame.setFrameShape(QtWidgets.QFrame.Panel)
        self.deskewedMIPFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.deskewedMIPFrame.setObjectName("deskewedMIPFrame")
        self.horizontalLayout_21 = QtWidgets.QHBoxLayout(self.deskewedMIPFrame)
        self.horizontalLayout_21.setContentsMargins(5, 5, 5, 5)
        self.horizontalLayout_21.setSpacing(6)
        self.horizontalLayout_21.setObjectName("horizontalLayout_21")
        self.deconSaveMIPSLabel_2 = QtWidgets.QLabel(self.deskewedMIPFrame)
        self.deconSaveMIPSLabel_2.setEnabled(True)
        self.deconSaveMIPSLabel_2.setObjectName("deconSaveMIPSLabel_2")
        self.horizontalLayout_21.addWidget(self.deconSaveMIPSLabel_2)
        self.deskewedXMIPCheckBox = QtWidgets.QCheckBox(self.deskewedMIPFrame)
        self.deskewedXMIPCheckBox.setObjectName("deskewedXMIPCheckBox")
        self.horizontalLayout_21.addWidget(self.deskewedXMIPCheckBox)
        self.deskewedYMIPCheckBox = QtWidgets.QCheckBox(self.deskewedMIPFrame)
        self.deskewedYMIPCheckBox.setObjectName("deskewedYMIPCheckBox")
        self.horizontalLayout_21.addWidget(self.deskewedYMIPCheckBox)
        self.deskewedZMIPCheckBox = QtWidgets.QCheckBox(self.deskewedMIPFrame)
        self.deskewedZMIPCheckBox.setObjectName("deskewedZMIPCheckBox")
        self.horizontalLayout_21.addWidget(self.deskewedZMIPCheckBox)
        self.gridLayout_7.addWidget(self.deskewedMIPFrame, 0, 2, 1, 1)
        self.saveDeskewedCheckBox = QtWidgets.QCheckBox(self.deskewedGroupBox)
        self.saveDeskewedCheckBox.setChecked(True)
        self.saveDeskewedCheckBox.setObjectName("saveDeskewedCheckBox")
        self.gridLayout_7.addWidget(self.saveDeskewedCheckBox, 0, 0, 1, 1)
        self.deskewedBitDepthCombo = QtWidgets.QComboBox(self.deskewedGroupBox)
        self.deskewedBitDepthCombo.setEnabled(False)
        self.deskewedBitDepthCombo.setMaximumSize(QtCore.QSize(100, 16777215))
        self.deskewedBitDepthCombo.setObjectName("deskewedBitDepthCombo")
        self.deskewedBitDepthCombo.addItem("")
        self.deskewedBitDepthCombo.addItem("")
        self.gridLayout_7.addWidget(self.deskewedBitDepthCombo, 0, 4, 1, 1)
        spacerItem13 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.gridLayout_7.addItem(spacerItem13, 0, 3, 1, 1)
        self.verticalLayout_14.addWidget(self.deskewedGroupBox)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setContentsMargins(-1, 0, -1, -1)
        self.horizontalLayout_2.setSpacing(6)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.deconJoinMIPCheckBox = QtWidgets.QCheckBox(self.tool_deconvolution)
        self.deconJoinMIPCheckBox.setEnabled(True)
        self.deconJoinMIPCheckBox.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.deconJoinMIPCheckBox.setChecked(True)
        self.deconJoinMIPCheckBox.setObjectName("deconJoinMIPCheckBox")
        self.horizontalLayout_2.addWidget(self.deconJoinMIPCheckBox)
        spacerItem14 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_2.addItem(spacerItem14)
        self.useLZWCheckBox = QtWidgets.QCheckBox(self.tool_deconvolution)
        self.useLZWCheckBox.setEnabled(True)
        self.useLZWCheckBox.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.useLZWCheckBox.setChecked(True)
        self.useLZWCheckBox.setObjectName("useLZWCheckBox")
        self.horizontalLayout_2.addWidget(self.useLZWCheckBox)
        self.verticalLayout_14.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setContentsMargins(-1, 0, -1, -1)
        self.horizontalLayout_3.setSpacing(6)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.dupRevStackCheckBox = QtWidgets.QCheckBox(self.tool_deconvolution)
        self.dupRevStackCheckBox.setEnabled(True)
        self.dupRevStackCheckBox.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.dupRevStackCheckBox.setChecked(True)
        self.dupRevStackCheckBox.setObjectName("dupRevStackCheckBox")
        self.horizontalLayout_3.addWidget(self.dupRevStackCheckBox)
        spacerItem15 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_3.addItem(spacerItem15)
        self.padValLabel = QtWidgets.QLabel(self.tool_deconvolution)
        self.padValLabel.setEnabled(True)
        self.padValLabel.setObjectName("padValLabel")
        self.horizontalLayout_3.addWidget(self.padValLabel)
        self.padValSpinBox = QtWidgets.QSpinBox(self.tool_deconvolution)
        self.padValSpinBox.setEnabled(True)
        self.padValSpinBox.setMinimum(0)
        self.padValSpinBox.setMaximum(9999)
        self.padValSpinBox.setProperty("value", 0)
        self.padValSpinBox.setObjectName("padValSpinBox")
        self.horizontalLayout_3.addWidget(self.padValSpinBox)
        self.verticalLayout_14.addLayout(self.horizontalLayout_3)
        spacerItem16 = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.verticalLayout_14.addItem(spacerItem16)
        self.processingToolBox.addItem(self.tool_deconvolution, "")
        self.tool_postprocess = QtWidgets.QWidget()
        self.tool_postprocess.setGeometry(QtCore.QRect(0, 0, 547, 337))
        self.tool_postprocess.setObjectName("tool_postprocess")
        self.verticalLayout_12 = QtWidgets.QVBoxLayout(self.tool_postprocess)
        self.verticalLayout_12.setContentsMargins(11, 11, 11, 11)
        self.verticalLayout_12.setSpacing(6)
        self.verticalLayout_12.setObjectName("verticalLayout_12")
        self.croppingGroupBox = QtWidgets.QGroupBox(self.tool_postprocess)
        self.croppingGroupBox.setStyleSheet(
            "QGroupBox{font-size: 14px} QGroupBox::title{subcontrol-position: top left}"
        )
        self.croppingGroupBox.setCheckable(True)
        self.croppingGroupBox.setChecked(True)
        self.croppingGroupBox.setObjectName("croppingGroupBox")
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout(self.croppingGroupBox)
        self.horizontalLayout_7.setContentsMargins(8, 5, 11, 5)
        self.horizontalLayout_7.setSpacing(6)
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.cropAutoRadio = QtWidgets.QRadioButton(self.croppingGroupBox)
        self.cropAutoRadio.setChecked(True)
        self.cropAutoRadio.setObjectName("cropAutoRadio")
        self.horizontalLayout_7.addWidget(self.cropAutoRadio)
        self.autocropPadLabel = QtWidgets.QLabel(self.croppingGroupBox)
        self.autocropPadLabel.setEnabled(True)
        self.autocropPadLabel.setScaledContents(False)
        self.autocropPadLabel.setObjectName("autocropPadLabel")
        self.horizontalLayout_7.addWidget(self.autocropPadLabel)
        self.autocropPadSpinBox = QtWidgets.QSpinBox(self.croppingGroupBox)
        self.autocropPadSpinBox.setEnabled(True)
        self.autocropPadSpinBox.setMinimumSize(QtCore.QSize(48, 0))
        self.autocropPadSpinBox.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.autocropPadSpinBox.setMaximum(500)
        self.autocropPadSpinBox.setProperty("value", 50)
        self.autocropPadSpinBox.setObjectName("autocropPadSpinBox")
        self.horizontalLayout_7.addWidget(self.autocropPadSpinBox)
        spacerItem17 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_7.addItem(spacerItem17)
        self.cropManualRadio = QtWidgets.QRadioButton(self.croppingGroupBox)
        self.cropManualRadio.setObjectName("cropManualRadio")
        self.horizontalLayout_7.addWidget(self.cropManualRadio)
        self.cropManualGroupBox = QtWidgets.QGroupBox(self.croppingGroupBox)
        self.cropManualGroupBox.setEnabled(True)
        self.cropManualGroupBox.setTitle("")
        self.cropManualGroupBox.setFlat(False)
        self.cropManualGroupBox.setObjectName("cropManualGroupBox")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.cropManualGroupBox)
        self.horizontalLayout.setContentsMargins(4, 2, 2, 0)
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.cropWidthLabel = QtWidgets.QLabel(self.cropManualGroupBox)
        self.cropWidthLabel.setEnabled(False)
        self.cropWidthLabel.setScaledContents(False)
        self.cropWidthLabel.setObjectName("cropWidthLabel")
        self.horizontalLayout.addWidget(self.cropWidthLabel)
        self.cropWidthSpinBox = QtWidgets.QSpinBox(self.cropManualGroupBox)
        self.cropWidthSpinBox.setEnabled(False)
        self.cropWidthSpinBox.setMinimumSize(QtCore.QSize(50, 0))
        self.cropWidthSpinBox.setMaximum(2000)
        self.cropWidthSpinBox.setObjectName("cropWidthSpinBox")
        self.horizontalLayout.addWidget(self.cropWidthSpinBox)
        self.cropShiftLabel = QtWidgets.QLabel(self.cropManualGroupBox)
        self.cropShiftLabel.setEnabled(False)
        self.cropShiftLabel.setObjectName("cropShiftLabel")
        self.horizontalLayout.addWidget(self.cropShiftLabel)
        self.cropShiftSpinBox = QtWidgets.QSpinBox(self.cropManualGroupBox)
        self.cropShiftSpinBox.setEnabled(False)
        self.cropShiftSpinBox.setMinimumSize(QtCore.QSize(48, 0))
        self.cropShiftSpinBox.setMinimum(-1000)
        self.cropShiftSpinBox.setMaximum(1000)
        self.cropShiftSpinBox.setObjectName("cropShiftSpinBox")
        self.horizontalLayout.addWidget(self.cropShiftSpinBox)
        self.horizontalLayout_7.addWidget(self.cropManualGroupBox)
        self.verticalLayout_12.addWidget(self.croppingGroupBox)
        self.rotateGroupBox = QtWidgets.QGroupBox(self.tool_postprocess)
        self.rotateGroupBox.setEnabled(True)
        self.rotateGroupBox.setStyleSheet(
            "QGroupBox{font-size: 14px} QGroupBox::title{subcontrol-position: top left}"
        )
        self.rotateGroupBox.setCheckable(True)
        self.rotateGroupBox.setChecked(True)
        self.rotateGroupBox.setObjectName("rotateGroupBox")
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout(self.rotateGroupBox)
        self.horizontalLayout_8.setContentsMargins(8, 4, 8, 4)
        self.horizontalLayout_8.setSpacing(6)
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.rotateReverseCheckBox = QtWidgets.QCheckBox(self.rotateGroupBox)
        self.rotateReverseCheckBox.setEnabled(True)
        self.rotateReverseCheckBox.setObjectName("rotateReverseCheckBox")
        self.horizontalLayout_8.addWidget(self.rotateReverseCheckBox)
        spacerItem18 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_8.addItem(spacerItem18)
        self.rotateOverrideCheckBox = QtWidgets.QCheckBox(self.rotateGroupBox)
        self.rotateOverrideCheckBox.setEnabled(True)
        self.rotateOverrideCheckBox.setObjectName("rotateOverrideCheckBox")
        self.horizontalLayout_8.addWidget(
            self.rotateOverrideCheckBox, 0, QtCore.Qt.AlignRight
        )
        self.rotateOverrideSpinBox = QtWidgets.QDoubleSpinBox(self.rotateGroupBox)
        self.rotateOverrideSpinBox.setEnabled(False)
        self.rotateOverrideSpinBox.setMaximumSize(QtCore.QSize(70, 16777215))
        self.rotateOverrideSpinBox.setMinimum(-180.0)
        self.rotateOverrideSpinBox.setMaximum(180.0)
        self.rotateOverrideSpinBox.setSingleStep(0.5)
        self.rotateOverrideSpinBox.setProperty("value", 31.5)
        self.rotateOverrideSpinBox.setObjectName("rotateOverrideSpinBox")
        self.horizontalLayout_8.addWidget(self.rotateOverrideSpinBox)
        self.verticalLayout_12.addWidget(self.rotateGroupBox)
        self.doRegistrationGroupBox = QtWidgets.QGroupBox(self.tool_postprocess)
        self.doRegistrationGroupBox.setStyleSheet(
            "QGroupBox{font-size: 14px} QGroupBox::title{subcontrol-position: top left}"
        )
        self.doRegistrationGroupBox.setCheckable(True)
        self.doRegistrationGroupBox.setChecked(True)
        self.doRegistrationGroupBox.setObjectName("doRegistrationGroupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.doRegistrationGroupBox)
        self.gridLayout.setContentsMargins(11, 11, 11, 11)
        self.gridLayout.setSpacing(6)
        self.gridLayout.setObjectName("gridLayout")
        self.channelRefLabel = QtWidgets.QLabel(self.doRegistrationGroupBox)
        self.channelRefLabel.setEnabled(True)
        self.channelRefLabel.setObjectName("channelRefLabel")
        self.gridLayout.addWidget(self.channelRefLabel, 0, 0, 1, 1)
        self.RegProcessChannelRefCombo = QtWidgets.QComboBox(
            self.doRegistrationGroupBox
        )
        self.RegProcessChannelRefCombo.setEnabled(True)
        self.RegProcessChannelRefCombo.setMaximumSize(QtCore.QSize(65, 16777215))
        self.RegProcessChannelRefCombo.setCurrentText("")
        self.RegProcessChannelRefCombo.setObjectName("RegProcessChannelRefCombo")
        self.gridLayout.addWidget(self.RegProcessChannelRefCombo, 0, 1, 1, 1)
        self.channelRefModeLabel = QtWidgets.QLabel(self.doRegistrationGroupBox)
        self.channelRefModeLabel.setObjectName("channelRefModeLabel")
        self.gridLayout.addWidget(self.channelRefModeLabel, 0, 2, 1, 1)
        self.RegProcessChannelRefModeCombo = QtWidgets.QComboBox(
            self.doRegistrationGroupBox
        )
        self.RegProcessChannelRefModeCombo.setEnabled(True)
        self.RegProcessChannelRefModeCombo.setMinimumSize(QtCore.QSize(130, 0))
        self.RegProcessChannelRefModeCombo.setMaximumSize(QtCore.QSize(50, 16777215))
        self.RegProcessChannelRefModeCombo.setCurrentText("")
        self.RegProcessChannelRefModeCombo.setObjectName(
            "RegProcessChannelRefModeCombo"
        )
        self.gridLayout.addWidget(self.RegProcessChannelRefModeCombo, 0, 3, 1, 1)
        spacerItem19 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.gridLayout.addItem(spacerItem19, 0, 4, 1, 1)
        self.RegProcessLoadRegFile = QtWidgets.QPushButton(self.doRegistrationGroupBox)
        self.RegProcessLoadRegFile.setObjectName("RegProcessLoadRegFile")
        self.gridLayout.addWidget(self.RegProcessLoadRegFile, 0, 5, 1, 1)
        self.RegProcessPathLabel = QtWidgets.QLabel(self.doRegistrationGroupBox)
        self.RegProcessPathLabel.setObjectName("RegProcessPathLabel")
        self.gridLayout.addWidget(self.RegProcessPathLabel, 1, 0, 1, 1)
        self.RegProcessPathLineEdit = QtWidgets.QLineEdit(self.doRegistrationGroupBox)
        self.RegProcessPathLineEdit.setEnabled(True)
        self.RegProcessPathLineEdit.setReadOnly(True)
        self.RegProcessPathLineEdit.setObjectName("RegProcessPathLineEdit")
        self.gridLayout.addWidget(self.RegProcessPathLineEdit, 1, 1, 1, 4)
        self.RegProcessPathPushButton = QtWidgets.QPushButton(
            self.doRegistrationGroupBox
        )
        self.RegProcessPathPushButton.setObjectName("RegProcessPathPushButton")
        self.gridLayout.addWidget(self.RegProcessPathPushButton, 1, 5, 1, 1)
        self.discardUnregisteredCheckBox = QtWidgets.QCheckBox(
            self.doRegistrationGroupBox
        )
        self.discardUnregisteredCheckBox.setEnabled(True)
        self.discardUnregisteredCheckBox.setObjectName("discardUnregisteredCheckBox")
        self.gridLayout.addWidget(self.discardUnregisteredCheckBox, 2, 0, 1, 5)
        self.verticalLayout_12.addWidget(self.doRegistrationGroupBox)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setContentsMargins(-1, 0, -1, -1)
        self.horizontalLayout_4.setSpacing(6)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.bleachCorrectionCheckBox = QtWidgets.QCheckBox(self.tool_postprocess)
        self.bleachCorrectionCheckBox.setObjectName("bleachCorrectionCheckBox")
        self.horizontalLayout_4.addWidget(self.bleachCorrectionCheckBox)
        spacerItem20 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_4.addItem(spacerItem20)
        self.compressRawCheckBox = QtWidgets.QCheckBox(self.tool_postprocess)
        self.compressRawCheckBox.setObjectName("compressRawCheckBox")
        self.horizontalLayout_4.addWidget(self.compressRawCheckBox)
        spacerItem21 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_4.addItem(spacerItem21)
        self.label = QtWidgets.QLabel(self.tool_postprocess)
        self.label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter
        )
        self.label.setObjectName("label")
        self.horizontalLayout_4.addWidget(self.label)
        self.compressTypeCombo = QtWidgets.QComboBox(self.tool_postprocess)
        self.compressTypeCombo.setEnabled(True)
        self.compressTypeCombo.setMinimumSize(QtCore.QSize(0, 0))
        self.compressTypeCombo.setMaximumSize(QtCore.QSize(100, 16777215))
        self.compressTypeCombo.setEditable(False)
        self.compressTypeCombo.setObjectName("compressTypeCombo")
        self.horizontalLayout_4.addWidget(self.compressTypeCombo)
        self.verticalLayout_12.addLayout(self.horizontalLayout_4)
        spacerItem22 = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.verticalLayout_12.addItem(spacerItem22)
        self.processingToolBox.addItem(self.tool_postprocess, "")
        self.process_tab_layout.addWidget(self.processingToolBox)
        self.tabWidget.addTab(self.tab_process, "")
        self.tab_registration = QtWidgets.QWidget()
        self.tab_registration.setObjectName("tab_registration")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.tab_registration)
        self.gridLayout_3.setContentsMargins(11, 11, 11, 11)
        self.gridLayout_3.setSpacing(6)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.RegCalib_channelRefModeCombo = QtWidgets.QComboBox(self.tab_registration)
        self.RegCalib_channelRefModeCombo.setEnabled(True)
        self.RegCalib_channelRefModeCombo.setMinimumSize(QtCore.QSize(0, 0))
        self.RegCalib_channelRefModeCombo.setMaximumSize(
            QtCore.QSize(1606000, 16777215)
        )
        self.RegCalib_channelRefModeCombo.setCurrentText("")
        self.RegCalib_channelRefModeCombo.setObjectName("RegCalib_channelRefModeCombo")
        self.gridLayout_3.addWidget(self.RegCalib_channelRefModeCombo, 8, 6, 1, 3)
        self.RegCalibPathLineEdit = QtWidgets.QLineEdit(self.tab_registration)
        self.RegCalibPathLineEdit.setEnabled(True)
        self.RegCalibPathLineEdit.setObjectName("RegCalibPathLineEdit")
        self.gridLayout_3.addWidget(self.RegCalibPathLineEdit, 0, 1, 1, 7)
        self.RegCalib_channelRefCombo = QtWidgets.QComboBox(self.tab_registration)
        self.RegCalib_channelRefCombo.setEnabled(True)
        self.RegCalib_channelRefCombo.setMaximumSize(QtCore.QSize(70, 16777215))
        self.RegCalib_channelRefCombo.setCurrentText("")
        self.RegCalib_channelRefCombo.setObjectName("RegCalib_channelRefCombo")
        self.gridLayout_3.addWidget(self.RegCalib_channelRefCombo, 8, 4, 1, 1)
        self.RegCalibRefChannelsLabel = QtWidgets.QLabel(self.tab_registration)
        self.RegCalibRefChannelsLabel.setEnabled(True)
        self.RegCalibRefChannelsLabel.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter
        )
        self.RegCalibRefChannelsLabel.setObjectName("RegCalibRefChannelsLabel")
        self.gridLayout_3.addWidget(self.RegCalibRefChannelsLabel, 3, 2, 1, 2)
        self.GenerateRegFileButton = QtWidgets.QPushButton(self.tab_registration)
        self.GenerateRegFileButton.setMinimumSize(QtCore.QSize(190, 0))
        self.GenerateRegFileButton.setObjectName("GenerateRegFileButton")
        self.gridLayout_3.addWidget(self.GenerateRegFileButton, 3, 0, 1, 2)
        self.RegCalibPathLabel = QtWidgets.QLabel(self.tab_registration)
        self.RegCalibPathLabel.setMinimumSize(QtCore.QSize(95, 0))
        self.RegCalibPathLabel.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.RegCalibPathLabel.setAlignment(
            QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        self.RegCalibPathLabel.setObjectName("RegCalibPathLabel")
        self.gridLayout_3.addWidget(self.RegCalibPathLabel, 0, 0, 1, 1)
        self.RegCalib_channelRefModeLabel = QtWidgets.QLabel(self.tab_registration)
        self.RegCalib_channelRefModeLabel.setMaximumSize(QtCore.QSize(50, 16777215))
        self.RegCalib_channelRefModeLabel.setObjectName("RegCalib_channelRefModeLabel")
        self.gridLayout_3.addWidget(self.RegCalib_channelRefModeLabel, 8, 5, 1, 1)
        self.horizline_1 = QtWidgets.QFrame(self.tab_registration)
        self.horizline_1.setFrameShape(QtWidgets.QFrame.HLine)
        self.horizline_1.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.horizline_1.setObjectName("horizline_1")
        self.gridLayout_3.addWidget(self.horizline_1, 4, 0, 1, 9)
        spacerItem23 = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.gridLayout_3.addItem(spacerItem23, 9, 4, 1, 1)
        self.RegCalibPathLoadButton = QtWidgets.QPushButton(self.tab_registration)
        self.RegCalibPathLoadButton.setObjectName("RegCalibPathLoadButton")
        self.gridLayout_3.addWidget(self.RegCalibPathLoadButton, 0, 8, 1, 1)
        self.RegFilePathLoadButton = QtWidgets.QPushButton(self.tab_registration)
        self.RegFilePathLoadButton.setObjectName("RegFilePathLoadButton")
        self.gridLayout_3.addWidget(self.RegFilePathLoadButton, 6, 8, 1, 1)
        self.RegFilePathLabel = QtWidgets.QLabel(self.tab_registration)
        self.RegFilePathLabel.setMinimumSize(QtCore.QSize(105, 0))
        self.RegFilePathLabel.setObjectName("RegFilePathLabel")
        self.gridLayout_3.addWidget(self.RegFilePathLabel, 6, 0, 1, 1)
        self.RegFilePath = QtWidgets.QLineEdit(self.tab_registration)
        self.RegFilePath.setEnabled(True)
        self.RegFilePath.setText("")
        self.RegFilePath.setObjectName("RegFilePath")
        self.gridLayout_3.addWidget(self.RegFilePath, 6, 1, 1, 7)
        self.RegCalibPreviewButton = QtWidgets.QPushButton(self.tab_registration)
        self.RegCalibPreviewButton.setObjectName("RegCalibPreviewButton")
        self.gridLayout_3.addWidget(self.RegCalibPreviewButton, 8, 0, 1, 2)
        self.RegCalib_channelRefLabel = QtWidgets.QLabel(self.tab_registration)
        self.RegCalib_channelRefLabel.setEnabled(True)
        self.RegCalib_channelRefLabel.setObjectName("RegCalib_channelRefLabel")
        self.gridLayout_3.addWidget(self.RegCalib_channelRefLabel, 8, 2, 1, 2)
        self.BeadThresholdLabel = QtWidgets.QLabel(self.tab_registration)
        self.BeadThresholdLabel.setMinimumSize(QtCore.QSize(95, 0))
        self.BeadThresholdLabel.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.BeadThresholdLabel.setAlignment(
            QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        self.BeadThresholdLabel.setObjectName("BeadThresholdLabel")
        self.gridLayout_3.addWidget(self.BeadThresholdLabel, 1, 0, 1, 1)
        self.RegCalibRefChannelsGroup = QtWidgets.QGroupBox(self.tab_registration)
        self.RegCalibRefChannelsGroup.setTitle("")
        self.RegCalibRefChannelsGroup.setObjectName("RegCalibRefChannelsGroup")
        self.RegCalibRefGroupLayout = QtWidgets.QHBoxLayout(
            self.RegCalibRefChannelsGroup
        )
        self.RegCalibRefGroupLayout.setContentsMargins(11, 0, 11, 0)
        self.RegCalibRefGroupLayout.setSpacing(6)
        self.RegCalibRefGroupLayout.setObjectName("RegCalibRefGroupLayout")
        self.gridLayout_3.addWidget(self.RegCalibRefChannelsGroup, 3, 4, 1, 5)
        self.RegBeadThreshSpin = QtWidgets.QSpinBox(self.tab_registration)
        self.RegBeadThreshSpin.setEnabled(False)
        self.RegBeadThreshSpin.setMaximum(65536)
        self.RegBeadThreshSpin.setProperty("value", 1000)
        self.RegBeadThreshSpin.setObjectName("RegBeadThreshSpin")
        self.gridLayout_3.addWidget(self.RegBeadThreshSpin, 1, 1, 1, 1)
        self.RegMinBeadsLabel = QtWidgets.QLabel(self.tab_registration)
        self.RegMinBeadsLabel.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter
        )
        self.RegMinBeadsLabel.setObjectName("RegMinBeadsLabel")
        self.gridLayout_3.addWidget(self.RegMinBeadsLabel, 1, 4, 1, 4)
        self.RegMinBeadsSpin = QtWidgets.QSpinBox(self.tab_registration)
        self.RegMinBeadsSpin.setMaximum(200)
        self.RegMinBeadsSpin.setProperty("value", 20)
        self.RegMinBeadsSpin.setObjectName("RegMinBeadsSpin")
        self.gridLayout_3.addWidget(self.RegMinBeadsSpin, 1, 8, 1, 1)
        self.RegAutoThreshCheckbox = QtWidgets.QCheckBox(self.tab_registration)
        self.RegAutoThreshCheckbox.setEnabled(True)
        self.RegAutoThreshCheckbox.setChecked(True)
        self.RegAutoThreshCheckbox.setObjectName("RegAutoThreshCheckbox")
        self.gridLayout_3.addWidget(self.RegAutoThreshCheckbox, 1, 2, 1, 2)
        self.tabWidget.addTab(self.tab_registration, "")
        self.tab_config = QtWidgets.QWidget()
        self.tab_config.setObjectName("tab_config")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.tab_config)
        self.gridLayout_4.setContentsMargins(11, 11, 11, 11)
        self.gridLayout_4.setSpacing(6)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.filenamePatternLabel = QtWidgets.QLabel(self.tab_config)
        self.filenamePatternLabel.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter
        )
        self.filenamePatternLabel.setObjectName("filenamePatternLabel")
        self.gridLayout_4.addWidget(self.filenamePatternLabel, 3, 0, 1, 1)
        self.cudaDeconvPathLabel_2 = QtWidgets.QLabel(self.tab_config)
        self.cudaDeconvPathLabel_2.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter
        )
        self.cudaDeconvPathLabel_2.setObjectName("cudaDeconvPathLabel_2")
        self.gridLayout_4.addWidget(self.cudaDeconvPathLabel_2, 0, 0, 1, 1)
        self.useBundledBinariesCheckBox = QtWidgets.QCheckBox(self.tab_config)
        self.useBundledBinariesCheckBox.setChecked(False)
        self.useBundledBinariesCheckBox.setObjectName("useBundledBinariesCheckBox")
        self.gridLayout_4.addWidget(self.useBundledBinariesCheckBox, 1, 1, 1, 6)
        self.cudaDeconvPathLabel = QtWidgets.QLabel(self.tab_config)
        self.cudaDeconvPathLabel.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter
        )
        self.cudaDeconvPathLabel.setObjectName("cudaDeconvPathLabel")
        self.gridLayout_4.addWidget(self.cudaDeconvPathLabel, 5, 0, 1, 1)
        self.cudaDeconvPathLineEdit = QtWidgets.QLineEdit(self.tab_config)
        self.cudaDeconvPathLineEdit.setReadOnly(True)
        self.cudaDeconvPathLineEdit.setObjectName("cudaDeconvPathLineEdit")
        self.gridLayout_4.addWidget(self.cudaDeconvPathLineEdit, 5, 1, 1, 6)
        self.cudaDeconvPathToolButton = QtWidgets.QToolButton(self.tab_config)
        self.cudaDeconvPathToolButton.setAutoRaise(False)
        self.cudaDeconvPathToolButton.setObjectName("cudaDeconvPathToolButton")
        self.gridLayout_4.addWidget(self.cudaDeconvPathToolButton, 5, 7, 1, 1)
        self.otfFolderPathLabel = QtWidgets.QLabel(self.tab_config)
        self.otfFolderPathLabel.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter
        )
        self.otfFolderPathLabel.setObjectName("otfFolderPathLabel")
        self.gridLayout_4.addWidget(self.otfFolderPathLabel, 6, 0, 1, 1)
        self.otfFolderLineEdit = QtWidgets.QLineEdit(self.tab_config)
        self.otfFolderLineEdit.setText("")
        self.otfFolderLineEdit.setAlignment(
            QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        self.otfFolderLineEdit.setReadOnly(True)
        self.otfFolderLineEdit.setObjectName("otfFolderLineEdit")
        self.gridLayout_4.addWidget(self.otfFolderLineEdit, 6, 1, 1, 6)
        self.otfFolderToolButton = QtWidgets.QToolButton(self.tab_config)
        self.otfFolderToolButton.setObjectName("otfFolderToolButton")
        self.gridLayout_4.addWidget(self.otfFolderToolButton, 6, 7, 1, 1)
        self.allowNoSettingsCheckBox = QtWidgets.QCheckBox(self.tab_config)
        self.allowNoSettingsCheckBox.setChecked(False)
        self.allowNoSettingsCheckBox.setObjectName("allowNoSettingsCheckBox")
        self.gridLayout_4.addWidget(self.allowNoSettingsCheckBox, 7, 1, 1, 6)
        self.defaultValuesLabel = QtWidgets.QLabel(self.tab_config)
        self.defaultValuesLabel.setEnabled(False)
        self.defaultValuesLabel.setObjectName("defaultValuesLabel")
        self.gridLayout_4.addWidget(
            self.defaultValuesLabel, 8, 0, 1, 1, QtCore.Qt.AlignRight
        )
        self.defaultDxLabel = QtWidgets.QLabel(self.tab_config)
        self.defaultDxLabel.setEnabled(False)
        self.defaultDxLabel.setObjectName("defaultDxLabel")
        self.gridLayout_4.addWidget(
            self.defaultDxLabel, 8, 1, 1, 1, QtCore.Qt.AlignRight
        )
        self.defaultDxSpin = QtWidgets.QDoubleSpinBox(self.tab_config)
        self.defaultDxSpin.setEnabled(False)
        self.defaultDxSpin.setDecimals(3)
        self.defaultDxSpin.setSingleStep(0.01)
        self.defaultDxSpin.setProperty("value", 0.1)
        self.defaultDxSpin.setObjectName("defaultDxSpin")
        self.gridLayout_4.addWidget(self.defaultDxSpin, 8, 2, 1, 1)
        self.defaultDzLabel = QtWidgets.QLabel(self.tab_config)
        self.defaultDzLabel.setEnabled(False)
        self.defaultDzLabel.setObjectName("defaultDzLabel")
        self.gridLayout_4.addWidget(
            self.defaultDzLabel, 8, 3, 1, 1, QtCore.Qt.AlignRight
        )
        self.defaultDzSpin = QtWidgets.QDoubleSpinBox(self.tab_config)
        self.defaultDzSpin.setEnabled(False)
        self.defaultDzSpin.setDecimals(3)
        self.defaultDzSpin.setSingleStep(0.01)
        self.defaultDzSpin.setProperty("value", 0.5)
        self.defaultDzSpin.setObjectName("defaultDzSpin")
        self.gridLayout_4.addWidget(self.defaultDzSpin, 8, 4, 1, 1)
        self.defaultAngleLabel = QtWidgets.QLabel(self.tab_config)
        self.defaultAngleLabel.setEnabled(False)
        self.defaultAngleLabel.setObjectName("defaultAngleLabel")
        self.gridLayout_4.addWidget(
            self.defaultAngleLabel, 8, 5, 1, 1, QtCore.Qt.AlignRight
        )
        self.defaultAngleSpin = QtWidgets.QDoubleSpinBox(self.tab_config)
        self.defaultAngleSpin.setEnabled(False)
        self.defaultAngleSpin.setDecimals(1)
        self.defaultAngleSpin.setSingleStep(0.1)
        self.defaultAngleSpin.setProperty("value", 31.5)
        self.defaultAngleSpin.setObjectName("defaultAngleSpin")
        self.gridLayout_4.addWidget(self.defaultAngleSpin, 8, 6, 1, 1)
        self.reprocessCheckBox = QtWidgets.QCheckBox(self.tab_config)
        self.reprocessCheckBox.setChecked(True)
        self.reprocessCheckBox.setObjectName("reprocessCheckBox")
        self.gridLayout_4.addWidget(self.reprocessCheckBox, 9, 1, 1, 6)
        self.saveMIPsDuringReduceCheckBox = QtWidgets.QCheckBox(self.tab_config)
        self.saveMIPsDuringReduceCheckBox.setChecked(True)
        self.saveMIPsDuringReduceCheckBox.setObjectName("saveMIPsDuringReduceCheckBox")
        self.gridLayout_4.addWidget(self.saveMIPsDuringReduceCheckBox, 10, 1, 1, 5)
        self.confirmOnQuitCheckBox = QtWidgets.QCheckBox(self.tab_config)
        self.confirmOnQuitCheckBox.setChecked(True)
        self.confirmOnQuitCheckBox.setObjectName("confirmOnQuitCheckBox")
        self.gridLayout_4.addWidget(self.confirmOnQuitCheckBox, 11, 1, 1, 5)
        self.genFlashParams = QtWidgets.QPushButton(self.tab_config)
        self.genFlashParams.setObjectName("genFlashParams")
        self.gridLayout_4.addWidget(self.genFlashParams, 12, 1, 1, 6)
        spacerItem24 = QtWidgets.QSpacerItem(
            20, 600, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.gridLayout_4.addItem(spacerItem24, 13, 4, 1, 1)
        self.disableSpimagineCheckBox = QtWidgets.QCheckBox(self.tab_config)
        self.disableSpimagineCheckBox.setChecked(False)
        self.disableSpimagineCheckBox.setObjectName("disableSpimagineCheckBox")
        self.gridLayout_4.addWidget(self.disableSpimagineCheckBox, 14, 1, 1, 6)
        self.previewBackendLabel = QtWidgets.QLabel(self.tab_config)
        self.previewBackendLabel.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter
        )
        self.previewBackendLabel.setObjectName("previewBackendLabel")
        self.gridLayout_4.addWidget(self.previewBackendLabel, 15, 0, 1, 1)
        spacerItem25 = QtWidgets.QSpacerItem(
            20, 600, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.gridLayout_4.addItem(spacerItem25, 16, 4, 1, 1)
        self.watchDirCheckBox = QtWidgets.QCheckBox(self.tab_config)
        self.watchDirCheckBox.setObjectName("watchDirCheckBox")
        self.gridLayout_4.addWidget(self.watchDirCheckBox, 17, 0, 1, 1)
        self.watchDirLineEdit = QtWidgets.QLineEdit(self.tab_config)
        self.watchDirLineEdit.setEnabled(False)
        self.watchDirLineEdit.setText("")
        self.watchDirLineEdit.setReadOnly(True)
        self.watchDirLineEdit.setObjectName("watchDirLineEdit")
        self.gridLayout_4.addWidget(self.watchDirLineEdit, 17, 1, 1, 6)
        self.watchDirToolButton = QtWidgets.QToolButton(self.tab_config)
        self.watchDirToolButton.setEnabled(False)
        self.watchDirToolButton.setObjectName("watchDirToolButton")
        self.gridLayout_4.addWidget(self.watchDirToolButton, 17, 7, 1, 1)
        self.watchModeLabel = QtWidgets.QLabel(self.tab_config)
        self.watchModeLabel.setEnabled(False)
        self.watchModeLabel.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter
        )
        self.watchModeLabel.setObjectName("watchModeLabel")
        self.gridLayout_4.addWidget(self.watchModeLabel, 18, 0, 1, 1)
        self.errorOptOutCheckBox = QtWidgets.QCheckBox(self.tab_config)
        self.errorOptOutCheckBox.setChecked(False)
        self.errorOptOutCheckBox.setObjectName("errorOptOutCheckBox")
        self.gridLayout_4.addWidget(self.errorOptOutCheckBox, 19, 1, 1, 6)
        self.gpusGroupBox = QtWidgets.QGroupBox(self.tab_config)
        self.gpusGroupBox.setTitle("")
        self.gpusGroupBox.setObjectName("gpusGroupBox")
        self.gpuGroupBoxLayout = QtWidgets.QHBoxLayout(self.gpusGroupBox)
        self.gpuGroupBoxLayout.setContentsMargins(11, 2, 11, 2)
        self.gpuGroupBoxLayout.setSpacing(6)
        self.gpuGroupBoxLayout.setObjectName("gpuGroupBoxLayout")
        self.gridLayout_4.addWidget(self.gpusGroupBox, 0, 1, 1, 6)
        self.previewBackendGroupBox = QtWidgets.QGroupBox(self.tab_config)
        self.previewBackendGroupBox.setTitle("")
        self.previewBackendGroupBox.setObjectName("previewBackendGroupBox")
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout(self.previewBackendGroupBox)
        self.horizontalLayout_10.setContentsMargins(8, 8, 8, 8)
        self.horizontalLayout_10.setSpacing(6)
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.prevBackendSpimagineRadio = QtWidgets.QRadioButton(
            self.previewBackendGroupBox
        )
        self.prevBackendSpimagineRadio.setChecked(True)
        self.prevBackendSpimagineRadio.setObjectName("prevBackendSpimagineRadio")
        self.horizontalLayout_10.addWidget(self.prevBackendSpimagineRadio)
        self.prevBackendNapariRadio = QtWidgets.QRadioButton(
            self.previewBackendGroupBox
        )
        self.prevBackendNapariRadio.setObjectName("prevBackendNapariRadio")
        self.horizontalLayout_10.addWidget(self.prevBackendNapariRadio)
        self.prevBackendMatplotlibRadio = QtWidgets.QRadioButton(
            self.previewBackendGroupBox
        )
        self.prevBackendMatplotlibRadio.setObjectName("prevBackendMatplotlibRadio")
        self.horizontalLayout_10.addWidget(self.prevBackendMatplotlibRadio)
        self.gridLayout_4.addWidget(self.previewBackendGroupBox, 15, 1, 1, 6)
        self.watchModeGroupBox = QtWidgets.QGroupBox(self.tab_config)
        self.watchModeGroupBox.setEnabled(False)
        self.watchModeGroupBox.setObjectName("watchModeGroupBox")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.watchModeGroupBox)
        self.horizontalLayout_5.setContentsMargins(4, 4, 4, 6)
        self.horizontalLayout_5.setSpacing(6)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.watchModeAcquisitionRadio = QtWidgets.QRadioButton(self.watchModeGroupBox)
        self.watchModeAcquisitionRadio.setEnabled(False)
        self.watchModeAcquisitionRadio.setChecked(False)
        self.watchModeAcquisitionRadio.setObjectName("watchModeAcquisitionRadio")
        self.horizontalLayout_5.addWidget(self.watchModeAcquisitionRadio)
        self.watchModeServerRadio = QtWidgets.QRadioButton(self.watchModeGroupBox)
        self.watchModeServerRadio.setEnabled(False)
        self.watchModeServerRadio.setChecked(True)
        self.watchModeServerRadio.setObjectName("watchModeServerRadio")
        self.horizontalLayout_5.addWidget(self.watchModeServerRadio)
        self.gridLayout_4.addWidget(self.watchModeGroupBox, 18, 1, 1, 6)
        self.filenamePatternLineEdit = QtWidgets.QLineEdit(self.tab_config)
        self.filenamePatternLineEdit.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.filenamePatternLineEdit.setAlignment(
            QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        self.filenamePatternLineEdit.setReadOnly(False)
        self.filenamePatternLineEdit.setObjectName("filenamePatternLineEdit")
        self.gridLayout_4.addWidget(self.filenamePatternLineEdit, 3, 1, 1, 6)
        self.tabWidget.addTab(self.tab_config, "")
        self.tab_log = QtWidgets.QWidget()
        self.tab_log.setObjectName("tab_log")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.tab_log)
        self.verticalLayout_2.setContentsMargins(11, 11, 11, 11)
        self.verticalLayout_2.setSpacing(6)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.log = QtWidgets.QTextEdit(self.tab_log)
        self.log.setAutoFillBackground(False)
        self.log.setStyleSheet("")
        self.log.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.log.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.log.setLineWidth(2)
        self.log.setReadOnly(True)
        self.log.setObjectName("log")
        self.verticalLayout_2.addWidget(self.log)
        self.tabWidget.addTab(self.tab_log, "")
        self.verticalLayout_4.addWidget(self.tabWidget)
        self.previewProcessButtonFrame = QtWidgets.QFrame(self.centralWidget)
        self.previewProcessButtonFrame.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.previewProcessButtonFrame.setFrameShadow(QtWidgets.QFrame.Plain)
        self.previewProcessButtonFrame.setObjectName("previewProcessButtonFrame")
        self.processButtonLayout = QtWidgets.QHBoxLayout(self.previewProcessButtonFrame)
        self.processButtonLayout.setContentsMargins(11, 0, 11, 0)
        self.processButtonLayout.setSpacing(6)
        self.processButtonLayout.setObjectName("processButtonLayout")
        self.previewButton = QtWidgets.QPushButton(self.previewProcessButtonFrame)
        self.previewButton.setEnabled(True)
        self.previewButton.setMinimumSize(QtCore.QSize(0, 0))
        self.previewButton.setAutoDefault(True)
        self.previewButton.setDefault(False)
        self.previewButton.setFlat(False)
        self.previewButton.setObjectName("previewButton")
        self.processButtonLayout.addWidget(self.previewButton)
        self.previewCRangeLineEdit = QtWidgets.QLineEdit(self.previewProcessButtonFrame)
        self.previewCRangeLineEdit.setMinimumSize(QtCore.QSize(0, 0))
        self.previewCRangeLineEdit.setMaximumSize(QtCore.QSize(70, 16777215))
        self.previewCRangeLineEdit.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.previewCRangeLineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.previewCRangeLineEdit.setObjectName("previewCRangeLineEdit")
        self.processButtonLayout.addWidget(self.previewCRangeLineEdit)
        self.previewTRangeLineEdit = QtWidgets.QLineEdit(self.previewProcessButtonFrame)
        self.previewTRangeLineEdit.setMinimumSize(QtCore.QSize(0, 0))
        self.previewTRangeLineEdit.setMaximumSize(QtCore.QSize(80, 16777215))
        self.previewTRangeLineEdit.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.previewTRangeLineEdit.setEchoMode(QtWidgets.QLineEdit.Normal)
        self.previewTRangeLineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.previewTRangeLineEdit.setCursorMoveStyle(QtCore.Qt.LogicalMoveStyle)
        self.previewTRangeLineEdit.setClearButtonEnabled(False)
        self.previewTRangeLineEdit.setObjectName("previewTRangeLineEdit")
        self.processButtonLayout.addWidget(self.previewTRangeLineEdit)
        self.line = QtWidgets.QFrame(self.previewProcessButtonFrame)
        self.line.setFrameShadow(QtWidgets.QFrame.Plain)
        self.line.setFrameShape(QtWidgets.QFrame.VLine)
        self.line.setObjectName("line")
        self.processButtonLayout.addWidget(self.line)
        self.processButton = QtWidgets.QPushButton(self.previewProcessButtonFrame)
        self.processButton.setMinimumSize(QtCore.QSize(0, 0))
        self.processButton.setObjectName("processButton")
        self.processButtonLayout.addWidget(self.processButton)
        self.processCRangeLineEdit = QtWidgets.QLineEdit(self.previewProcessButtonFrame)
        self.processCRangeLineEdit.setMinimumSize(QtCore.QSize(0, 0))
        self.processCRangeLineEdit.setMaximumSize(QtCore.QSize(70, 16777215))
        self.processCRangeLineEdit.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.processCRangeLineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.processCRangeLineEdit.setObjectName("processCRangeLineEdit")
        self.processButtonLayout.addWidget(self.processCRangeLineEdit)
        self.processTRangeLineEdit = QtWidgets.QLineEdit(self.previewProcessButtonFrame)
        self.processTRangeLineEdit.setMinimumSize(QtCore.QSize(0, 0))
        self.processTRangeLineEdit.setMaximumSize(QtCore.QSize(80, 16777215))
        self.processTRangeLineEdit.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.processTRangeLineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.processTRangeLineEdit.setObjectName("processTRangeLineEdit")
        self.processButtonLayout.addWidget(self.processTRangeLineEdit)
        self.verticalLayout_4.addWidget(self.previewProcessButtonFrame)
        self.progressLayout = QtWidgets.QHBoxLayout()
        self.progressLayout.setSpacing(6)
        self.progressLayout.setObjectName("progressLayout")
        self.progressBar = QtWidgets.QProgressBar(self.centralWidget)
        self.progressBar.setMinimumSize(QtCore.QSize(0, 0))
        self.progressBar.setStyleSheet(
            "QProgressBar {\n"
            "  border: 1px solid grey;\n"
            "  border-radius: 3px;\n"
            "  height: 20px;\n"
            "  margin: 0px 0px 0px 5px;\n"
            "}\n"
            "\n"
            "QProgressBar::chunk:horizontal {\n"
            "  background: qlineargradient(x1: 0, y1: 0.5, x2: 1, y2: 0.5, stop: 0 #484DE7, stop: 1 #787DFF);\n"
            "}"
        )
        self.progressBar.setProperty("value", 0)
        self.progressBar.setTextVisible(False)
        self.progressBar.setObjectName("progressBar")
        self.progressLayout.addWidget(self.progressBar)
        self.clock = QtWidgets.QLCDNumber(self.centralWidget)
        self.clock.setMinimumSize(QtCore.QSize(0, 0))
        font = QtGui.QFont()
        font.setBold(False)
        font.setWeight(50)
        self.clock.setFont(font)
        self.clock.setStyleSheet("")
        self.clock.setFrameShape(QtWidgets.QFrame.WinPanel)
        self.clock.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.clock.setLineWidth(1)
        self.clock.setMidLineWidth(0)
        self.clock.setSmallDecimalPoint(True)
        self.clock.setDigitCount(8)
        self.clock.setMode(QtWidgets.QLCDNumber.Dec)
        self.clock.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.clock.setObjectName("clock")
        self.progressLayout.addWidget(self.clock)
        self.verticalLayout_4.addLayout(self.progressLayout)
        Main_GUI.setCentralWidget(self.centralWidget)
        self.menuBar = QtWidgets.QMenuBar(Main_GUI)
        self.menuBar.setGeometry(QtCore.QRect(0, 0, 617, 22))
        self.menuBar.setObjectName("menuBar")
        self.menuFile = QtWidgets.QMenu(self.menuBar)
        self.menuFile.setObjectName("menuFile")
        self.menuView = QtWidgets.QMenu(self.menuBar)
        self.menuView.setObjectName("menuView")
        self.menuProcess = QtWidgets.QMenu(self.menuBar)
        self.menuProcess.setObjectName("menuProcess")
        self.menuLLSpy = QtWidgets.QMenu(self.menuBar)
        self.menuLLSpy.setObjectName("menuLLSpy")
        self.menuTools = QtWidgets.QMenu(self.menuBar)
        self.menuTools.setObjectName("menuTools")
        Main_GUI.setMenuBar(self.menuBar)
        self.mainToolBar = QtWidgets.QToolBar(Main_GUI)
        self.mainToolBar.setEnabled(True)
        self.mainToolBar.setObjectName("mainToolBar")
        Main_GUI.addToolBar(QtCore.Qt.TopToolBarArea, self.mainToolBar)
        self.statusBar = QtWidgets.QStatusBar(Main_GUI)
        self.statusBar.setMinimumSize(QtCore.QSize(0, 30))
        self.statusBar.setSizeGripEnabled(True)
        self.statusBar.setObjectName("statusBar")
        Main_GUI.setStatusBar(self.statusBar)
        self.actionQuit = QtWidgets.QAction(Main_GUI)
        self.actionQuit.setObjectName("actionQuit")
        self.actionPreview = QtWidgets.QAction(Main_GUI)
        self.actionPreview.setObjectName("actionPreview")
        self.actionRun = QtWidgets.QAction(Main_GUI)
        self.actionRun.setObjectName("actionRun")
        self.actionAbort = QtWidgets.QAction(Main_GUI)
        self.actionAbort.setEnabled(False)
        self.actionAbort.setObjectName("actionAbort")
        self.actionOpen_LLSdir = QtWidgets.QAction(Main_GUI)
        self.actionOpen_LLSdir.setObjectName("actionOpen_LLSdir")
        self.actionSave_Settings_as_Default = QtWidgets.QAction(Main_GUI)
        self.actionSave_Settings_as_Default.setObjectName(
            "actionSave_Settings_as_Default"
        )
        self.actionLoad_Default_Settings = QtWidgets.QAction(Main_GUI)
        self.actionLoad_Default_Settings.setObjectName("actionLoad_Default_Settings")
        self.actionReduce_to_Raw = QtWidgets.QAction(Main_GUI)
        self.actionReduce_to_Raw.setObjectName("actionReduce_to_Raw")
        self.actionCompress_Folder = QtWidgets.QAction(Main_GUI)
        self.actionCompress_Folder.setObjectName("actionCompress_Folder")
        self.actionDecompress_Folder = QtWidgets.QAction(Main_GUI)
        self.actionDecompress_Folder.setObjectName("actionDecompress_Folder")
        self.actionConcatenate = QtWidgets.QAction(Main_GUI)
        self.actionConcatenate.setObjectName("actionConcatenate")
        self.actionRename_Scripted = QtWidgets.QAction(Main_GUI)
        self.actionRename_Scripted.setObjectName("actionRename_Scripted")
        self.actionClose_All_Previews = QtWidgets.QAction(Main_GUI)
        self.actionClose_All_Previews.setObjectName("actionClose_All_Previews")
        self.actionAbout_LLSpy = QtWidgets.QAction(Main_GUI)
        self.actionAbout_LLSpy.setObjectName("actionAbout_LLSpy")
        self.actionFreeze = QtWidgets.QAction(Main_GUI)
        self.actionFreeze.setObjectName("actionFreeze")
        self.actionHelp = QtWidgets.QAction(Main_GUI)
        self.actionHelp.setObjectName("actionHelp")
        self.actionCamera_Calibration = QtWidgets.QAction(Main_GUI)
        self.actionCamera_Calibration.setObjectName("actionCamera_Calibration")
        self.actionRename_Iters = QtWidgets.QAction(Main_GUI)
        self.actionRename_Iters.setObjectName("actionRename_Iters")
        self.actionUndo_Rename_Iters = QtWidgets.QAction(Main_GUI)
        self.actionUndo_Rename_Iters.setObjectName("actionUndo_Rename_Iters")
        self.actionReveal = QtWidgets.QAction(Main_GUI)
        self.actionReveal.setObjectName("actionReveal")
        self.actionMerge_MIPs_from_folder = QtWidgets.QAction(Main_GUI)
        self.actionMerge_MIPs_from_folder.setObjectName("actionMerge_MIPs_from_folder")
        self.menuFile.addAction(self.actionOpen_LLSdir)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionSave_Settings_as_Default)
        self.menuFile.addAction(self.actionLoad_Default_Settings)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionQuit)
        self.menuView.addSeparator()
        self.menuView.addAction(self.actionClose_All_Previews)
        self.menuProcess.addAction(self.actionPreview)
        self.menuProcess.addAction(self.actionRun)
        self.menuProcess.addAction(self.actionAbort)
        self.menuProcess.addSeparator()
        self.menuProcess.addAction(self.actionRename_Iters)
        self.menuProcess.addAction(self.actionUndo_Rename_Iters)
        self.menuLLSpy.addAction(self.actionAbout_LLSpy)
        self.menuLLSpy.addAction(self.actionHelp)
        self.menuTools.addAction(self.actionCamera_Calibration)
        self.menuTools.addAction(self.actionMerge_MIPs_from_folder)
        self.menuBar.addAction(self.menuFile.menuAction())
        self.menuBar.addAction(self.menuView.menuAction())
        self.menuBar.addAction(self.menuProcess.menuAction())
        self.menuBar.addAction(self.menuTools.menuAction())
        self.menuBar.addAction(self.menuLLSpy.menuAction())
        self.mainToolBar.addAction(self.actionReduce_to_Raw)
        self.mainToolBar.addAction(self.actionCompress_Folder)
        self.mainToolBar.addAction(self.actionDecompress_Folder)
        self.mainToolBar.addAction(self.actionFreeze)
        self.mainToolBar.addAction(self.actionConcatenate)
        self.mainToolBar.addAction(self.actionRename_Scripted)
        self.mainToolBar.addAction(self.actionReveal)
        self.camParamTiffLabel.setBuddy(self.camParamTiffLineEdit)
        self.autocropPadLabel.setBuddy(self.autocropPadSpinBox)
        self.RegCalibPathLabel.setBuddy(self.RegCalibPathLineEdit)
        self.RegCalib_channelRefModeLabel.setBuddy(self.RegCalib_channelRefModeCombo)
        self.RegFilePathLabel.setBuddy(self.RegFilePath)
        self.RegCalib_channelRefLabel.setBuddy(self.RegCalib_channelRefCombo)
        self.BeadThresholdLabel.setBuddy(self.RegBeadThreshSpin)
        self.RegMinBeadsLabel.setBuddy(self.RegMinBeadsSpin)
        self.filenamePatternLabel.setBuddy(self.cudaDeconvPathLineEdit)
        self.cudaDeconvPathLabel_2.setBuddy(self.cudaDeconvPathLineEdit)
        self.cudaDeconvPathLabel.setBuddy(self.cudaDeconvPathLineEdit)
        self.otfFolderPathLabel.setBuddy(self.otfFolderLineEdit)
        self.previewBackendLabel.setBuddy(self.otfFolderLineEdit)

        self.retranslateUi(Main_GUI)
        self.tabWidget.setCurrentIndex(0)
        self.processingToolBox.setCurrentIndex(2)
        self.compressTypeCombo.setCurrentIndex(-1)
        self.RegCalib_channelRefModeCombo.setCurrentIndex(-1)
        self.actionQuit.triggered["bool"].connect(Main_GUI.close)
        self.backgroundRollingRadio.toggled["bool"].connect(
            self.backgroundRollingSpinBox.setEnabled
        )
        self.backgroundFixedRadio.toggled["bool"].connect(
            self.backgroundFixedSpinBox.setEnabled
        )
        self.cropManualRadio.toggled["bool"].connect(self.cropWidthSpinBox.setEnabled)
        self.cropManualRadio.toggled["bool"].connect(self.cropShiftSpinBox.setEnabled)
        self.cropManualRadio.toggled["bool"].connect(self.cropWidthLabel.setEnabled)
        self.cropManualRadio.toggled["bool"].connect(self.cropShiftLabel.setEnabled)
        self.rotateOverrideCheckBox.toggled["bool"].connect(
            self.rotateOverrideSpinBox.setEnabled
        )
        self.camcorCheckBox.toggled["bool"].connect(self.camcorTargetCombo.setEnabled)
        self.watchDirCheckBox.toggled["bool"].connect(
            self.watchDirToolButton.setEnabled
        )
        self.watchDirCheckBox.toggled["bool"].connect(self.watchDirLineEdit.setEnabled)
        self.useBundledBinariesCheckBox.toggled["bool"].connect(
            self.cudaDeconvPathLineEdit.setHidden
        )
        self.useBundledBinariesCheckBox.toggled["bool"].connect(
            self.cudaDeconvPathLabel.setHidden
        )
        self.cropAutoRadio.toggled["bool"].connect(self.autocropPadLabel.setEnabled)
        self.cropAutoRadio.toggled["bool"].connect(self.autocropPadSpinBox.setEnabled)
        self.saveDeskewedCheckBox.toggled["bool"].connect(
            self.deconSaveMIPSLabel_2.setEnabled
        )
        self.saveDeskewedCheckBox.toggled["bool"].connect(
            self.deskewedXMIPCheckBox.setEnabled
        )
        self.saveDeskewedCheckBox.toggled["bool"].connect(
            self.deskewedYMIPCheckBox.setEnabled
        )
        self.saveDeskewedCheckBox.toggled["bool"].connect(
            self.deskewedZMIPCheckBox.setEnabled
        )
        self.watchDirCheckBox.toggled["bool"].connect(self.watchModeLabel.setEnabled)
        self.watchDirCheckBox.toggled["bool"].connect(self.watchModeGroupBox.setEnabled)
        self.watchDirCheckBox.toggled["bool"].connect(
            self.watchModeAcquisitionRadio.setEnabled
        )
        self.watchDirCheckBox.toggled["bool"].connect(
            self.watchModeServerRadio.setEnabled
        )
        self.useBundledBinariesCheckBox.toggled["bool"].connect(
            self.cudaDeconvPathToolButton.setHidden
        )
        self.RegAutoThreshCheckbox.toggled["bool"].connect(
            self.RegBeadThreshSpin.setDisabled
        )
        self.RegAutoThreshCheckbox.toggled["bool"].connect(
            self.RegMinBeadsLabel.setEnabled
        )
        self.RegAutoThreshCheckbox.toggled["bool"].connect(
            self.RegMinBeadsSpin.setEnabled
        )
        self.allowNoSettingsCheckBox.toggled["bool"].connect(
            self.defaultValuesLabel.setEnabled
        )
        self.allowNoSettingsCheckBox.toggled["bool"].connect(
            self.defaultDxSpin.setEnabled
        )
        self.allowNoSettingsCheckBox.toggled["bool"].connect(
            self.defaultDxLabel.setEnabled
        )
        self.allowNoSettingsCheckBox.toggled["bool"].connect(
            self.defaultDzLabel.setEnabled
        )
        self.allowNoSettingsCheckBox.toggled["bool"].connect(
            self.defaultDzSpin.setEnabled
        )
        self.allowNoSettingsCheckBox.toggled["bool"].connect(
            self.defaultAngleLabel.setEnabled
        )
        self.allowNoSettingsCheckBox.toggled["bool"].connect(
            self.defaultAngleSpin.setEnabled
        )
        QtCore.QMetaObject.connectSlotsByName(Main_GUI)

    def retranslateUi(self, Main_GUI):
        _translate = QtCore.QCoreApplication.translate
        Main_GUI.setWindowTitle(_translate("Main_GUI", "Main_GUI"))
        self.listbox.setToolTip(
            _translate(
                "Main_GUI",
                "Drag and drop LLS experiment folders\n"
                "(containing a Settings.txt file) here, to\n"
                "add to the processing queue. Select\n"
                "and press delete to remove.\n"
                "Press process button below when ready.",
            )
        )
        item = self.listbox.horizontalHeaderItem(0)
        item.setText(_translate("Main_GUI", "basename"))
        item = self.listbox.horizontalHeaderItem(1)
        item.setText(_translate("Main_GUI", "nC"))
        item = self.listbox.horizontalHeaderItem(2)
        item.setText(_translate("Main_GUI", "nT"))
        item = self.listbox.horizontalHeaderItem(3)
        item.setText(_translate("Main_GUI", "nX"))
        item = self.listbox.horizontalHeaderItem(4)
        item.setText(_translate("Main_GUI", "nY"))
        item = self.listbox.horizontalHeaderItem(5)
        item.setText(_translate("Main_GUI", "nZ"))
        item = self.listbox.horizontalHeaderItem(6)
        item.setText(_translate("Main_GUI", "desQ"))
        self.camcorGroupBox.setTitle(_translate("Main_GUI", "Camera Correction"))
        self.camcorCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                "Perform per-pixel residual electron correction for\n"
                "Flash4.0 using CamaraParam Tiff file selected on\n"
                "config tab.  See help for details",
            )
        )
        self.camcorCheckBox.setText(_translate("Main_GUI", "Do Flash Correction"))
        self.camcorTargetCombo.setToolTip(
            _translate(
                "Main_GUI",
                "Target for camera correction (performace may vary from system to system)",
            )
        )
        self.camcorTargetCombo.setItemText(0, _translate("Main_GUI", "CPU"))
        self.camcorTargetCombo.setItemText(1, _translate("Main_GUI", "Parallel"))
        self.camcorTargetCombo.setItemText(2, _translate("Main_GUI", "CUDA"))
        self.medianFilterCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                "Perform selective median filter correction\n"
                "on particularly noisy pixels.\n"
                "As done in Amat et al 2015",
            )
        )
        self.medianFilterCheckBox.setText(_translate("Main_GUI", "Do Median Filter"))
        self.saveCamCorrectedCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                "Save the Raw-Corrected files after processing\n"
                "(otherwise corrected files will be deleted)",
            )
        )
        self.saveCamCorrectedCheckBox.setText(_translate("Main_GUI", "Save Corrected"))
        self.camParamTiffToolButton.setText(_translate("Main_GUI", "..."))
        self.camParamTiffLabel.setText(_translate("Main_GUI", "CameraParam Tiff"))
        self.camParamTiffLineEdit.setPlaceholderText(
            _translate("Main_GUI", "path to TIFF file with measured camera parameters")
        )
        self.trimEdgesGroupBox.setToolTip(
            _translate(
                "Main_GUI",
                "Trims N pixels from the corresponding volume edge.\n"
                "This is BEFORE processing, mostly to eliminate\n"
                "bright-edge camera artifacts prior to deskewing",
            )
        )
        self.trimEdgesGroupBox.setTitle(_translate("Main_GUI", "Trim Edges"))
        self.trimZ0Label.setText(_translate("Main_GUI", "Trim Z first"))
        self.trimY0Label.setText(_translate("Main_GUI", "Trim Y Top"))
        self.trimZ1Label.setText(_translate("Main_GUI", "Trim Z last"))
        self.trimX0Label.setText(_translate("Main_GUI", "Trim X Left"))
        self.trimY1Label.setText(_translate("Main_GUI", "Trim Y Bottom"))
        self.trimX1Label.setText(_translate("Main_GUI", "Trim X Right"))
        self.backgroundGroupBox.setTitle(
            _translate("Main_GUI", "Background Subtraction")
        )
        self.backgroundAutoRadio.setToolTip(
            _translate(
                "Main_GUI",
                "Use the mode intensity value from the second plane in\n"
                "the Z stack for each channel for background subtraction.",
            )
        )
        self.backgroundAutoRadio.setText(_translate("Main_GUI", "Autodetect"))
        self.backgroundFixedRadio.setToolTip(
            _translate(
                "Main_GUI", "Use specified intensity value for background subtraction."
            )
        )
        self.backgroundFixedRadio.setText(_translate("Main_GUI", "Fixed value"))
        self.backgroundRollingRadio.setToolTip(
            _translate("Main_GUI", "Not implemented")
        )
        self.backgroundRollingRadio.setText(
            _translate("Main_GUI", "Rolling Ball Radius:")
        )
        self.processingToolBox.setItemText(
            self.processingToolBox.indexOf(self.tool_preprocess),
            _translate("Main_GUI", "Pre-Processing"),
        )
        self.doDeconGroupBox.setTitle(_translate("Main_GUI", "Do Deconvolution"))
        self.iterationsLabel.setToolTip(
            _translate("Main_GUI", "Number of deconvolution iterations")
        )
        self.iterationsLabel.setText(_translate("Main_GUI", "Iterations:"))
        self.iterationsSpinBox.setToolTip(
            _translate("Main_GUI", "Number of deconvolution iterations")
        )
        self.apodizeLabel.setToolTip(
            _translate(
                "Main_GUI", "# of pixels to soften edge with prior to deconvolution"
            )
        )
        self.apodizeLabel.setText(_translate("Main_GUI", "nApodize:"))
        self.apodizeSpinBox.setToolTip(
            _translate(
                "Main_GUI", "# of pixels to soften edge with prior to deconvolution"
            )
        )
        self.zblendLabel.setToolTip(
            _translate(
                "Main_GUI",
                "# of top and bottom sections to blend in\n" "to reduce axial ringing",
            )
        )
        self.zblendLabel.setText(_translate("Main_GUI", "nZblend"))
        self.zblendSpinBox.setToolTip(
            _translate(
                "Main_GUI",
                "# of top and bottom sections to blend in\n" "to reduce axial ringing",
            )
        )
        self.saveDeconvolvedCheckBox.setText(_translate("Main_GUI", "Save Stacks"))
        self.deconvolvedMIPFrame.setToolTip(
            _translate(
                "Main_GUI",
                "Save maximum-intensity-projection\n" "images along the specified axis",
            )
        )
        self.deconSaveMIPSLabel.setText(_translate("Main_GUI", "Save MIPs:"))
        self.deconXMIPCheckBox.setText(_translate("Main_GUI", "X"))
        self.deconYMIPCheckBox.setText(_translate("Main_GUI", "Y"))
        self.deconZMIPCheckBox.setText(_translate("Main_GUI", "Z"))
        self.deconvolvedBitDepthCombo.setToolTip(
            _translate("Main_GUI", "Bit depth of resulting deconvolved images.")
        )
        self.deconvolvedBitDepthCombo.setCurrentText(_translate("Main_GUI", "16-bit"))
        self.deconvolvedBitDepthCombo.setItemText(0, _translate("Main_GUI", "16-bit"))
        self.deconvolvedBitDepthCombo.setItemText(1, _translate("Main_GUI", "32-bit"))
        self.deskewedGroupBox.setTitle(_translate("Main_GUI", "Raw Deskewed"))
        self.deskewedMIPFrame.setToolTip(
            _translate(
                "Main_GUI",
                "Save maximum-intensity-projection\n" "images along the specified axis",
            )
        )
        self.deconSaveMIPSLabel_2.setText(_translate("Main_GUI", "Save MIPs:"))
        self.deskewedXMIPCheckBox.setText(_translate("Main_GUI", "X"))
        self.deskewedYMIPCheckBox.setText(_translate("Main_GUI", "Y"))
        self.deskewedZMIPCheckBox.setText(_translate("Main_GUI", "Z"))
        self.saveDeskewedCheckBox.setToolTip(
            _translate("Main_GUI", "Save raw deskewed data.")
        )
        self.saveDeskewedCheckBox.setText(_translate("Main_GUI", "Save Deskwed"))
        self.deskewedBitDepthCombo.setCurrentText(_translate("Main_GUI", "16-bit"))
        self.deskewedBitDepthCombo.setItemText(0, _translate("Main_GUI", "16-bit"))
        self.deskewedBitDepthCombo.setItemText(1, _translate("Main_GUI", "32-bit"))
        self.deconJoinMIPCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                "Join maximum intensity projection images\n"
                "into a single multi-dimensional (XYZCT)\n"
                "file that can be viewed easily in Fiji/ImageJ",
            )
        )
        self.deconJoinMIPCheckBox.setText(
            _translate("Main_GUI", "Join MIP files into single hyperstack")
        )
        self.useLZWCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                "Enabling this will reduce file sizes, but increase the time it takes to open images",
            )
        )
        self.useLZWCheckBox.setText(_translate("Main_GUI", "Use LZW compression"))
        self.dupRevStackCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                "Duplicate reversed stack prior to decon to reduce Z ringing",
            )
        )
        self.dupRevStackCheckBox.setText(
            _translate("Main_GUI", "Duplicate reversed stack (reduce axial ringing)")
        )
        self.padValLabel.setToolTip(
            _translate("Main_GUI", "Value to pad image with when deskewing")
        )
        self.padValLabel.setText(_translate("Main_GUI", "Pad Value"))
        self.padValSpinBox.setToolTip(
            _translate("Main_GUI", "Value to pad image with when deskewing")
        )
        self.processingToolBox.setItemText(
            self.processingToolBox.indexOf(self.tool_deconvolution),
            _translate("Main_GUI", "Deskew/Deconvolution/Saving"),
        )
        self.croppingGroupBox.setTitle(_translate("Main_GUI", "Crop Result"))
        self.cropAutoRadio.setToolTip(
            _translate(
                "Main_GUI",
                "Auto-detect features in the image and\n"
                "crop to center around features.  Pad\n"
                "value adds extra space around features.",
            )
        )
        self.cropAutoRadio.setText(_translate("Main_GUI", "AutoCrop"))
        self.autocropPadLabel.setText(_translate("Main_GUI", "Pad"))
        self.autocropPadSpinBox.setToolTip(
            _translate(
                "Main_GUI",
                "Auto-detect features in the image and\n"
                "crop to center around features.  Pad\n"
                "value adds extra space around features.",
            )
        )
        self.cropManualRadio.setToolTip(
            _translate(
                "Main_GUI",
                "Manually specify the width of the resulting\n"
                "image after deskewing.  Use shift to change\n"
                "the middle position.  Use preview button\n"
                "below to check result.",
            )
        )
        self.cropManualRadio.setText(_translate("Main_GUI", "Manual"))
        self.cropManualGroupBox.setToolTip(
            _translate(
                "Main_GUI",
                "Manually specify the width of the resulting\n"
                "image after deskewing.  Use shift to change\n"
                "the middle position.  Use preview button\n"
                "below to check result.",
            )
        )
        self.cropWidthLabel.setText(_translate("Main_GUI", "Width:"))
        self.cropShiftLabel.setText(_translate("Main_GUI", "Shift:"))
        self.rotateGroupBox.setToolTip(
            _translate(
                "Main_GUI",
                "Transform final image around the\n"
                "Y-axis so that the Z-axis in the\n"
                "image is orthogonal to the coverslip.\n"
                "This entails interpolation.",
            )
        )
        self.rotateGroupBox.setTitle(
            _translate("Main_GUI", "Rotate to coverslip coordinates")
        )
        self.rotateReverseCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                "Specify that direction of stage travel\n"
                "during stage-scanning is reversed\n"
                "from conventional.",
            )
        )
        self.rotateReverseCheckBox.setText(_translate("Main_GUI", "Reverse"))
        self.rotateOverrideCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                "Override the angle of rotation.  Otherwise,\n"
                "use the angle value detected in the settings\n"
                "file (the same value used for deskewing).",
            )
        )
        self.rotateOverrideCheckBox.setText(_translate("Main_GUI", "Override angle:"))
        self.rotateOverrideSpinBox.setToolTip(
            _translate(
                "Main_GUI",
                "Override the angle of rotation.  Otherwise,\n"
                "use the angle value detected in the settings\n"
                "file (the same value used for deskewing).",
            )
        )
        self.doRegistrationGroupBox.setToolTip(
            _translate(
                "Main_GUI",
                "Use provided fiducial-based calibration\n"
                "dataset (e.g. tetraspeck bead images)\n"
                "to register different channels of a\n"
                "multi-channel dataset.",
            )
        )
        self.doRegistrationGroupBox.setTitle(
            _translate("Main_GUI", "Do Channel Registration")
        )
        self.channelRefLabel.setToolTip(
            _translate(
                "Main_GUI",
                "Reference channel to which to register\n"
                "(this channel will not change)",
            )
        )
        self.channelRefLabel.setText(_translate("Main_GUI", "Ref Wave:"))
        self.RegProcessChannelRefCombo.setToolTip(
            _translate(
                "Main_GUI",
                "Reference channel to which to register\n"
                "(this channel will not change)",
            )
        )
        self.channelRefModeLabel.setToolTip(
            _translate(
                "Main_GUI",
                "Type of registration to perform:\n"
                "Translation=shift only\n"
                "Rigid=Shift and rotation\n"
                "Similarity=Rigid plus scaling\n"
                "Affine=Translation, Rotation, Scaling, Shear\n"
                "2-step=Affine in XY, Rigid in Z\n"
                "CPD=Coherent Point Drift algorithm\n"
                "(Myronenko, 2010)",
            )
        )
        self.channelRefModeLabel.setText(_translate("Main_GUI", "Mode:"))
        self.RegProcessChannelRefModeCombo.setToolTip(
            _translate(
                "Main_GUI",
                "Type of registration to perform:\n"
                "Translation=shift only\n"
                "Rigid=Shift and rotation\n"
                "Similarity=Rigid plus scaling\n"
                "Affine=Translation, Rotation, Scaling, Shear\n"
                "2-step=Affine in XY, Rigid in Z\n"
                "CPD=Coherent Point Drift algorithm\n"
                "(Myronenko, 2010)",
            )
        )
        self.RegProcessLoadRegFile.setText(_translate("Main_GUI", "Use RegFile"))
        self.RegProcessPathLabel.setToolTip(
            _translate(
                "Main_GUI",
                "Specify folder with calibration (e.g. tetraspeck\n"
                "bead) images acquired in each channel.",
            )
        )
        self.RegProcessPathLabel.setText(_translate("Main_GUI", "Calibration:"))
        self.RegProcessPathLineEdit.setToolTip(
            _translate(
                "Main_GUI",
                "Specify folder with calibration (e.g. tetraspeck\n"
                "bead) images acquired in each channel.",
            )
        )
        self.RegProcessPathLineEdit.setPlaceholderText(
            _translate("Main_GUI", " registration file or fiducial dataset...")
        )
        self.RegProcessPathPushButton.setText(_translate("Main_GUI", "Use Dataset"))
        self.discardUnregisteredCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                "Specify that direction of stage travel\n"
                "during stage-scanning is reversed\n"
                "from conventional.",
            )
        )
        self.discardUnregisteredCheckBox.setText(
            _translate("Main_GUI", "Discard un-registered files")
        )
        self.bleachCorrectionCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                "Modify intensity values of timelapse data to\n"
                "minimize the appearance of photobleaching.",
            )
        )
        self.bleachCorrectionCheckBox.setText(
            _translate("Main_GUI", "Do Bleach Correction")
        )
        self.compressRawCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                "Compress the raw data files\n" "after processing to save space.",
            )
        )
        self.compressRawCheckBox.setText(_translate("Main_GUI", "Compress Raw Data"))
        self.label.setText(_translate("Main_GUI", "Type:"))
        self.processingToolBox.setItemText(
            self.processingToolBox.indexOf(self.tool_postprocess),
            _translate("Main_GUI", "Post-Processing"),
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_process), _translate("Main_GUI", "Process")
        )
        self.RegCalib_channelRefModeCombo.setToolTip(
            _translate(
                "Main_GUI",
                "Type of registration to perform:\n"
                "Translation=shift only\n"
                "Rigid=Shift and rotation\n"
                "Similarity=Rigid plus scaling\n"
                "Affine=Translation, Rotation, Scaling, Shear\n"
                "2-step=Affine in XY, Rigid in Z\n"
                "CPD=Coherent Point Drift algorithm\n"
                "(Myronenko, 2010)",
            )
        )
        self.RegCalibPathLineEdit.setToolTip(
            _translate(
                "Main_GUI",
                "Specify folder with calibration (e.g. tetraspeck\n"
                "bead) images acquired in each channel.",
            )
        )
        self.RegCalibPathLineEdit.setPlaceholderText(
            _translate("Main_GUI", " Folder with mult-channel fiducial stacks...")
        )
        self.RegCalib_channelRefCombo.setToolTip(
            _translate(
                "Main_GUI",
                "Reference channel to which to register\n"
                "(this channel will not change)",
            )
        )
        self.RegCalibRefChannelsLabel.setToolTip(
            _translate(
                "Main_GUI",
                "Reference channel to which to register\n"
                "(this channel will not change)",
            )
        )
        self.RegCalibRefChannelsLabel.setText(_translate("Main_GUI", "Ref Channels:"))
        self.GenerateRegFileButton.setText(
            _translate("Main_GUI", "Generate Registration File")
        )
        self.RegCalibPathLabel.setToolTip(
            _translate(
                "Main_GUI",
                "Specify folder with calibration (e.g. tetraspeck\n"
                "bead) images acquired in each channel.",
            )
        )
        self.RegCalibPathLabel.setText(_translate("Main_GUI", "Fiducial Data:"))
        self.RegCalib_channelRefModeLabel.setToolTip(
            _translate(
                "Main_GUI",
                "Type of registration to perform:\n"
                "Translation=shift only\n"
                "Rigid=Shift and rotation\n"
                "Similarity=Rigid plus scaling\n"
                "Affine=Translation, Rotation, Scaling, Shear\n"
                "2-step=Affine in XY, Rigid in Z\n"
                "CPD=Coherent Point Drift algorithm\n"
                "(Myronenko, 2010)",
            )
        )
        self.RegCalib_channelRefModeLabel.setText(_translate("Main_GUI", "Mode:"))
        self.RegCalibPathLoadButton.setText(_translate("Main_GUI", "load"))
        self.RegFilePathLoadButton.setText(_translate("Main_GUI", "load"))
        self.RegFilePathLabel.setToolTip(
            _translate(
                "Main_GUI",
                "Specify folder with calibration (e.g. tetraspeck\n"
                "bead) images acquired in each channel.",
            )
        )
        self.RegFilePathLabel.setText(_translate("Main_GUI", "Registration File:"))
        self.RegFilePath.setToolTip(
            _translate(
                "Main_GUI",
                "Specify folder with calibration (e.g. tetraspeck\n"
                "bead) images acquired in each channel.",
            )
        )
        self.RegFilePath.setPlaceholderText(
            _translate("Main_GUI", " Registration Tform file...")
        )
        self.RegCalibPreviewButton.setText(
            _translate("Main_GUI", "Register Fiducial Data")
        )
        self.RegCalib_channelRefLabel.setToolTip(
            _translate(
                "Main_GUI",
                "Reference channel to which to register\n"
                "(this channel will not change)",
            )
        )
        self.RegCalib_channelRefLabel.setText(_translate("Main_GUI", "Ref Channel:"))
        self.BeadThresholdLabel.setToolTip(
            _translate(
                "Main_GUI",
                "Specify folder with calibration (e.g. tetraspeck\n"
                "bead) images acquired in each channel.",
            )
        )
        self.BeadThresholdLabel.setText(_translate("Main_GUI", "Bead Threshold:"))
        self.RegMinBeadsLabel.setText(_translate("Main_GUI", "Min number of beads:"))
        self.RegAutoThreshCheckbox.setText(_translate("Main_GUI", "Autodetect"))
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_registration),
            _translate("Main_GUI", "Registration"),
        )
        self.filenamePatternLabel.setText(_translate("Main_GUI", "filename pattern:"))
        self.cudaDeconvPathLabel_2.setToolTip(
            _translate(
                "Main_GUI",
                "Toggle the GPUs that you want to use for processing.\n"
                " Work will be distributed among them",
            )
        )
        self.cudaDeconvPathLabel_2.setText(_translate("Main_GUI", "GPUs"))
        self.useBundledBinariesCheckBox.setText(
            _translate("Main_GUI", "Use bundled cudaDeconv binary")
        )
        self.cudaDeconvPathLabel.setText(_translate("Main_GUI", "cudaDeconv binary:"))
        self.cudaDeconvPathLineEdit.setText(
            _translate("Main_GUI", "/usr/local/cudaDeconv")
        )
        self.cudaDeconvPathLineEdit.setPlaceholderText(
            _translate("Main_GUI", "path to cudaDeconv binary")
        )
        self.cudaDeconvPathToolButton.setText(_translate("Main_GUI", "..."))
        self.otfFolderPathLabel.setText(_translate("Main_GUI", "OTF directory:"))
        self.otfFolderLineEdit.setPlaceholderText(
            _translate("Main_GUI", "path to directory with PSFs/OTFs")
        )
        self.otfFolderToolButton.setText(_translate("Main_GUI", "..."))
        self.allowNoSettingsCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                'The "reduce to raw" function deletes all\n'
                "processed data, leaving only the original\n"
                "raw data.  This option retains any MIP\n"
                "folders found, as a smaller-sized\n"
                "preview of the dataset for later review.",
            )
        )
        self.allowNoSettingsCheckBox.setText(
            _translate(
                "Main_GUI",
                "allow folders without Settings.txt files (will require input)",
            )
        )
        self.defaultValuesLabel.setText(_translate("Main_GUI", "default values:"))
        self.defaultDxLabel.setText(_translate("Main_GUI", "dx:"))
        self.defaultDzLabel.setText(_translate("Main_GUI", "dz:"))
        self.defaultAngleLabel.setText(_translate("Main_GUI", "angle:"))
        self.reprocessCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                'The "reduce to raw" function deletes all\n'
                "processed data, leaving only the original\n"
                "raw data.  This option retains any MIP\n"
                "folders found, as a smaller-sized\n"
                "preview of the dataset for later review.",
            )
        )
        self.reprocessCheckBox.setText(
            _translate("Main_GUI", "Reprocess folders that have already been processed")
        )
        self.saveMIPsDuringReduceCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                'The "reduce to raw" function deletes all\n'
                "processed data, leaving only the original\n"
                "raw data.  This option retains any MIP\n"
                "folders found, as a smaller-sized\n"
                "preview of the dataset for later review.",
            )
        )
        self.saveMIPsDuringReduceCheckBox.setText(
            _translate("Main_GUI", 'Save MIP folder during "Reduce to Raw"')
        )
        self.confirmOnQuitCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                'The "reduce to raw" function deletes all\n'
                "processed data, leaving only the original\n"
                "raw data.  This option retains any MIP\n"
                "folders found, as a smaller-sized\n"
                "preview of the dataset for later review.",
            )
        )
        self.confirmOnQuitCheckBox.setText(
            _translate("Main_GUI", "Warn when quitting with unprocessed items")
        )
        self.genFlashParams.setText(
            _translate("Main_GUI", "Generate Camera Calibration File")
        )
        self.disableSpimagineCheckBox.setText(
            _translate(
                "Main_GUI", "Disable spimagine import (in case of WinError on Preview)"
            )
        )
        self.previewBackendLabel.setText(_translate("Main_GUI", "Preview Type"))
        self.watchDirCheckBox.setText(_translate("Main_GUI", "Watch Directory:"))
        self.watchDirLineEdit.setPlaceholderText(
            _translate(
                "Main_GUI",
                "New items in watched folder will be automatically processed.",
            )
        )
        self.watchDirToolButton.setText(_translate("Main_GUI", "..."))
        self.watchModeLabel.setText(_translate("Main_GUI", "Watch Mode:"))
        self.errorOptOutCheckBox.setToolTip(
            _translate(
                "Main_GUI",
                'The "reduce to raw" function deletes all\n'
                "processed data, leaving only the original\n"
                "raw data.  This option retains any MIP\n"
                "folders found, as a smaller-sized\n"
                "preview of the dataset for later review.",
            )
        )
        self.errorOptOutCheckBox.setText(
            _translate(
                "Main_GUI",
                " Opt out of automatic error reporting.\n"
                " (Leaving this disabled helps us fix bugs in the program!)",
            )
        )
        self.gpusGroupBox.setToolTip(
            _translate(
                "Main_GUI",
                "Toggle the GPUs that you want to use for processing.\n"
                " Work will be distributed among them",
            )
        )
        self.prevBackendSpimagineRadio.setText(_translate("Main_GUI", "spimagine"))
        self.prevBackendNapariRadio.setText(_translate("Main_GUI", "napari"))
        self.prevBackendMatplotlibRadio.setText(_translate("Main_GUI", "matplotlib"))
        self.watchModeAcquisitionRadio.setToolTip(
            _translate(
                "Main_GUI",
                "Use this mode on the acquisition computer\n"
                "to watch a given folder for new LLS folders,\n"
                "and process new images as they arrive.",
            )
        )
        self.watchModeAcquisitionRadio.setText(_translate("Main_GUI", "Acquisition"))
        self.watchModeServerRadio.setToolTip(
            _translate(
                "Main_GUI",
                "This mode assumes that LLS folders are\n"
                '"finished" when they are dropped into the\n'
                "watched folder.  Newly detected folders\n"
                "are added to the regular processing queue\n"
                "in the main window, and processed in turn.",
            )
        )
        self.watchModeServerRadio.setText(_translate("Main_GUI", "Server"))
        self.filenamePatternLineEdit.setText(
            _translate(
                "Main_GUI",
                "{basename}_ch{channel:d}_stack{stack:d}_{wave:d}nm_{reltime:d}msec_{abstime:d}msecAbs{}",
            )
        )
        self.filenamePatternLineEdit.setPlaceholderText(
            _translate("Main_GUI", "filename pattern")
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_config), _translate("Main_GUI", "Config")
        )
        self.log.setHtml(
            _translate(
                "Main_GUI",
                '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">\n'
                '<html><head><meta name="qrichtext" content="1" /><style type="text/css">\n'
                "p, li { white-space: pre-wrap; }\n"
                "</style></head><body style=\" font-family:'.SF NS Text'; font-size:13pt; font-weight:400; font-style:normal;\">\n"
                '<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; background-color:#ffffff;"><br /></p></body></html>',
            )
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_log), _translate("Main_GUI", "Log")
        )
        self.previewButton.setToolTip(
            _translate(
                "Main_GUI", "Preview the highlighted dataset with the current settings"
            )
        )
        self.previewButton.setText(_translate("Main_GUI", "Preview"))
        self.previewCRangeLineEdit.setToolTip(
            _translate(
                "Main_GUI",
                "<html><head/><body><p><span style=\" font-size:12pt;\">a string can be used to dictate a subset of channels to preview. Separate list items with commas, and &quot;start-stop-step&quot; items with dashes. <br>For instance: '0,2-3'<br>NOTE: channels are zero-indexed</span></p></body></html>",
            )
        )
        self.previewCRangeLineEdit.setPlaceholderText(
            _translate("Main_GUI", "channels")
        )
        self.previewTRangeLineEdit.setToolTip(
            _translate(
                "Main_GUI",
                "<html><head/><body><p><span style=\" font-size:12pt;\">a string can be used to dictate a subset of timepoints to preview. Separate list items with commas, and &quot;start-stop-step&quot; items with dashes.<br>For instance: '0,3,5-10,15-30-3,40'<br>NOTE: time is zero-indexed</span></p></body></html>",
            )
        )
        self.previewTRangeLineEdit.setPlaceholderText(_translate("Main_GUI", "time"))
        self.processButton.setText(_translate("Main_GUI", "Process"))
        self.processCRangeLineEdit.setToolTip(
            _translate(
                "Main_GUI",
                "<html><head/><body><p><span style=\" font-size:12pt;\">a string can be used to dictate a subset of channels to preview. Separate list items with commas, and &quot;start-stop-step&quot; items with dashes. <br>For instance: '0,2-3'<br>NOTE: channels are zero-indexed</span></p></body></html>",
            )
        )
        self.processCRangeLineEdit.setPlaceholderText(
            _translate("Main_GUI", "channels")
        )
        self.processTRangeLineEdit.setToolTip(
            _translate(
                "Main_GUI",
                "<html><head/><body><p><span style=\" font-size:12pt;\">a string can be used to dictate a subset of timepoints to process. Separate list items with commas, and &quot;start-stop-step&quot; items with dashes.<br>For instance: '0,3,5-10,15-30-3,40'<br>NOTE: time is zero-indexed</span></p></body></html>",
            )
        )
        self.processTRangeLineEdit.setPlaceholderText(_translate("Main_GUI", "time"))
        self.menuFile.setTitle(_translate("Main_GUI", "File"))
        self.menuView.setTitle(_translate("Main_GUI", "View"))
        self.menuProcess.setTitle(_translate("Main_GUI", "Process"))
        self.menuLLSpy.setTitle(_translate("Main_GUI", "LLSpy"))
        self.menuTools.setTitle(_translate("Main_GUI", "Tools"))
        self.actionQuit.setText(_translate("Main_GUI", "Quit"))
        self.actionQuit.setShortcut(_translate("Main_GUI", "Ctrl+Q"))
        self.actionPreview.setText(_translate("Main_GUI", "Preview"))
        self.actionPreview.setShortcut(_translate("Main_GUI", "Ctrl+P"))
        self.actionRun.setText(_translate("Main_GUI", "Run"))
        self.actionRun.setShortcut(_translate("Main_GUI", "Ctrl+R"))
        self.actionAbort.setText(_translate("Main_GUI", "Abort"))
        self.actionAbort.setShortcut(_translate("Main_GUI", "Ctrl+X"))
        self.actionOpen_LLSdir.setText(_translate("Main_GUI", "Open LLSdir"))
        self.actionOpen_LLSdir.setShortcut(_translate("Main_GUI", "Ctrl+O"))
        self.actionSave_Settings_as_Default.setText(
            _translate("Main_GUI", "Save Settings as Default")
        )
        self.actionSave_Settings_as_Default.setShortcut(
            _translate("Main_GUI", "Ctrl+S")
        )
        self.actionLoad_Default_Settings.setText(
            _translate("Main_GUI", "Load Default Settings")
        )
        self.actionLoad_Default_Settings.setShortcut(_translate("Main_GUI", "Ctrl+D"))
        self.actionReduce_to_Raw.setText(_translate("Main_GUI", "Reduce to Raw"))
        self.actionReduce_to_Raw.setToolTip(
            _translate(
                "Main_GUI",
                "Remove all processed data from selected folder\n"
                "and restore folder to it's original state\n"
                "(immediately after acquisition)",
            )
        )
        self.actionCompress_Folder.setText(_translate("Main_GUI", "Compress Raw"))
        self.actionCompress_Folder.setToolTip(
            _translate("Main_GUI", "Compress raw data in selected folder")
        )
        self.actionDecompress_Folder.setText(_translate("Main_GUI", "Decompress Raw"))
        self.actionConcatenate.setText(_translate("Main_GUI", "Concatenate"))
        self.actionConcatenate.setToolTip(
            _translate("Main_GUI", "Merge selected folders into single LLSdir")
        )
        self.actionRename_Scripted.setText(_translate("Main_GUI", "Rename Scripted"))
        self.actionRename_Scripted.setToolTip(
            _translate(
                "Main_GUI",
                'Rename "Iter_" files in an LLSdir acquired with Script Editor',
            )
        )
        self.actionClose_All_Previews.setText(
            _translate("Main_GUI", "Close All Previews")
        )
        self.actionClose_All_Previews.setShortcut(
            _translate("Main_GUI", "Ctrl+Shift+W")
        )
        self.actionAbout_LLSpy.setText(_translate("Main_GUI", "About LLSpy"))
        self.actionFreeze.setText(_translate("Main_GUI", "Freeze"))
        self.actionFreeze.setToolTip(
            _translate(
                "Main_GUI",
                "Delete all processed data, and compress raw data for storage",
            )
        )
        self.actionHelp.setText(_translate("Main_GUI", "Help"))
        self.actionCamera_Calibration.setText(
            _translate("Main_GUI", "Camera Calibration")
        )
        self.actionRename_Iters.setText(_translate("Main_GUI", "Rename 'Iters_'"))
        self.actionRename_Iters.setToolTip(
            _translate(
                "Main_GUI",
                "Rename files acquired with Script Editor mode, containing 'Iters_'",
            )
        )
        self.actionUndo_Rename_Iters.setText(
            _translate("Main_GUI", "Undo Rename 'Iters_'")
        )
        self.actionReveal.setText(_translate("Main_GUI", "Reveal"))
        self.actionReveal.setToolTip(
            _translate("Main_GUI", "Reveal Item in Explorer/Finder")
        )
        self.actionReveal.setShortcut(_translate("Main_GUI", "Ctrl+Shift+O"))
        self.actionMerge_MIPs_from_folder.setText(_translate("Main_GUI", "Merge MIPs"))
