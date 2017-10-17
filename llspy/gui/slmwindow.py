import os
import numpy as np
import json
from llspy import slm as _slm

from PyQt5 import QtWidgets, QtCore, QtGui
from llspy.gui.slm_pattern_dialog import Ui_Dialog
import logging
logger = logging.getLogger(__name__)


LUTs = {
    "PARULA" : [[53,42,135],[53,43,138],[54,45,141],[54,46,144],[54,48,147],[54,50,150],[54,51,153],[54,53,157],[54,55,160],[54,57,163],[54,58,166],[53,60,170],[53,61,173],[52,62,176],[52,64,179],[51,65,183],[50,67,186],[49,69,189],[48,70,192],[46,72,196],[44,74,199],[42,76,202],[39,78,206],[36,81,209],[32,83,212],[28,85,215],[24,88,217],[19,90,219],[15,92,221],[11,94,222],[8,96,224],[5,97,224],[3,99,225],[2,100,225],[2,102,225],[2,103,225],[2,104,225],[2,105,225],[3,107,225],[3,108,224],[4,109,224],[5,110,224],[6,111,223],[7,112,223],[8,113,222],[9,114,221],[11,115,221],[12,116,220],[13,117,220],[14,118,219],[15,119,219],[15,120,218],[16,121,218],[16,122,217],[17,123,217],[17,124,216],[18,125,216],[19,126,215],[19,127,215],[20,128,214],[20,129,214],[20,130,213],[20,131,213],[20,132,212],[20,133,212],[20,134,212],[20,135,211],[19,136,211],[19,137,211],[18,138,211],[18,139,210],[17,141,210],[16,142,210],[15,143,210],[14,144,210],[13,146,210],[12,147,210],[11,148,210],[10,150,210],[10,151,209],[9,152,209],[8,153,208],[8,154,208],[7,155,207],[7,156,207],[7,157,206],[6,158,206],[6,159,206],[6,160,205],[6,161,204],[6,162,204],[6,163,203],[6,164,202],[6,165,201],[6,166,200],[6,166,199],[6,167,198],[6,167,197],[6,168,196],[7,168,195],[7,169,194],[8,170,193],[8,170,192],[9,171,191],[10,172,190],[11,172,189],[12,173,188],[14,173,186],[15,174,185],[16,175,184],[18,175,182],[19,176,181],[21,177,180],[23,178,179],[25,178,178],[27,179,176],[29,179,175],[31,179,173],[33,180,172],[35,180,170],[37,181,169],[39,181,168],[41,182,166],[44,182,165],[46,183,164],[48,183,163],[51,184,161],[53,184,160],[56,185,158],[58,186,156],[61,186,155],[63,187,153],[66,187,152],[69,187,150],[71,188,149],[74,188,147],[77,188,146],[80,188,144],[83,188,143],[86,189,141],[89,189,140],[92,189,138],[95,189,137],[98,190,135],[101,190,134],[104,190,132],[107,191,131],[110,191,129],[113,191,128],[116,191,127],[119,191,125],[121,191,124],[124,191,123],[127,191,122],[129,191,121],[132,191,120],[135,191,119],[138,191,118],[141,191,117],[143,191,116],[146,191,115],[149,191,114],[151,191,113],[154,191,112],[156,191,111],[158,191,110],[161,190,109],[163,190,108],[165,190,107],[167,190,106],[169,190,105],[172,190,104],[174,190,103],[176,190,102],[178,190,102],[181,189,101],[183,189,100],[185,189,99],[188,188,98],[190,188,97],[192,188,96],[194,188,95],[196,188,94],[198,188,94],[200,188,93],[202,188,92],[204,188,91],[207,187,90],[209,187,89],[211,187,88],[213,186,87],[215,186,87],[217,186,86],[219,186,85],[221,185,84],[223,185,83],[225,185,82],[227,185,81],[229,185,80],[231,185,79],[233,185,78],[235,185,77],[237,185,76],[239,185,75],[241,185,74],[243,185,73],[245,186,71],[246,186,70],[248,187,68],[249,188,66],[251,188,64],[252,189,63],[253,190,61],[254,191,59],[254,192,58],[255,194,56],[255,195,55],[255,196,54],[255,197,52],[254,199,51],[254,200,50],[253,201,49],[253,203,48],[252,204,47],[252,206,46],[252,207,45],[251,209,44],[251,210,43],[250,211,42],[249,212,41],[248,213,40],[248,215,39],[247,216,38],[246,217,37],[246,219,35],[245,220,34],[245,222,33],[245,223,32],[245,225,31],[245,226,30],[245,228,29],[245,230,28],[245,231,27],[245,233,25],[245,235,24],[245,237,23],[245,239,21],[246,241,20],[246,243,19],[247,245,18],[247,247,17],[248,249,15],[249,251,14],[250,253,13],[251,255,11],[251,255,10]],
    "GLOW" : [[0,0,0],[1,0,0],[1,0,0],[2,0,0],[2,0,0],[3,0,0],[4,0,0],[6,0,0],[8,0,0],[11,0,0],[13,0,0],[15,0,0],[18,0,0],[21,1,1],[23,1,1],[24,1,1],[27,1,1],[30,1,1],[31,1,1],[33,1,1],[36,1,1],[37,1,1],[40,2,1],[42,2,3],[45,2,4],[46,2,4],[49,2,4],[51,2,4],[53,2,4],[56,2,4],[58,3,3],[60,3,3],[62,3,3],[65,3,3],[68,4,4],[70,5,6],[72,5,6],[74,5,6],[78,5,6],[80,6,6],[82,6,6],[84,6,6],[86,7,6],[89,7,6],[91,8,6],[93,9,6],[96,9,6],[98,9,6],[100,9,6],[102,10,6],[104,10,6],[106,11,6],[108,12,6],[110,13,6],[113,14,6],[115,14,6],[117,14,6],[119,14,6],[122,15,6],[125,16,6],[127,16,5],[129,17,5],[132,18,7],[135,19,9],[135,19,10],[137,19,10],[140,20,10],[141,21,10],[142,22,10],[145,23,10],[148,24,10],[149,24,10],[152,25,10],[154,27,10],[156,28,10],[157,28,10],[158,28,10],[160,29,10],[162,31,10],[164,32,10],[166,32,10],[168,33,9],[170,35,9],[171,36,9],[173,36,9],[174,37,9],[176,39,9],[178,40,9],[179,40,9],[180,41,9],[182,42,9],[183,43,9],[185,45,9],[186,46,9],[189,47,9],[192,48,8],[193,50,8],[193,51,8],[194,52,8],[195,54,8],[195,55,8],[196,56,8],[198,57,8],[199,59,8],[201,62,8],[203,63,8],[204,65,8],[204,66,8],[205,68,8],[206,70,8],[207,71,8],[209,73,8],[211,74,7],[211,75,7],[211,77,7],[211,79,7],[213,81,7],[215,83,7],[216,85,7],[216,87,7],[216,89,7],[216,92,7],[218,93,7],[219,96,7],[219,98,7],[219,99,7],[220,100,7],[222,103,6],[223,105,6],[223,107,6],[223,109,6],[223,111,6],[224,113,6],[224,116,6],[226,117,7],[227,119,10],[227,121,12],[227,123,12],[227,125,12],[228,126,12],[229,128,12],[231,130,12],[231,132,13],[231,135,15],[231,137,17],[231,139,18],[231,140,18],[231,142,19],[232,144,20],[233,145,22],[234,147,23],[234,148,23],[234,150,24],[234,152,26],[234,154,27],[234,156,27],[235,158,28],[237,160,30],[238,161,32],[238,162,33],[238,164,34],[238,166,35],[238,168,37],[238,171,39],[238,172,40],[238,172,41],[239,174,43],[240,176,45],[242,177,46],[242,179,48],[242,180,50],[242,182,52],[242,183,54],[242,185,55],[242,187,57],[242,188,58],[242,189,61],[243,191,63],[245,192,65],[246,192,67],[246,192,70],[246,196,72],[246,200,73],[245,201,76],[245,201,79],[245,202,80],[245,203,83],[245,204,86],[245,206,88],[245,208,89],[247,210,92],[248,212,95],[249,213,96],[249,213,99],[249,214,102],[249,215,104],[249,217,107],[249,218,108],[249,220,110],[249,221,113],[249,222,116],[249,223,120],[249,224,121],[249,225,123],[249,226,125],[249,226,127],[249,227,129],[249,228,132],[249,229,135],[250,231,137],[252,232,140],[253,233,143],[253,234,146],[253,235,149],[253,236,150],[253,237,153],[253,238,155],[253,239,158],[253,239,160],[253,239,162],[253,239,165],[253,241,168],[253,242,171],[253,243,173],[253,243,175],[253,243,178],[253,244,180],[253,245,183],[253,247,186],[253,247,188],[253,247,191],[253,247,192],[253,247,195],[253,247,198],[253,248,201],[253,249,203],[253,250,206],[253,251,209],[253,251,210],[253,251,213],[253,252,215],[253,252,218],[253,252,221],[253,252,223],[253,252,225],[253,252,228],[253,252,231],[253,252,233],[253,252,236],[253,252,238],[253,252,241],[253,252,244],[253,252,246],[253,253,250],[253,253,252],[255,255,255]],
    "INFERNO" : [[0,0,3],[0,0,4],[0,0,6],[1,0,7],[1,1,9],[1,1,11],[2,1,14],[2,2,16],[3,2,18],[4,3,20],[4,3,22],[5,4,24],[6,4,27],[7,5,29],[8,6,31],[9,6,33],[10,7,35],[11,7,38],[13,8,40],[14,8,42],[15,9,45],[16,9,47],[18,10,50],[19,10,52],[20,11,54],[22,11,57],[23,11,59],[25,11,62],[26,11,64],[28,12,67],[29,12,69],[31,12,71],[32,12,74],[34,11,76],[36,11,78],[38,11,80],[39,11,82],[41,11,84],[43,10,86],[45,10,88],[46,10,90],[48,10,92],[50,9,93],[52,9,95],[53,9,96],[55,9,97],[57,9,98],[59,9,100],[60,9,101],[62,9,102],[64,9,102],[65,9,103],[67,10,104],[69,10,105],[70,10,105],[72,11,106],[74,11,106],[75,12,107],[77,12,107],[79,13,108],[80,13,108],[82,14,108],[83,14,109],[85,15,109],[87,15,109],[88,16,109],[90,17,109],[91,17,110],[93,18,110],[95,18,110],[96,19,110],[98,20,110],[99,20,110],[101,21,110],[102,21,110],[104,22,110],[106,23,110],[107,23,110],[109,24,110],[110,24,110],[112,25,110],[114,25,109],[115,26,109],[117,27,109],[118,27,109],[120,28,109],[122,28,109],[123,29,108],[125,29,108],[126,30,108],[128,31,107],[129,31,107],[131,32,107],[133,32,106],[134,33,106],[136,33,106],[137,34,105],[139,34,105],[141,35,105],[142,36,104],[144,36,104],[145,37,103],[147,37,103],[149,38,102],[150,38,102],[152,39,101],[153,40,100],[155,40,100],[156,41,99],[158,41,99],[160,42,98],[161,43,97],[163,43,97],[164,44,96],[166,44,95],[167,45,95],[169,46,94],[171,46,93],[172,47,92],[174,48,91],[175,49,91],[177,49,90],[178,50,89],[180,51,88],[181,51,87],[183,52,86],[184,53,86],[186,54,85],[187,55,84],[189,55,83],[190,56,82],[191,57,81],[193,58,80],[194,59,79],[196,60,78],[197,61,77],[199,62,76],[200,62,75],[201,63,74],[203,64,73],[204,65,72],[205,66,71],[207,68,70],[208,69,68],[209,70,67],[210,71,66],[212,72,65],[213,73,64],[214,74,63],[215,75,62],[217,77,61],[218,78,59],[219,79,58],[220,80,57],[221,82,56],[222,83,55],[223,84,54],[224,86,52],[226,87,51],[227,88,50],[228,90,49],[229,91,48],[230,92,46],[230,94,45],[231,95,44],[232,97,43],[233,98,42],[234,100,40],[235,101,39],[236,103,38],[237,104,37],[237,106,35],[238,108,34],[239,109,33],[240,111,31],[240,112,30],[241,114,29],[242,116,28],[242,117,26],[243,119,25],[243,121,24],[244,122,22],[245,124,21],[245,126,20],[246,128,18],[246,129,17],[247,131,16],[247,133,14],[248,135,13],[248,136,12],[248,138,11],[249,140,9],[249,142,8],[249,144,8],[250,145,7],[250,147,6],[250,149,6],[250,151,6],[251,153,6],[251,155,6],[251,157,6],[251,158,7],[251,160,7],[251,162,8],[251,164,10],[251,166,11],[251,168,13],[251,170,14],[251,172,16],[251,174,18],[251,176,20],[251,177,22],[251,179,24],[251,181,26],[251,183,28],[251,185,30],[250,187,33],[250,189,35],[250,191,37],[250,193,40],[249,195,42],[249,197,44],[249,199,47],[248,201,49],[248,203,52],[248,205,55],[247,207,58],[247,209,60],[246,211,63],[246,213,66],[245,215,69],[245,217,72],[244,219,75],[244,220,79],[243,222,82],[243,224,86],[243,226,89],[242,228,93],[242,230,96],[241,232,100],[241,233,104],[241,235,108],[241,237,112],[241,238,116],[241,240,121],[241,242,125],[242,243,129],[242,244,133],[243,246,137],[244,247,141],[245,248,145],[246,250,149],[247,251,153],[249,252,157],[250,253,160],[252,254,164]],
    "VIRIDIS" : [[68,1,84],[68,2,85],[68,3,87],[69,5,88],[69,6,90],[69,8,91],[70,9,92],[70,11,94],[70,12,95],[70,14,97],[71,15,98],[71,17,99],[71,18,101],[71,20,102],[71,21,103],[71,22,105],[71,24,106],[72,25,107],[72,26,108],[72,28,110],[72,29,111],[72,30,112],[72,32,113],[72,33,114],[72,34,115],[72,35,116],[71,37,117],[71,38,118],[71,39,119],[71,40,120],[71,42,121],[71,43,122],[71,44,123],[70,45,124],[70,47,124],[70,48,125],[70,49,126],[69,50,127],[69,52,127],[69,53,128],[69,54,129],[68,55,129],[68,57,130],[67,58,131],[67,59,131],[67,60,132],[66,61,132],[66,62,133],[66,64,133],[65,65,134],[65,66,134],[64,67,135],[64,68,135],[63,69,135],[63,71,136],[62,72,136],[62,73,137],[61,74,137],[61,75,137],[61,76,137],[60,77,138],[60,78,138],[59,80,138],[59,81,138],[58,82,139],[58,83,139],[57,84,139],[57,85,139],[56,86,139],[56,87,140],[55,88,140],[55,89,140],[54,90,140],[54,91,140],[53,92,140],[53,93,140],[52,94,141],[52,95,141],[51,96,141],[51,97,141],[50,98,141],[50,99,141],[49,100,141],[49,101,141],[49,102,141],[48,103,141],[48,104,141],[47,105,141],[47,106,141],[46,107,142],[46,108,142],[46,109,142],[45,110,142],[45,111,142],[44,112,142],[44,113,142],[44,114,142],[43,115,142],[43,116,142],[42,117,142],[42,118,142],[42,119,142],[41,120,142],[41,121,142],[40,122,142],[40,122,142],[40,123,142],[39,124,142],[39,125,142],[39,126,142],[38,127,142],[38,128,142],[38,129,142],[37,130,142],[37,131,141],[36,132,141],[36,133,141],[36,134,141],[35,135,141],[35,136,141],[35,137,141],[34,137,141],[34,138,141],[34,139,141],[33,140,141],[33,141,140],[33,142,140],[32,143,140],[32,144,140],[32,145,140],[31,146,140],[31,147,139],[31,148,139],[31,149,139],[31,150,139],[30,151,138],[30,152,138],[30,153,138],[30,153,138],[30,154,137],[30,155,137],[30,156,137],[30,157,136],[30,158,136],[30,159,136],[30,160,135],[31,161,135],[31,162,134],[31,163,134],[32,164,133],[32,165,133],[33,166,133],[33,167,132],[34,167,132],[35,168,131],[35,169,130],[36,170,130],[37,171,129],[38,172,129],[39,173,128],[40,174,127],[41,175,127],[42,176,126],[43,177,125],[44,177,125],[46,178,124],[47,179,123],[48,180,122],[50,181,122],[51,182,121],[53,183,120],[54,184,119],[56,185,118],[57,185,118],[59,186,117],[61,187,116],[62,188,115],[64,189,114],[66,190,113],[68,190,112],[69,191,111],[71,192,110],[73,193,109],[75,194,108],[77,194,107],[79,195,105],[81,196,104],[83,197,103],[85,198,102],[87,198,101],[89,199,100],[91,200,98],[94,201,97],[96,201,96],[98,202,95],[100,203,93],[103,204,92],[105,204,91],[107,205,89],[109,206,88],[112,206,86],[114,207,85],[116,208,84],[119,208,82],[121,209,81],[124,210,79],[126,210,78],[129,211,76],[131,211,75],[134,212,73],[136,213,71],[139,213,70],[141,214,68],[144,214,67],[146,215,65],[149,215,63],[151,216,62],[154,216,60],[157,217,58],[159,217,56],[162,218,55],[165,218,53],[167,219,51],[170,219,50],[173,220,48],[175,220,46],[178,221,44],[181,221,43],[183,221,41],[186,222,39],[189,222,38],[191,223,36],[194,223,34],[197,223,33],[199,224,31],[202,224,30],[205,224,29],[207,225,28],[210,225,27],[212,225,26],[215,226,25],[218,226,24],[220,226,24],[223,227,24],[225,227,24],[228,227,24],[231,228,25],[233,228,25],[236,228,26],[238,229,27],[241,229,28],[243,229,30],[246,230,31],[248,230,33],[250,230,34],[253,231,36]]
}

