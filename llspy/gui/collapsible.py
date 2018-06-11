from PyQt5 import QtWidgets, QtCore, QtGui
import sys

class FrameLayout(QtWidgets.QFrame):

    def __init__(self, parent=None, title=None):
        super(FrameLayout, self).__init__(parent=parent)

        self._is_collasped = True
        self._title_frame = None
        self._content, self._content_layout = (None, None)
        self._main_v_layout = QtWidgets.QVBoxLayout(self)

        self._main_v_layout.addWidget(self.initTitleFrame(title, self._is_collasped))
        self._main_v_layout.addWidget(self.initContent(self._is_collasped))
        self.setFrameStyle(1)

    def initTitleFrame(self, title, collapsed):
        self._title_frame = self.TitleFrame(title=title, collapsed=collapsed)
        self._title_frame._arrow.clicked.connect(self.toggleCollapsed)
        return self._title_frame

    def initContent(self, collapsed):
        self._content = QtWidgets.QWidget()
        self._content_layout = QtWidgets.QVBoxLayout()

        self._content.setLayout(self._content_layout)
        self._content.setVisible(not collapsed)

        return self._content

    def addWidget(self, widget):
        self._content_layout.addWidget(widget)

    def toggleCollapsed(self):
        self._content.setVisible(self._is_collasped)
        self._is_collasped = not self._is_collasped
        self._title_frame._arrow.setArrow(int(self._is_collasped))

    class TitleFrame(QtWidgets.QFrame):

        def __init__(self, parent=None, title="", collapsed=False):
            QtWidgets.QFrame.__init__(self, parent=parent)

            self.setMinimumHeight(24)
            self.move(QtCore.QPoint(24, 0))

            self._hlayout = QtWidgets.QHBoxLayout(self)
            self._hlayout.setContentsMargins(0, 0, 0, 0)
            self._hlayout.setSpacing(4)

            self._arrow = FrameLayout.Arrow(collapsed=collapsed)
            self._arrow.setStyleSheet("border:0px")
            self._title = QtWidgets.QLabel(title)
            self.checkActive = QtWidgets.QCheckBox()
            self.checkActive.setMaximumSize(24, 24)

            self._hlayout.addWidget(self._arrow)
            self._hlayout.addWidget(self.checkActive)
            self._hlayout.addWidget(self._title)

    class Arrow(QtWidgets.QFrame):
        clicked = QtCore.pyqtSignal()

        def __init__(self, parent=None, collapsed=False):
            QtWidgets.QFrame.__init__(self, parent=parent)

            self.setMaximumSize(24, 24)

            # horizontal == 0
            self._arrow_horizontal = (QtCore.QPointF(7.0, 5), QtCore.QPointF(17.0, 5), QtCore.QPointF(12.0, 10))
            # vertical == 1
            self._arrow_vertical = (QtCore.QPointF(8.0, 4), QtCore.QPointF(13.0, 9), QtCore.QPointF(8.0, 14))
            # arrow
            self._arrow = None
            self.setArrow(int(collapsed))

        def setArrow(self, arrow_dir):
            if arrow_dir:
                self._arrow = self._arrow_vertical
            else:
                self._arrow = self._arrow_horizontal

        def paintEvent(self, event):
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setBrush(QtGui.QColor(192, 192, 192))
            painter.setPen(QtGui.QColor(64, 64, 64))
            painter.drawPolygon(*self._arrow)
            painter.end()

        def mousePressEvent(self, event):
            self.clicked.emit()
            return super(FrameLayout.Arrow, self).mousePressEvent(event)


if __name__ == '__main__':

    from llspy.newgui import imgp_view
    from llspy import imgprocessors as imgp

    app = QtWidgets.QApplication([])
    win = QtWidgets.QMainWindow()
    w = QtWidgets.QWidget()
    w.setMinimumWidth(350)
    win.setCentralWidget(w)
    l = QtWidgets.QVBoxLayout()
    l.setSpacing(2)
    l.setAlignment(QtCore.Qt.AlignTop)
    w.setLayout(l)

    t = FrameLayout(title="Buttons")
    t.addWidget(imgp_view.ImageProcessorView(imgp.CUDADeconProcessor))
    l.addWidget(t)

    t = FrameLayout(title="Buttons")
    t.addWidget(imgp_view.ImageProcessorView(imgp.BleachCorrectionProcessor))
    l.addWidget(t)


    win.show()
    win.raise_()
    sys.exit(app.exec_())
