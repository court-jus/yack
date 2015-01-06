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
    def __init__(self):
        super(Yack, self).__init__()
        self.setupUi(self)
        self._scene = QtWidgets.QGraphicsScene()
        self.graphicsView.setScene(self._scene)
        with Image(filename='/tmp/micro.pdf', resolution=WORK_RESOLUTION) as img:
            npages = len(img.sequence)
            ncards = TILEW * TILEH
            page = img.sequence[0]
            rownum = 1
            colnum = 1
            left = MLEFT + colnum * (CARDW + INNW)
            right = left + CARDW
            top = MTOP + rownum * (CARDH + INNH)
            bottom = top + CARDH
            with page[left-30:right+30, top-30:bottom+30] as card:
                xpm = card.make_blob(format='xpm')
                pix = QtGui.QPixmap()
                loaded = pix.loadFromData(xpm)
                if loaded:
                    print("Loaded")
                self._scene.addPixmap(pix)


if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)

    yack = Yack()
    yack.show()

    sys.exit(app.exec_())

