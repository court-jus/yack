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
from wand.drawing import Drawing
from wand.color import Color

# YACK
from ui.main_ui import Ui_MainWindow

class Yack(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, filename=None):
        super(Yack, self).__init__()
        self.setupUi(self)
        self.filename = filename
        self.inputScene = QtWidgets.QGraphicsScene()
        self.cardScene = QtWidgets.QGraphicsScene()
        self.outputScene = QtWidgets.QGraphicsScene()
        self._image = None
        self._image_cache = {}
        self._center = [0, 0]
        self.currentPage = 0
        self.currentPageIdx = 0
        self.activePages = [0]
        self.currentCard = 4
        self.inputGView.setScene(self.inputScene)
        self.cardGView.setScene(self.cardScene)
        self.cardGView.scale(3, 3)
        self.outputGView.setScene(self.outputScene)
        # Menu
        self.actionExit.triggered.connect(self.close)
        self.actionOpen.triggered.connect(self.chooseFile)
        self.actionSaveCards.triggered.connect(self.exportCards)
        self.actionSaveOutput.triggered.connect(self.exportOutput)
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
            self.inputShiftHor, self.inputShiftVert,
            self.inputInnerWidth, self.inputInnerHeight,
            self.outputCardWidth, self.outputCardHeight,
            self.outputShiftHor, self.outputShiftVert,
            self.outputInnerWidth, self.outputInnerHeight,
        ]:
            if self.workResolution.value() != 300:
                widget.setValue(int(widget.value() * self.workResolution.value() / 300))
        for widget in [
            self.inputCardWidth, self.inputCardHeight,
            self.inputRows, self.inputColumns,
            self.inputShiftHor, self.inputShiftVert,
            self.inputInnerWidth, self.inputInnerHeight,
        ]:
            widget.valueChanged.connect(self.updateCard)
        for widget in [
            self.outputCardWidth, self.outputCardHeight,
            self.outputRows, self.outputColumns,
            self.outputShiftHor, self.outputShiftVert,
            self.outputInnerWidth, self.outputInnerHeight,
            self.outputPageWidth, self.outputPageHeight,
        ]:
            widget.valueChanged.connect(lambda v: self.showOutputPage())
        self.inputIgnoredPages.textEdited.connect(lambda v: self.computeIgnoredPages())
        self.applyResolutionBtn.clicked.connect(lambda v: self.changeResolution())
        if self.filename:
            self.openFile(self.filename)

    # Choose and update current
    def computeIgnoredPages(self):
        ignored = []
        self.activePages = self.allPages[:]
        try:
            for i in self.inputIgnoredPages.text().split(','):
                if '-' in i:
                    start, end = map(int, i.split('-'))
                    if end < start:
                        start, end = end, start
                else:
                    start, end = map(int, [i, i])
                while start <= end:
                    ignored.append(start - 1)
                    start += 1
            for i in ignored:
                self.activePages.remove(i)
            self.setCurrent(page=0)
        except:
            traceback.print_exc()
            self.statusbar.showMessage("Error: can't understand your ignored pages input.", 1500)

    def setCurrent(self, page=None, card=None, relPage=None, relCard=None):
        cp = self.currentPage
        cc = self.currentCard
        cardCount = self.inputRows.value() * self.inputColumns.value()
        if page is not None:
            if page in self.activePages:
                self.currentPage = page
        if card is not None:
            self.currentCard = card
        if relPage is not None:
            self.currentPageIdx = (self.currentPageIdx + relPage) % len(self.activePages)
            self.currentPage = self.activePages[self.currentPageIdx]
        if relCard is not None:
            self.currentCard = (self.currentCard + relCard) % cardCount
        self.currentDisplay.setText(
            "{0}/{1} ({2}) - {2}/{3}".format(self.currentPageIdx + 1, len(self.activePages),
                                       self.currentPage + 1,
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
                self.showCard, page=self.currentPage, card=self.currentCard,
                force=True)

    def changeResolution(self):
        if self.filename:
            self.openFile(self.filename)

    def updateAll(self):
        self.showPixmap(
            self.inputScene, 'page{0}'.format(self.currentPage),
            self.showFullPage, page=self.currentPage, force=True)
        self.showPixmap(
            self.cardScene,
            'page{0}card{1}'.format(self.currentPage, self.currentCard),
            self.showCard, page=self.currentPage, card=self.currentCard,
            force=True)
        self.showOutputPage()

    def updateCard(self):
        self.showPixmap(self.cardScene, 'page{0}card{1}'.format(self.currentPage, self.currentCard),
                        self.showCard, page=self.currentPage, card=self.currentCard,
                        force=True)
        self.showOutputPage()

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
        with Image(blob=self._image, resolution=self.workResolution.value()) as img:
            if page >= len(img.sequence):
                return QtGui.QPixmap()
            page = Image(img.sequence[page], resolution=self.workResolution.value())
            xpm = page.make_blob(format='xpm')
            pix = QtGui.QPixmap()
            pix.loadFromData(xpm)
            return pix

    def showOutputPage(self, page=0):
        self.clearScene(self.outputScene)
        oR = self.outputRows.value()
        oC = self.outputColumns.value()
        oCW = self.outputCardWidth.value()
        oCH = self.outputCardHeight.value()
        oIW = self.outputInnerWidth.value()
        oIH = self.outputInnerHeight.value()
        oSH = self.outputShiftHor.value()
        oSV = self.outputShiftVert.value()
        ncards = oC * oR
        nincards = self.inputColumns.value() * self.inputRows.value()
        firstcard = page * ncards
        pageWidth = self.outputPageWidth.value() * self.workResolution.value() / 300
        pageHeight = self.outputPageHeight.value() * self.workResolution.value() / 300
        allCardsWidth = oC * oCW + oC * oIW + oIW
        allCardsHeight = oR * oCH + oR * oIH + oIH
        mL = (pageWidth - allCardsWidth) / 2
        mT = (pageHeight - allCardsHeight) / 2
        self.outputScene.addRect(0, 0, pageWidth, pageHeight)
        brush = QtGui.QBrush(QtGui.QColor(self.outputInnerColor.text()))
        pen = QtGui.QPen(QtGui.QColor('#ffffff'))
        self.outputScene.addRect(mL, mT, allCardsWidth, allCardsHeight, pen=pen, brush=brush)
        for cardnumber in range(ncards):
            cardidx = cardnumber + firstcard
            inpage = cardidx // nincards
            incard = cardidx % nincards
            pix = self.showCard(page=inpage, card=incard)
            if pix:
                pix = pix.scaled(oCW, oCH)
                item = self.outputScene.addPixmap(pix)
                row = cardnumber // oC
                col = cardnumber % oC
                item.setPos(
                    col * (oCW + oIW) + oSH + mL + oIW,
                    row * (oCH + oIH) + oSV + mT + oIH,
                )

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
        with Image(filename=filename, resolution=self.workResolution.value()) as img:
            self.allPages = list(range(len(img.sequence)))
            self.activePages = self.allPages[:]
            self._center = [s/2 for s in img.size]
            self._image = img.make_blob()
            self.setCurrent(page=0, card=0)
            self.updateAll()

    def exportCards(self):
        pages = self.activePages
        ncards = self.inputColumns.value() * self.inputRows.value()
        total_cards = len(pages) * ncards
        current_card = 0
        self.statusbar.showMessage("Exporting...")
        with Image(blob=self._image, resolution=self.workResolution.value()) as img:
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

    def exportOutput(self):
        self.statusbar.showMessage("Exporting...")
        oR = self.outputRows.value()
        oC = self.outputColumns.value()
        oCW = self.outputCardWidth.value()
        oCH = self.outputCardHeight.value()
        oIW = self.outputInnerWidth.value()
        oIH = self.outputInnerHeight.value()
        oSH = self.outputShiftHor.value()
        oSV = self.outputShiftVert.value()
        ncards = oC * oR
        nincards = self.inputColumns.value() * self.inputRows.value()
        pageWidth = int(self.outputPageWidth.value() * self.workResolution.value() / 300)
        pageHeight = int(self.outputPageHeight.value() * self.workResolution.value() / 300)
        allCardsWidth = oC * oCW + oC * oIW + oIW
        allCardsHeight = oR * oCH + oR * oIH + oIH
        mL = int((pageWidth - allCardsWidth) / 2)
        mT = int((pageHeight - allCardsHeight) / 2)
        totalInputCards = nincards * len(self.activePages)
        totalOutputPages = totalInputCards // ncards + (1 if totalInputCards % ncards > 0 else 0)
        draw = Drawing()
        draw.fill_color = Color(self.outputInnerColor.text())
        draw.rectangle(left=mL, top=mT, width=allCardsWidth, height=allCardsHeight)
        with Image(width=pageWidth, height=pageHeight) as outputImage:
            for oPageNum in range(totalOutputPages):
                firstcard = oPageNum * ncards
                page = Image(width=pageWidth, height=pageHeight)
                draw(page)
                img = Image(blob=self._image, resolution=self.workResolution.value())
                for cardnumber in range(ncards):
                    self.statusbar.showMessage("Exporting... {0} {1}".format(oPageNum, cardnumber))
                    cardidx = cardnumber + firstcard
                    try:
                        inpage = self.activePages[cardidx // nincards]
                    except IndexError:
                        # We have more output cards than input cards
                        # we then take the first page again
                        inpage = self.activePages[0]
                    incard = cardidx % nincards
                    inputpage = Image(img.sequence[inpage], resolution=self.workResolution.value())
                    l, t, w, h = self.getCropCoords(card=incard)
                    inputcard = inputpage[l:l+w, t:t+h]
                    # scale to output
                    inputcard.resize(width=oCW, height=oCH)
                    row = cardnumber // oC
                    col = cardnumber % oC
                    page.composite(
                        inputcard,
                        int(col * (oCW + oIW) + oSH + mL + oIW),
                        int(row * (oCH + oIH) + oSV + mT + oIH),
                    )
                    inputcard.close()
                outputImage.sequence.append(page)
                page.close()
            del outputImage.sequence[0]
            outputImage.save(filename='output.pdf')

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
        ic = self.inputColumns.value()
        ir = self.inputRows.value()
        middle_row = ir / 2
        middle_col = ic / 2
        left = (
            self._center[0] - self.inputShiftHor.value() +
            (colnum - middle_col) * self.inputCardWidth.value() -
            (self.inputCardWidth.value() / 2) * (ic % 2 > 0) +
            self.inputInnerWidth.value() / 2
        )
        top = (
            self._center[1] - self.inputShiftVert.value() +
            (rownum - middle_row) * self.inputCardHeight.value() -
            (self.inputCardHeight.value() / 2) * (ir % 2 > 0) +
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

