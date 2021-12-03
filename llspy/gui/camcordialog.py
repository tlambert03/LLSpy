# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'llspy/gui/camcordialog.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from qtpy import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(1000, 760)
        Dialog.setMinimumSize(QtCore.QSize(1000, 760))
        Dialog.setMaximumSize(QtCore.QSize(10000, 10000))
        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.textEdit = QtWidgets.QTextEdit(Dialog)
        self.textEdit.setMinimumSize(QtCore.QSize(0, 280))
        self.textEdit.setMaximumSize(QtCore.QSize(16777215, 1000))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.textEdit.setFont(font)
        self.textEdit.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.textEdit.setFrameShadow(QtWidgets.QFrame.Plain)
        self.textEdit.setObjectName("textEdit")
        self.horizontalLayout.addWidget(self.textEdit)
        self.picture = QtWidgets.QLabel(Dialog)
        self.picture.setMinimumSize(QtCore.QSize(500, 280))
        self.picture.setText("")
        self.picture.setPixmap(QtGui.QPixmap("before_after.png"))
        self.picture.setObjectName("picture")
        self.horizontalLayout.addWidget(self.picture)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.textEdit_2 = QtWidgets.QTextEdit(Dialog)
        self.textEdit_2.setMinimumSize(QtCore.QSize(0, 140))
        self.textEdit_2.setMaximumSize(QtCore.QSize(16777215, 10000))
        self.textEdit_2.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.textEdit_2.setFrameShadow(QtWidgets.QFrame.Plain)
        self.textEdit_2.setObjectName("textEdit_2")
        self.verticalLayout.addWidget(self.textEdit_2)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setContentsMargins(-1, 0, -1, -1)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1, QtCore.Qt.AlignRight)
        self.camCalibFolderLineEdit = QtWidgets.QLineEdit(Dialog)
        self.camCalibFolderLineEdit.setReadOnly(True)
        self.camCalibFolderLineEdit.setObjectName("camCalibFolderLineEdit")
        self.gridLayout.addWidget(self.camCalibFolderLineEdit, 0, 1, 1, 1)
        self.selectFolderPushButton = QtWidgets.QPushButton(Dialog)
        self.selectFolderPushButton.setObjectName("selectFolderPushButton")
        self.gridLayout.addWidget(self.selectFolderPushButton, 0, 2, 1, 1)
        self.DarkAVGPushButton = QtWidgets.QPushButton(Dialog)
        self.DarkAVGPushButton.setObjectName("DarkAVGPushButton")
        self.gridLayout.addWidget(self.DarkAVGPushButton, 1, 2, 1, 1)
        self.darkAVGLineEdit = QtWidgets.QLineEdit(Dialog)
        self.darkAVGLineEdit.setReadOnly(True)
        self.darkAVGLineEdit.setObjectName("darkAVGLineEdit")
        self.gridLayout.addWidget(self.darkAVGLineEdit, 1, 1, 1, 1)
        self.label_3 = QtWidgets.QLabel(Dialog)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1, QtCore.Qt.AlignRight)
        self.label_4 = QtWidgets.QLabel(Dialog)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 2, 0, 1, 1)
        self.darkSTDLineEdit = QtWidgets.QLineEdit(Dialog)
        self.darkSTDLineEdit.setReadOnly(True)
        self.darkSTDLineEdit.setObjectName("darkSTDLineEdit")
        self.gridLayout.addWidget(self.darkSTDLineEdit, 2, 1, 1, 1)
        self.DarkSTDPushButton = QtWidgets.QPushButton(Dialog)
        self.DarkSTDPushButton.setObjectName("DarkSTDPushButton")
        self.gridLayout.addWidget(self.DarkSTDPushButton, 2, 2, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.textEdit_4 = QtWidgets.QTextEdit(Dialog)
        self.textEdit_4.setMinimumSize(QtCore.QSize(0, 0))
        self.textEdit_4.setMaximumSize(QtCore.QSize(16777215, 10000))
        self.textEdit_4.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.textEdit_4.setFrameShadow(QtWidgets.QFrame.Plain)
        self.textEdit_4.setObjectName("textEdit_4")
        self.verticalLayout.addWidget(self.textEdit_4)
        self.runButton = QtWidgets.QPushButton(Dialog)
        self.runButton.setObjectName("runButton")
        self.verticalLayout.addWidget(self.runButton)
        self.progressBar = QtWidgets.QProgressBar(Dialog)
        self.progressBar.setProperty("value", 24)
        self.progressBar.setObjectName("progressBar")
        self.verticalLayout.addWidget(self.progressBar)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setContentsMargins(-1, 10, -1, -1)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.abortButton = QtWidgets.QPushButton(Dialog)
        self.abortButton.setObjectName("abortButton")
        self.horizontalLayout_2.addWidget(self.abortButton)
        self.statusLabel = QtWidgets.QLabel(Dialog)
        self.statusLabel.setObjectName("statusLabel")
        self.horizontalLayout_2.addWidget(self.statusLabel)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Close)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName("buttonBox")
        self.horizontalLayout_2.addWidget(self.buttonBox)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.label.setBuddy(self.camCalibFolderLineEdit)
        self.label_3.setBuddy(self.camCalibFolderLineEdit)
        self.label_4.setBuddy(self.camCalibFolderLineEdit)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.textEdit.setHtml(
            _translate(
                "Dialog",
                '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">\n'
                '<html><head><meta name="qrichtext" content="1" /><style type="text/css">\n'
                "p, li { white-space: pre-wrap; }\n"
                '</style></head><body style=" font-family:\'.SF NS Text\'; font-size:12pt; font-weight:400; font-style:normal;" bgcolor="#ececec">\n'
                '<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:14pt; font-weight:600;">Flash4.0 Artifact Explanation</span></p>\n'
                '<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:14pt;"><br /></p>\n'
                '<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:14pt;">For a full explanation of the need for this correction, please read the docs:</span></p>\n'
                '<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:13pt;">http://llspy.readthedocs.io/en/latest/camera.html</span></p>\n'
                '<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:14pt;"><br /></p>\n'
                '<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:13pt; font-style:italic;">Use this script to generate the calibration file that holds the parameters of the regression describing the predicted residual intensity in a given pixel as a function of the intensity of the previous image.  This can be used to yield a corrected image, as shown in the image on the right.</span></p></body></html>',
            )
        )
        self.textEdit_2.setHtml(
            _translate(
                "Dialog",
                '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">\n'
                '<html><head><meta name="qrichtext" content="1" /><style type="text/css">\n'
                "p, li { white-space: pre-wrap; }\n"
                '</style></head><body style=" font-family:\'.SF NS Text\'; font-size:13pt; font-weight:400; font-style:normal;" bgcolor="#ececec">\n'
                '<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:14pt; font-weight:600;">Image Acquisition Procedure</span></p>\n'
                '<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><br /></p>\n'
                '<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">This script assumes you have aquired a series of 2-channel Zstacks (not actually a 3D stack: set Z galvo range and Z and Sample Piezo range to zero). The first channel should be &quot;bright&quot; (many photons hitting the chip) and even like a flatfield image (such as 488 laser sheet exciting FITC) and the second channel is a &quot;dark&quot; image (I use another wavelength channel with the laser off.  Collect two ~100-plane Z stacks for many different intensities (laser power) in the &quot;bright channel&quot;: start at very low power (0.1% laser) and gradually acquire stacks at higher power.  Due to the exponential relationship of the residual electron effect, it\'s particularly important to get a lot of low-powered stacks: 1%, 2%, 3% etc... then after 10% you can begin to take bigger steps. (Of course, the exact laser powers will depend on the power and efficiency of your system.).  More here: http://llspy.readthedocs.io/en/latest/camera.html</p></body></html>',
            )
        )
        self.label.setText(_translate("Dialog", "Image Folder:"))
        self.selectFolderPushButton.setText(_translate("Dialog", "Select Folder"))
        self.DarkAVGPushButton.setText(_translate("Dialog", "Chose Dark Avg"))
        self.label_3.setText(_translate("Dialog", "Dark AVG (optional):"))
        self.label_4.setText(_translate("Dialog", "Dark STD (optional):"))
        self.DarkSTDPushButton.setText(_translate("Dialog", "Chose Dark STD"))
        self.textEdit_4.setHtml(
            _translate(
                "Dialog",
                '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">\n'
                '<html><head><meta name="qrichtext" content="1" /><style type="text/css">\n'
                "p, li { white-space: pre-wrap; }\n"
                '</style></head><body style=" font-family:\'.SF NS Text\'; font-size:13pt; font-weight:400; font-style:normal;" bgcolor="#ececec">\n'
                '<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-style:italic;">Dark AVG is an average projection of many (&gt;20,000) images with no light delivered to the camera.  Dark STD is a standard deviation projection of the same images.  By default, the program will generate an offset map (Avg projection) and noise map (StdDev Projection) from all images in the folder with the word &quot;dark&quot; . Optionally, these two images can be calculated elsewhere and provided to the program in the lines above. </span></p>\n'
                '<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-style:italic;">See docs for more info: http://llspy.readthedocs.io/en/latest/camera.html</span></p></body></html>',
            )
        )
        self.runButton.setText(_translate("Dialog", "Run"))
        self.abortButton.setText(_translate("Dialog", "Abort"))
        self.statusLabel.setText(_translate("Dialog", "TextLabel"))
