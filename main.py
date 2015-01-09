# -*- config: utf-8 -*-

import sys
import pdb
import os
import time

# QT
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets, QtGui

# Image manipulation
from wand.image import Image

# YACK
from ui.main_ui import Ui_MainWindow

WORK_RESOLUTION = 300
BASEDIR = '/tmp'
# MM = INCH / 25.4

def unit_convert(unit=1.0, base_resolution=300, work_resolution=300):

    def px(val):
        if work_resolution != base_resolution:
            return int(val * unit * float(work_resolution) / float(base_resolution))
        return int(val * unit)

    return px

px = unit_convert(work_resolution=WORK_RESOLUTION)
    
CARDW = px(750)
CARDH = px(1050)
TILEW = 3
TILEH = 3
INNW = px(0)
INNH = px(0)

class Yack(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, filename=None):
        super(Yack, self).__init__()
        self.setupUi(self)
        self._scene = QtWidgets.QGraphicsScene()
        self._image = None
        self._image_cache = {}
        self._center = [0, 0]
        self.currentPage = 0
        self.pageCount = 1
        self.currentCard = 4
        self.graphicsView.setScene(self._scene)
        self.actionExit.triggered.connect(self.close)
        self.inputCardWidth.setValue(CARDW)
        self.inputCardHeight.setValue(CARDH)
        self.inputRows.setValue(TILEH)
        self.inputColumns.setValue(TILEW)
        self.shiftHor.setValue(0)
        self.shiftVert.setValue(0)
        self.inputInnerWidth.setValue(INNW)
        self.inputInnerHeight.setValue(INNH)
        self.actionOpen.triggered.connect(self.chooseFile)
        self.actionSaveCards.triggered.connect(self.exportCards)
        self.rotateButton.clicked.connect(self.fn1)
        self.zoomInButton.clicked.connect(lambda: self.zoom(1.5))
        self.zoomOutButton.clicked.connect(lambda: self.zoom(1.0/1.5))
        self.prevPageButton.clicked.connect(lambda: self.setCurrent(relPage=-1))
        self.nextPageButton.clicked.connect(lambda: self.setCurrent(relPage=1))
        self.prevCardButton.clicked.connect(lambda: self.setCurrent(relCard=-1))
        self.nextCardButton.clicked.connect(lambda: self.setCurrent(relCard=1))
        for widget in [
            self.inputCardWidth, self.inputCardHeight,
            self.inputRows, self.inputColumns,
            self.shiftHor, self.shiftVert,
            self.inputInnerWidth, self.inputInnerHeight,
        ]:
            widget.valueChanged.connect(self.updateCard)
        self.showFullPageCB.toggled.connect(self.toggleFullPage)
        if filename:
            self.openFile(filename)

    def setCurrent(self, page=None, card=None, relPage=None, relCard=None):
        cp = self.currentPage
        cc = self.currentCard
        cardCount = self.inputRows.value() * self.inputColumns.value()
        if page is not None:
            self.currentPage = page
        if card is not None:
            self.currentCard = card
        if relPage is not None:
            self.currentPage = (self.currentPage + relPage) % self.pageCount
        if relCard is not None:
            self.currentCard = (self.currentCard + relCard) % cardCount
        self.currentDisplay.setText(
            "{0}/{1} - {2}/{3}".format(self.currentPage + 1, self.pageCount,
                                       self.currentCard + 1, cardCount)
        )
        if self.currentPage != cp or self.currentCard != cc:
            self.updateCard()

    def toggleFullPage(self):
        if self._image is None:
            return
        if self.showFullPageCB.isChecked():
            self.showPixmap('page{0}'.format(self.currentPage), self.showFullPage,
                            page=self.currentPage)
        else:
            self.showPixmap('page{0}card{1}'.format(self.currentPage, self.currentCard),
                            self.showCard, page=self.currentPage, card=self.currentCard)

    def updateCard(self):
        self.showPixmap('page{0}card{1}'.format(self.currentPage, self.currentCard),
                        self.showCard, page=self.currentPage, card=self.currentCard,
                        force=True)

    def fn1(self):
        self.graphicsView.rotate(90)

    def zoom(self, factor):
        self.graphicsView.scale(factor, factor)

    def chooseFile(self):
        filename, truc = QtWidgets.QFileDialog.getOpenFileName(self, "Open file...", None,
            "PDF (*.pdf);;All files (*)")
        if filename:
            self.openFile(filename)

    def openFile(self, filename):
        self._image_cache = {}
        with Image(filename=filename, resolution=WORK_RESOLUTION) as img:
            self.pageCount = len(img.sequence)
            self._center = [s/2 for s in img.size]
            print(self._center)
            self._image = img.make_blob()
            self.setCurrent(page=0, card=0)
            self.toggleFullPage()

    def clearScene(self):
        for i in self._scene.items():
            self._scene.removeItem(i)

    def getPixmap(self, ident, fn, force=False, *args, **kwargs):
        if ident not in self._image_cache or force:
            self._image_cache[ident] = fn(*args, **kwargs)
        return self._image_cache[ident]

    def showPixmap(self, *args, **kwargs):
        self.clearScene()
        self._scene.addPixmap(self.getPixmap(*args, **kwargs))

    def showFullPage(self, page=0):
        with Image(blob=self._image, resolution=WORK_RESOLUTION) as img:
            page = Image(img.sequence[page], resolution=WORK_RESOLUTION)
            xpm = page.make_blob(format='xpm')
            pix = QtGui.QPixmap()
            pix.loadFromData(xpm)
            return pix

    def getCropCoords(self, card=0):
        rownum = card // self.inputColumns.value()
        colnum = card % self.inputColumns.value()
        # TODO : handle even number of rows or columns
        middle_row = self.inputColumns.value() // 2
        middle_col = self.inputRows.value() // 2
        left = (
            self._center[0] - self.shiftHor.value() +
            (colnum - middle_col) * self.inputCardWidth.value() -
            self.inputCardWidth.value() / 2 +
            self.inputInnerWidth.value() / 2
        )
        top = (
            self._center[1] - self.shiftVert.value() +
            (rownum - middle_row) * self.inputCardHeight.value() -
            self.inputCardHeight.value() / 2 +
            self.inputInnerHeight.value() / 2
        )
        width = self.inputCardWidth.value() - self.inputInnerWidth.value()
        height = self.inputCardHeight.value() - self.inputInnerHeight.value()
        return map(int, [left, top, width, height])

    def showCard(self, page=0, card=0):
        fullpage = self.getPixmap('page{0}'.format(page), self.showFullPage, page=page)
        left, top, width, height = self.getCropCoords(card)
        return fullpage.copy(left, top, width, height)

    def exportCards(self):
        pages = range(self.pageCount)
        ncards = self.inputColumns.value() * self.inputRows.value()
        total_cards = len(pages) * ncards
        current_card = 0
        self.statusbar.showMessage("Exporting...")
        with Image(blob=self._image, resolution=WORK_RESOLUTION) as img:
            for p in pages:
                page = img.sequence[p]
                for c in range(ncards):
                    self.statusbar.showMessage(
                        "Exporting... page {0}, card {1}".format(p + 1, c + 1))
                    left, top, width, height = self.getCropCoords(c)
                    time.sleep(0.250)
                    with page[left:left+width, top:top+height] as card:
                        card.save(filename='page{0}card{1}.png'.format(p, c))
        self.statusbar.showMessage("Export done.", 1500)


if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)

    yack = Yack(filename=sys.argv[1] if len(sys.argv) > 1 else None)
    yack.show()

    sys.exit(app.exec_())