QLuts = {k: [QtGui.qRgb(*i) for i in v] for k, v in LUTs.items()}

SLMs = {
    'SXGA-3DM': {
        'pixel_size': 13.62,
        'xpix': 1280,
        'ypix': 1024,
    },
    'WXGA-3DM': {
        'pixel_size': 13.62,
        'xpix': 1280,
        'ypix': 768,
    },
    'QXGA-3DM': {
        'pixel_size': 8.2,
        'xpix': 2048,
        'ypix': 1536,
    },
    'Custom': {
        'pixel_size': 10,
        'xpix': 1000,
        'ypix': 1000,
    }
}


class SLMdialog(QtWidgets.QDialog, Ui_Dialog):
    def __init__(self, parent=None):
        super(SLMdialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('LLSpy :: SLM Pattern Generator')
        self.autofill = False

        self.fudgeSpin.valueChanged.connect(self.updateSpacing)
        self.wavelengthSpin.valueChanged.connect(self.updateSpacing)
        self.innerNASpin.valueChanged.connect(self.updateSpacing)
        self.autoSpacingCheckBox.toggled.connect(self.toggleAutoSpace)

        # self.slmBinaryLabel.setStyleSheet("background-color: rgb(111, 174, 255);")
        self.slmBinaryLabel = QtWidgets.QLabel(self)
        self.slmBinaryLabel.setBackgroundRole(QtGui.QPalette.Base)
        self.slmBinaryLabel.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.slmBinaryLabel.setGeometry(QtCore.QRect(0, 0, 450, 150))
        # self.slmBinaryLabel.setScaledContents(True)

        self.sampleIntensityLabel = QtWidgets.QLabel(self)
        self.sampleIntensityLabel.setBackgroundRole(QtGui.QPalette.Base)
        self.sampleIntensityLabel.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        self.maskIntensityLabel = QtWidgets.QLabel(self)
        self.maskIntensityLabel.setBackgroundRole(QtGui.QPalette.Base)
        self.maskIntensityLabel.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        self.upperRightScroll.setBackgroundRole(QtGui.QPalette.Dark)
        self.lowerLeftScroll.setBackgroundRole(QtGui.QPalette.Dark)
        self.lowerRightScroll.setBackgroundRole(QtGui.QPalette.Dark)
        self.upperRightScroll.setWidget(self.maskIntensityLabel)
        self.lowerLeftScroll.setWidget(self.slmBinaryLabel)
        self.lowerRightScroll.setWidget(self.sampleIntensityLabel)

        font = QtGui.QFont()
        #font.setFamily("Helvetica")
        font.setBold(True)
        font.setWeight(60)

        self.lowerLeftTitle = QtWidgets.QLabel(self.lowerLeftScroll)
        self.lowerLeftTitle.setGeometry(QtCore.QRect(5, 5, 111, 16))
        self.lowerLeftTitle.setFont(font)
        self.lowerLeftTitle.setStyleSheet("color:#777;")
        self.lowerLeftTitle.setObjectName("lowerLeftTitle")
        self.lowerLeftTitle.setText("binary SLM mask")

        self.lowerRightTitle = QtWidgets.QLabel(self.lowerRightScroll)
        self.lowerRightTitle.setGeometry(QtCore.QRect(5, 5, 122, 16))
        self.lowerRightTitle.setFont(font)
        self.lowerRightTitle.setStyleSheet("color:#777;")
        self.lowerRightTitle.setObjectName("lowerRightTitle")
        self.lowerRightTitle.setText("Intensity At Sample")

        self.upperRightTitle = QtWidgets.QLabel(self.upperRightScroll)
        self.upperRightTitle.setGeometry(QtCore.QRect(5, 5, 122, 16))
        self.upperRightTitle.setFont(font)
        self.upperRightTitle.setStyleSheet("color:#777;")
        self.upperRightTitle.setObjectName("upperRightTitle")
        self.upperRightTitle.setText("Intensity After Mask")

        self.previewPatternButton.clicked.connect(self.previewPattern)
        self.writeFileButton.clicked.connect(self.writeFile)
        self.PatternPresetsCombo.currentTextChanged.connect(self.updatePreset)
        self.SLMmodelCombo.currentTextChanged.connect(self.setSLM)
        self.SLMmodelCombo.clear()
        self.SLMmodelCombo.addItems(SLMs.keys())
        self.setSLM('SXGA-3DM')
        self.PatternPresetsCombo.setCurrentText('Square Lattice, Fill Chip')

    def toggleAutoFill(self, val):
        dependents = [self.slm_pixelSize_spin, self.slm_xpix_spin,
                      self.magSpin, self.spacingSpin, self.fudgeSpin]
        if val:
            [d.valueChanged.connect(self.updateAutoBeams) for d in dependents]
            self.updateAutoBeams()
        else:
            try:
                [d.valueChanged.disconnect(self.updateAutoBeams) for d in dependents]
            except Exception:
                pass

    def updateAutoBeams(self):
        pixel = self.slm_pixelSize_spin.value()
        slm_xpix = self.slm_xpix_spin.value()
        mag = self.magSpin.value()
        spacing = self.spacingSpin.value()
        fillchip = 0.95
        n_beam = int(np.floor(1 + ((fillchip * (slm_xpix * (pixel/mag)/2)) / spacing)))
        self.nBeamsSpin.setValue(n_beam)

    def toggleAutoSpace(self, val):
        if val:
            self.fudgeSpin.valueChanged.connect(self.updateSpacing)
            self.wavelengthSpin.valueChanged.connect(self.updateSpacing)
            self.innerNASpin.valueChanged.connect(self.updateSpacing)
        else:
            self.fudgeSpin.valueChanged.disconnect(self.updateSpacing)
            self.wavelengthSpin.valueChanged.disconnect(self.updateSpacing)
            self.innerNASpin.valueChanged.disconnect(self.updateSpacing)

    def updateSpacing(self):
        fudge = self.fudgeSpin.value()
        wave = float(self.wavelengthSpin.value())/1000
        NA_inner = self.innerNASpin.value()
        spacing = fudge * wave / NA_inner
        self.spacingSpin.setValue(spacing)

    def previewPattern(self):

        slm_binary, sample_intensity, mask_intensity = _slm.makeSLMPattern(**self.getparams())

        data = slm_binary.astype(np.uint8)
        dh, dw = data.shape
        w = self.slmBinaryLabel.width()/2
        h = self.slmBinaryLabel.height()/2
        data = data[int(dh/2-h):int(dh/2+h), int(dw/2-w):int(dw/2+w)] * 255
        QI = QtGui.QImage(
            data, data.shape[1], data.shape[0], QtGui.QImage.Format_Indexed8)
        p = QtGui.QPixmap.fromImage(QI)
        self.slmBinaryLabel.setPixmap(p)

        data = sample_intensity
        data -= data.min()
        data /= data.max() * 0.65
        data = np.minimum(data, 1)
        data *= 255
        data = data.astype(np.uint8)
        dh, dw = data.shape
        w = self.sampleIntensityLabel.width()/2
        h = self.sampleIntensityLabel.height()/2
        data = data[int(dh/2-h):int(dh/2+h), int(dw/2-w):int(dw/2+w)] * 1
        QI = QtGui.QImage(
            data, data.shape[1], data.shape[0], QtGui.QImage.Format_Indexed8)
        QI.setColorTable(QLuts['VIRIDIS'])
        p = QtGui.QPixmap.fromImage(QI)
        self.sampleIntensityLabel.setPixmap(p)

        data = mask_intensity
        data -= data.min()
        data /= data.max() * 0.65
        data = np.minimum(data, 1)
        data *= 255
        data = data.astype(np.uint8)
        dh, dw = data.shape
        w = 150
        h = 150
        data = data[int(dh/2-h):int(dh/2+h), int(dw/2-w):int(dw/2+w)] * 1
        QI = QtGui.QImage(
            data, data.shape[1], data.shape[0], QtGui.QImage.Format_Indexed8)
        QI.setColorTable(QLuts['INFERNO'])
        p = QtGui.QPixmap.fromImage(QI)
        self.maskIntensityLabel.setPixmap(p)


        #w = self.slmBinaryLabel.width()
        #h = self.slmBinaryLabel.height()
        #self.slmBinaryLabel.setPixmap(p.scaled(w, h, QtCore.Qt.KeepAspectRatio))

    def writeFile(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Where do you want to save the SLM pattern?', '',
            QtWidgets.QFileDialog.ShowDirsOnly)
        if path is None or path is '':
            return
        logger.debug("Writing SLM pattern to " + path)
        _slm.makeSLMPattern(outdir=path, **self.getparams())

    def updatePreset(self, preset):
        logger.debug("SLM Preset changed to: " + preset)
        if preset == 'Manual':
            self.toggleAutoFill(False)
            self.nBeamsSpin.setEnabled(True)
            self.autoSpacingCheckBox.setChecked(True)
            self.autoSpacingCheckBox.setEnabled(True)
            self.spacingSpin.setDisabled(True)
            self.fudgeSpin.setEnabled(True)
        elif preset == 'Single Bessel':
            self.toggleAutoFill(False)
            self.nBeamsSpin.setValue(1)
            self.nBeamsSpin.setDisabled(True)
            self.autoSpacingCheckBox.setChecked(False)
            self.autoSpacingCheckBox.setDisabled(True)
            self.fudgeSpin.setDisabled(True)
            self.spacingSpin.setValue(1)
            self.spacingSpin.setDisabled(True)
            self.cropSpin.setValue(.0291)
        elif preset == '3-Beam Spaced':
            self.toggleAutoFill(False)
            self.nBeamsSpin.setValue(3.0)
            self.nBeamsSpin.setDisabled(True)
            self.autoSpacingCheckBox.setChecked(False)
            self.autoSpacingCheckBox.setDisabled(True)
            self.spacingSpin.setValue(22)
            self.spacingSpin.setEnabled(True)
            self.fudgeSpin.setDisabled(True)
            self.cropSpin.setValue(.05)
        elif preset == 'Square Lattice, Fill Chip':
            self.toggleAutoFill(True)
            self.nBeamsSpin.setDisabled(True)
            self.autoSpacingCheckBox.setChecked(True)
            self.autoSpacingCheckBox.setDisabled(True)
            self.cropSpin.setValue(.22)
            self.updateSpacing()
        else:
            pass

    def setSLM(self, slm):
        if slm not in SLMs:
            return
        if slm.lower() == 'custom':
            self.SLMmodelCombo.setCurrentText(slm)
            self.slm_pixelSize_spin.setEnabled(True)
            self.slm_xpix_spin.setEnabled(True)
            self.slm_ypix_spin.setEnabled(True)
        else:
            self.SLMmodelCombo.setCurrentText(slm)
            self.slm_pixelSize_spin.setValue(SLMs[slm]['pixel_size'])
            self.slm_xpix_spin.setValue(SLMs[slm]['xpix'])
            self.slm_ypix_spin.setValue(SLMs[slm]['ypix'])
            self.slm_pixelSize_spin.setDisabled(True)
            self.slm_xpix_spin.setDisabled(True)
            self.slm_ypix_spin.setDisabled(True)

    def getparams(self):
        opts = {}
        opts['wave'] = float(self.wavelengthSpin.value())/1000
        opts['NA_inner'] = self.innerNASpin.value()
        opts['NA_outer'] = self.outerNASpin.value()

        if opts['NA_outer'] <= opts['NA_inner']:
            raise InvalidSettingsError('Outer NA must be greater than inner NA')

        opts['fudge'] = self.fudgeSpin.value()
        if self.autoSpacingCheckBox.isChecked():
            opts['spacing'] = None
        else:
            opts['spacing'] = self.spacingSpin.value()
        opts['tilt'] = self.tiltSpin.value()
        opts['shift_x'] = self.shiftXSpin.value()
        opts['shift_y'] = self.shiftYSpin.value()
        opts['mag'] = self.magSpin.value()
        opts['crop'] = self.cropSpin.value()
        opts['n_beam'] = self.nBeamsSpin.value()
        opts['pixel'] = self.slm_pixelSize_spin.value()
        opts['slm_xpix'] = self.slm_xpix_spin.value()
        opts['slm_ypix'] = self.slm_ypix_spin.value()
        logger.info("SLM params: {}".format(opts))
        return opts

    @QtCore.pyqtSlot(str, str, str, str)
    def show_error_window(self, errMsg, title=None, info=None, detail=None):
        self.msgBox = QtWidgets.QMessageBox()
        if title is None or title is '':
            title = "LLSpy Error"
        self.msgBox.setWindowTitle(title)

        # self.msgBox.setTextFormat(QtCore.Qt.RichText)
        self.msgBox.setIcon(QtWidgets.QMessageBox.Warning)
        self.msgBox.setText(errMsg)
        if info is not None and info is not '':
            self.msgBox.setInformativeText(info+'\n')
        if detail is not None and detail is not '':
            self.msgBox.setDetailedText(detail)
        self.msgBox.exec_()


class SLMerror(Exception):
    pass


class InvalidSettingsError(SLMerror):
    def __init__(self, msg=None, detail=''):
        if msg is None:
            msg = "An unexpected error occured in the SLM Pattern Generator"
        super(InvalidSettingsError, self).__init__(msg)
        self.msg = msg
        self.detail = detail


class ExceptionHandler(QtCore.QObject):
    """General class to handle all raise exception errors in the GUI"""

    # error message, title, more info, detail (e.g. traceback)
    errorMessage = QtCore.pyqtSignal(str, str, str, str)

    def __init__(self):
        super(ExceptionHandler, self).__init__()

    def handler(self, etype, value, tb):
        err_info = (etype, value, tb)
        self.handleError(*err_info)

    def handleError(self, etype, value, tb):
        import traceback
        tbstring = "".join(traceback.format_exception(etype, value, tb))
        title = "SLM Pattern Generator Error"
        self.errorMessage.emit(value.msg, title, value.detail, tbstring)


def main():
    import sys
    from llspy.util import getAbsoluteResourcePath

    app = QtWidgets.QApplication(sys.argv)
    appicon = QtGui.QIcon(getAbsoluteResourcePath('gui/logo_dark.png'))
    app.setWindowIcon(appicon)

    main = SLMdialog()
    main.show()

    # instantiate the execption handler
    exceptionHandler = ExceptionHandler()
    sys.excepthook = exceptionHandler.handler
    exceptionHandler.errorMessage.connect(main.show_error_window)

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
