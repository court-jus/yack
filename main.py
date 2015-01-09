# -*- config: utf-8 -*-

import sys
import pdb
import traceback
import os
import time
import json

# QT
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets, QtGui

# Image manipulation
from wand.image import Image

# YACK
from ui.main_ui import Ui_MainWindow

WORK_RESOLUTION = 50

class Yack(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, filename=None):
        super(Yack, self).__init__()
        self.setupUi(self)
        self.inputScene = QtWidgets.QGraphicsScene()
        self.cardScene = QtWidgets.QGraphicsScene()
        self.outputScene = QtWidgets.QGraphicsScene()
        self._image = None
        self._image_cache = {}
        self._center = [0, 0]
        self.currentPage = 0
        self.pageCount = 1
        self.currentCard = 4
        self.inputGView.setScene(self.inputScene)
        self.cardGView.setScene(self.cardScene)
        self.cardGView.scale(3, 3)
        self.outputGView.setScene(self.outputScene)
        # Menu
        self.actionExit.triggered.connect(self.close)
        self.actionOpen.triggered.connect(self.chooseFile)
        self.actionSaveCards.triggered.connect(self.exportCards)
        # Top buttons
        self.rotateButton.clicked.connect(self.rotate)
        self.zoomInButton.clicked.connect(lambda: self.zoom(1.5))
        self.zoomOutButton.clicked.connect(lambda: self.zoom(1.0/1.5))
        self.prevPageButton.clicked.connect(lambda: self.setCurrent(relPage=-1))
        self.nextPageButton.clicked.connect(lambda: self.setCurrent(relPage=1))
        self.prevCardButton.clicked.connect(lambda: self.setCurrent(relCard=-1))
        self.nextCardButton.clicked.connect(lambda: self.setCurrent(relCard=1))
        # Input buttons
        self.openInputLayoutButton.clicked.connect(lambda: self.openLayout())
        self.saveInputLayoutButton.clicked.connect(lambda: self.saveLayout())
        # Output buttons
        self.copyLayoutButton.clicked.connect(
            lambda: self.dictToLayout(self.layoutToDict(), 'output'))
        self.openOutputLayoutButton.clicked.connect(lambda: self.openLayout('output'))
        self.saveOutputLayoutButton.clicked.connect(lambda: self.saveLayout('output'))
        for widget in [
            self.inputCardWidth, self.inputCardHeight,
            self.inputRows, self.inputColumns,
            self.inputShiftHor, self.inputShiftVert,
            self.inputInnerWidth, self.inputInnerHeight,
        ]:
            if WORK_RESOLUTION != 300:
                widget.setValue(int(widget.value() * WORK_RESOLUTION / 300))
            widget.valueChanged.connect(self.updateCard)
        if filename:
            self.openFile(filename)

    # Choose and update current
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
        if self.currentPage != cp:
            self.showPixmap(
                self.inputScene, 'page{0}'.format(self.currentPage),
                self.showFullPage, page=self.currentPage)
        if self.currentPage != cp or self.currentCard != cc:
            self.showPixmap(
                self.cardScene,
                'page{0}card{1}'.format(self.currentPage, self.currentCard),
                self.showCard, page=self.currentPage, card=self.currentCard)

    def updateAll(self):
        self.showPixmap(
            self.inputScene, 'page{0}'.format(self.currentPage),
            self.showFullPage, page=self.currentPage, force=True)
        self.showPixmap(
            self.cardScene,
            'page{0}card{1}'.format(self.currentPage, self.currentCard),
            self.showCard, page=self.currentPage, card=self.currentCard,
            force=True)

    def updateCard(self):
        self.showPixmap(self.cardScene, 'page{0}card{1}'.format(self.currentPage, self.currentCard),
                        self.showCard, page=self.currentPage, card=self.currentCard,
                        force=True)

    def clearScene(self, scene):
        for i in scene.items():
            scene.removeItem(i)

    def getPixmap(self, ident, fn, force=False, *args, **kwargs):
        if ident not in self._image_cache or force:
            self._image_cache[ident] = fn(*args, **kwargs)
        return self._image_cache[ident]

    def showPixmap(self, scene, *args, **kwargs):
        self.clearScene(scene)
        scene.addPixmap(self.getPixmap(*args, **kwargs))

    def showFullPage(self, page=0):
        with Image(blob=self._image, resolution=WORK_RESOLUTION) as img:
            page = Image(img.sequence[page], resolution=WORK_RESOLUTION)
            xpm = page.make_blob(format='xpm')
            pix = QtGui.QPixmap()
            pix.loadFromData(xpm)
            return pix

    def showCard(self, page=0, card=0):
        fullpage = self.getPixmap('page{0}'.format(page), self.showFullPage, page=page)
        left, top, width, height = self.getCropCoords(card)
        return fullpage.copy(left, top, width, height)

    # Manipulate the view
    def rotate(self):
        self.inputGView.rotate(90)
        self.cardGView.rotate(90)
        self.outputGView.rotate(90)

    def zoom(self, factor):
        self.inputGView.scale(factor, factor)
        self.cardGView.scale(factor, factor)
        self.outputGView.scale(factor, factor)

    # Manipulate files
    def chooseFile(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open file...", None,
            "PDF (*.pdf);;All files (*)")
        if filename:
            self.openFile(filename)

    def openFile(self, filename):
        self._image_cache = {}
        with Image(filename=filename, resolution=WORK_RESOLUTION) as img:
            self.pageCount = len(img.sequence)
            self._center = [s/2 for s in img.size]
            self._image = img.make_blob()
            self.setCurrent(page=0, card=0)
            self.updateAll()

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

    def openLayout(self, layout='input'):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open layout file...", None,
            "JSON (*.json);;All files (*)")
        if filename:
            try:
                with open(filename, 'r') as fh:
                    data = json.load(fh)
                    self.dictToLayout(data, layout)
            except ValueError:
                traceback.print_exc()
                self.statusbar.showMessage("Error loading or decoding layout file.")

    def saveLayout(self, layout='input'):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save layout file...", None,
            "JSON (*.json);;All files (*)")
        if filename:
            try:
                with open(filename, 'w') as fh:
                    json.dump(self.layoutToDict(layout), fh)
            except ValueError:
                traceback.print_exc()
                self.statusbar.showMessage("Error loading or decoding layout file.")

    # Helpers
    def layoutToDict(self, layout='input'):
        result = {}
        for attrname in dir(self):
            if attrname.startswith(layout):
                widget = getattr(self, attrname)
                key = attrname[len(layout):]
                if hasattr(widget, 'value'):
                    result[key] = widget.value()
                elif hasattr(widget, 'text'):
                    result[key] = widget.text()
        return result

    def dictToLayout(self, layoutDict, layout='input'):
        for k, v in layoutDict.items():
            if hasattr(self, layout + k):
                widget = getattr(self, layout + k)
                if hasattr(widget, 'setValue'):
                    widget.setValue(int(v))
                elif hasattr(widget, 'setText'):
                    widget.setText(v)

    def getCropCoords(self, card=0):
        rownum = card // self.inputColumns.value()
        colnum = card % self.inputColumns.value()
        # TODO : handle even number of rows or columns
        middle_row = self.inputColumns.value() // 2
        middle_col = self.inputRows.value() // 2
        left = (
            self._center[0] - self.inputShiftHor.value() +
            (colnum - middle_col) * self.inputCardWidth.value() -
            self.inputCardWidth.value() / 2 +
            self.inputInnerWidth.value() / 2
        )
        top = (
            self._center[1] - self.inputShiftVert.value() +
            (rownum - middle_row) * self.inputCardHeight.value() -
            self.inputCardHeight.value() / 2 +
            self.inputInnerHeight.value() / 2
        )
        width = self.inputCardWidth.value() - self.inputInnerWidth.value()
        height = self.inputCardHeight.value() - self.inputInnerHeight.value()
        return map(int, [left, top, width, height])


if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)

    yack = Yack(filename=sys.argv[1] if len(sys.argv) > 1 else None)
    yack.show()

    sys.exit(app.exec_())

