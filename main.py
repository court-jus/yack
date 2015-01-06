# -*- config: utf-8 -*-

import sys
import pdb
import os

# QT
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets, QtGui

# Image manipulation
from wand.image import Image

# YACK
from ui.main_ui import Ui_MainWindow

WORK_RESOLUTION = 150
BASEDIR = '/tmp'
# MM = INCH / 25.4

def unit_convert(unit=1.0, base_resolution=300, work_resolution=300):

    def px(val):
        if work_resolution != base_resolution:
            return int(val * unit * float(work_resolution) / float(base_resolution))
        return int(val * unit)

    return px

px = unit_convert(work_resolution=WORK_RESOLUTION)
    
CARDW = px(736)
CARDH = px(1030)
MTOP = px(95)
MLEFT = px(161)
TILEW = 3
TILEH = 3
INNW = px(10)
INNH = px(10)

class Yack(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, filename=None):
        super(Yack, self).__init__()
        self.setupUi(self)
        self._scene = QtWidgets.QGraphicsScene()
        self.graphicsView.setScene(self._scene)
        self.actionExit.triggered.connect(self.close)
        self.inputCardWidth.setValue(CARDW)
        self.inputCardHeight.setValue(CARDH)
        self.inputRows.setValue(TILEH)
        self.inputColumns.setValue(TILEW)
        self.inputOuterLeft.setValue(MLEFT)
        self.inputOuterTop.setValue(MTOP)
        self.inputInnerWidth.setValue(INNW)
        self.inputInnerHeight.setValue(INNH)
        self.actionOpen.triggered.connect(self.chooseFile)
        if filename:
            self.openFile(filename)

    def chooseFile(self):
        filename, truc = QtWidgets.QFileDialog.getOpenFileName(self, "Open file...", None,
            "PDF (*.pdf);;All files (*)")
        if filename:
            self.openFile(filename)

    def openFile(self, filename):
        with Image(filename=filename, resolution=WORK_RESOLUTION) as img:
            xpm = img.make_blob(format='xpm')
            pix = QtGui.QPixmap()
            loaded = pix.loadFromData(xpm)
            if loaded:
                print("Loaded")
            self._scene.addPixmap(pix)
#            npages = len(img.sequence)
#            page = img.sequence[0]
#            rownum = 1
#            colnum = 1
#            left = self.inputOuterLeft.value() + colnum * (self.inputCardWidth.value() + self.inputInnerWidth.value())
#            right = left + self.inputCardWidth.value()
#            top = self.inputOuterTop.value() + rownum * (self.inputCardHeight.value() + self.inputInnerHeight.value())
#            bottom = top + self.inputCardHeight.value()
#            print("left",left,"right",right,"top",top,"bottom",bottom)
#            print("imgsize", img.size)
#            with page[left:right, top:bottom] as card:
#                xpm = card.make_blob(format='xpm')
#                pix = QtGui.QPixmap()
#                loaded = pix.loadFromData(xpm)
#                if loaded:
#                    print("Loaded")
#                self._scene.addPixmap(pix)


if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)

    yack = Yack(filename=sys.argv[1] if len(sys.argv) > 0 else None)
    yack.show()

    sys.exit(app.exec_())

