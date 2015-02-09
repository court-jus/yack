# -*- config: utf-8 -*-

import sys
import argparse
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
    def __init__(self, filename=None, inputlayout=None, outputlayout=None,
                 resolution=300, output=None, extract=None, cardsdir=None,
                 ):
        super(Yack, self).__init__()
        self.setupUi(self)
        self.filename = filename
        self.cardsDir = cardsdir
        self.inputScene = QtWidgets.QGraphicsScene()
        self.cardScene = QtWidgets.QGraphicsScene()
        self.outputScene = QtWidgets.QGraphicsScene()
        self._image = None
        self._image_cache = {}
        self._center = [0, 0]
        self.currentPage = 0
        self.currentPageIdx = 0
        self.activePages = [0]
        self.currentCard = 0
        self.inputGView.setScene(self.inputScene)
        self.cardGView.setScene(self.cardScene)
        self.cardGView.scale(3, 3)
        self.outputGView.setScene(self.outputScene)
        # Menu
        self.actionExit.triggered.connect(self.close)
        self.actionOpen.triggered.connect(self.chooseFile)
        self.actionOpenCardsDir.triggered.connect(self.chooseCardDir)
        self.actionSaveCards.triggered.connect(lambda: self.exportCards())
        self.actionSaveOutput.triggered.connect(lambda: self.exportOutput())
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
        self.workResolution.setValue(resolution)
        self._oldResolution = self.workResolution.value()
        if inputlayout is not None:
            self.openLayout('input', filename=inputlayout)
        if outputlayout is not None:
            self.openLayout('output', filename=outputlayout)
        for widget in [
            self.inputCardWidth, self.inputCardHeight,
            self.inputShiftHor, self.inputShiftVert,
            self.inputInnerWidth, self.inputInnerHeight,
            self.outputCardWidth, self.outputCardHeight,
            self.outputShiftHor, self.outputShiftVert,
            self.outputInnerWidth, self.outputInnerHeight,
            self.cropMarksLength, self.cropMarksThickness,
            self.cropMarksCenter,
        ]:
            if self.workResolution.value() != 300:
                if widget.value() > 0:
                    widget.setValue(max(1, int(widget.value() * self.workResolution.value() / 300)))
        for widget in [
            self.inputCardWidth, self.inputCardHeight,
            self.inputRows, self.inputColumns,
            self.inputShiftHor, self.inputShiftVert,
            self.inputInnerWidth, self.inputInnerHeight,
        ]:
            widget.valueChanged.connect(self.updateCard)
            widget.valueChanged.connect(self.showInputPage)
        for widget in [
            self.outputCardWidth, self.outputCardHeight,
            self.outputRows, self.outputColumns,
            self.outputShiftHor, self.outputShiftVert,
            self.outputInnerWidth, self.outputInnerHeight,
            self.outputPageWidth, self.outputPageHeight,
            self.cropMarksLength, self.cropMarksThickness,
            self.cropMarksCenter,
        ]:
            widget.valueChanged.connect(lambda v: self.showOutputPage())
        self.showGuides.stateChanged.connect(lambda v: self.showInputPage())
        self.cropMarksInner.stateChanged.connect(lambda v: self.showOutputPage())
        self.cropMarksColor.textEdited.connect(lambda v: self.showInputPage())
        self.inputIgnoredPages.textEdited.connect(lambda v: self.computeIgnoredPages())
        self.applyResolutionBtn.clicked.connect(lambda v: self.changeResolution())
        if self.filename:
            self.openFile(self.filename, batch=(output or extract))
        if self.cardsDir and not (output or extract):
            self.updateAll()
        if output:
            self.exportOutput(output)
        if extract:
            self.exportCards(extract)
        if output or extract:
            sys.exit(0)

    # Choose and update current
    def computeIgnoredPages(self, batch=False):
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
        except:
            traceback.print_exc()
            self.statusbar.showMessage("Error: can't understand your ignored pages input.", 1500)
        if not batch:
            self.setCurrent(page=0, card=0)
            self.updateAll()

    def setCurrent(self, page=None, card=None, relPage=None, relCard=None):
        cp = self.currentPage
        cc = self.currentCard
        cardCount = self.inputRows.value() * self.inputColumns.value() * len(self.activePages)
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
            "{0}/{1} ({2}) - {3}/{4}".format(self.currentPageIdx + 1, len(self.activePages),
                                       self.currentPage + 1,
                                       self.currentCard + 1, cardCount)
        )
        if self.currentPage != cp:
            self.showInputPage(page=self.currentPage)
        if self.currentCard != cc:
            self.showCardPixmap(card=self.currentCard)

    def changeResolution(self):
        if self._oldResolution is not None:
            if self._oldResolution == self.workResolution.value():
                return
            fact = float(self.workResolution.value()) / float(self._oldResolution)
            for w in [
                self.inputCardWidth, self.inputCardHeight,
                self.inputShiftHor, self.inputShiftVert,
                self.inputInnerWidth, self.inputInnerHeight,
                self.outputCardWidth, self.outputCardHeight,
                self.outputShiftHor, self.outputShiftVert,
                self.outputInnerWidth, self.outputInnerHeight,
                self.cropMarksLength, self.cropMarksThickness,
                self.cropMarksCenter,
            ]:
                w.setValue(int(w.value() * fact))
                self._oldResolution = self.workResolution.value()
            self.zoom(1.0/fact)
        if self.filename:
            self.openFile(self.filename)

    def updateAll(self):
        self.showInputPage(page=self.currentPage, force=True)
        self.showCardPixmap(card=self.currentCard, force=True)
        self.showOutputPage()

    def updateCard(self):
        self.showCardPixmap(card=self.currentCard)
        self.showOutputPage()

    def clearScene(self, scene):
        for i in scene.items():
            scene.removeItem(i)

    def getPixmap(self, ident, fn, force=False, *args, **kwargs):
        if ident not in self._image_cache or force:
            self._image_cache[ident] = fn(*args, **kwargs)
        return self._image_cache[ident]

    def showCardPixmap(self, card=0, force=False):
        self.clearScene(self.cardScene)
        self.cardScene.addPixmap(self.getCardPix(card, force=force))

    def showFullPage(self, page=0):
        with Image(blob=self._image, resolution=self.workResolution.value()) as img:
            if page >= len(img.sequence):
                return QtGui.QPixmap()
            page = Image(img.sequence[page], resolution=self.workResolution.value())
            xpm = page.make_blob(format='xpm')
            pix = QtGui.QPixmap()
            pix.loadFromData(xpm)
            return pix

    def showInputPage(self, page=0, force=False):
        self.clearScene(self.inputScene)
        if self.cardsDir:
            return
        pix = self.getPixmap(
            'page{0}'.format(self.currentPage),
            self.showFullPage, page=page, force=force)
        pageWidth = self._center[0] * 2
        pageHeight = self._center[1] * 2
        self.inputScene.addPixmap(pix)
        shiftedh = self._center[0] - self.inputShiftHor.value()
        shiftedv = self._center[1] - self.inputShiftVert.value()
        if self.showGuides.isChecked():
            self.inputScene.addRect(0, 0, pageWidth, pageHeight)
            for i in range(self.inputRows.value() * self.inputColumns.value()):
                l, t, w, h = self.getCropCoords(i)
                pen = QtGui.QPen(QtGui.QColor('#ff0000'))
                self.inputScene.addRect(l, t, w, h, pen=pen)

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
        allCardsWidth = oC * oCW + oC + oIW
        allCardsHeight = oR * oCH + oR + oIH
        mL = (pageWidth - allCardsWidth) / 2
        mT = (pageHeight - allCardsHeight) / 2
        self.outputScene.addRect(0, 0, pageWidth, pageHeight)
        brush = QtGui.QBrush(QtGui.QColor(self.outputInnerColor.text()))
        pen = QtGui.QPen(QtGui.QColor(self.outputInnerColor.text()))
        for coln in range(self.outputColumns.value()):
            for rown in range(self.outputRows.value()):
                left = mL + coln * oCW
                top = mT + rown * oCH
                if oIH:
                    self.outputScene.addRect(left, top, oCW + oIW, oIH, pen=pen, brush=brush)
                    self.outputScene.addRect(left, top + oCH, oCW + oIW, oIH, pen=pen, brush=brush)
                if oIW:
                    self.outputScene.addRect(left, top, oIW, oCH + oIH, pen=pen, brush=brush)
                    self.outputScene.addRect(left + oCW, top, oIW, oCH + oIH, pen=pen, brush=brush)
        if self.cropMarksThickness.value() > 0:
            cMT = self.cropMarksThickness.value()
            cML = self.cropMarksLength.value()
            cMC = self.cropMarksCenter.value()
            cMI = self.cropMarksInner.isChecked()
            pen = QtGui.QPen(QtGui.QColor(self.cropMarksColor.text()), cMT)
            for coln in range(self.outputColumns.value() + 1):
                for rown in range(self.outputRows.value() + 1):
                    if (coln > 0 and coln < self.outputColumns.value() and
                        rown > 0 and rown < self.outputRows.value() and
                        not cMI
                    ):
                        continue
                    cent = (coln * oCW + oSH + mL + oIW / 2,
                            rown * oCH + oSV + mT + oIH / 2)
                    if cMI or coln == 0:
                        self.outputScene.addLine(
                            cent[0] - cML, cent[1],
                            cent[0] - cMC, cent[1],
                            pen=pen,
                        )
                    if cMI or coln == self.outputColumns.value():
                        self.outputScene.addLine(
                            cent[0] + cML, cent[1],
                            cent[0] + cMC, cent[1],
                            pen=pen,
                        )
                    if cMI or rown == 0:
                        self.outputScene.addLine(
                            cent[0], cent[1] - cML,
                            cent[0], cent[1] - cMC,
                            pen=pen,
                        )
                    if cMI or rown == self.outputRows.value():
                        self.outputScene.addLine(
                            cent[0], cent[1] + cML,
                            cent[0], cent[1] + cMC,
                            pen=pen,
                        )
        for cardnumber in range(ncards):
            cardidx = cardnumber + firstcard
            try:
                inpage = self.activePages[cardidx // nincards]
            except IndexError:
                # We have more output cards than input cards
                # we then take the first page again
                inpage = self.activePages[0]
            incard = cardidx % nincards
            pix = self.getCardPix(cardnumber)
            if pix:
                pix = pix.scaled(oCW - oIW, oCH - oIH)
                item = self.outputScene.addPixmap(pix)
                row = cardnumber // oC
                col = cardnumber % oC
                item.setPos(
                    col * oCW + oSH + mL + oIW,
                    row * oCH + oSV + mT + oIH,
                )

    def getCardPix(self, card, force=False):
        # Used for preview
        if card in self._image_cache and not force:
            return self._image_cache[card]
        if self.cardsDir:
            if force or 'pix{0}'.format(card) not in self._image_cache:
                img = self.cardImage(card, force=force)
                xpm = img.make_blob(format='xpm')
                pix = QtGui.QPixmap()
                pix.loadFromData(xpm)
                self._image_cache['pix{0}'.format(card)] = pix
            return self._image_cache['pix{0}'.format(card)]
        page = card // (self.inputRows.value() * self.inputColumns.value())
        card = card % (self.inputRows.value() * self.inputColumns.value())
        fullpage = self.getPixmap('page{0}'.format(page), self.showFullPage, page=page)
        l, t, w, h = self.getCropCoords(card)
        self._image_cache[card] = fullpage.copy(l, t, w, h)
        return self._image_cache[card]

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

    def chooseCardDir(self):
        dirname = QtWidgets.QFileDialog.getExistingDirectory(self, "Open cards directory...")
        if dirname:
            self.cardsDir = dirname
            self.updateAll()

    def openFile(self, filename, batch=False):
        self._image_cache = {}
        self.cardsDir = None
        with Image(filename=filename, resolution=self.workResolution.value()) as img:
            self.allPages = list(range(len(img.sequence)))
            self.activePages = self.allPages[:]
            self._center = [s/2 for s in img.size]
            self._image = img.make_blob()
            self.computeIgnoredPages(batch=batch)

    def _exportCards(self, dirname=None):
        if dirname is None:
            dirname = QtWidgets.QFileDialog.getExistingDirectory(self, "Export cards to...")
        if not dirname:
            return
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
                        card.save(filename=os.path.join(dirname, 'page{0}card{1}.png'.format(p, c)))
        self.statusbar.showMessage("Export done.", 1500)

    def exportCards(self, dirname=None):
        if dirname is None:
            dirname = QtWidgets.QFileDialog.getExistingDirectory(self, "Export cards to...")
        if not dirname:
            return
        pages = self.activePages
        ncards = self.inputColumns.value() * self.inputRows.value()
        total_cards = len(pages) * ncards
        current_card = 0
        self.statusbar.showMessage("Exporting...")
        # TODO : (optional : add inner margin)
        for cN in range(total_cards):
            self.statusbar.showMessage(
                "Exporting... card {0}".format(cN + 1))
            card = self.cardImage(cN, force=True)
            card.save(filename=os.path.join(dirname, 'card{0}.png'.format(cN)))
        self.statusbar.showMessage("Export done.", 1500)

    def exportOutput(self, filename=None):
        if filename is None:
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save output to...", None,
                "PDF (*.pdf);;All files (*)",
            )
        if not filename:
            return
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
        allCardsWidth = oC * oCW
        allCardsHeight = oR * oCH
        mL = int((pageWidth - allCardsWidth) / 2)
        mT = int((pageHeight - allCardsHeight) / 2)
        print(mL, mT, pageWidth, allCardsWidth, pageHeight, allCardsHeight)
        totalInputCards = nincards * len(self.activePages)
        if self.cardsDir:
            totalInputCards = len(os.listdir(self.cardsDir))
        totalOutputPages = totalInputCards // ncards + (1 if totalInputCards % ncards > 0 else 0)
        draw = Drawing()
        draw.fill_color = Color(self.outputInnerColor.text())
        def drawrectangle(**kwargs):
            newvals = {}
            for k, v in kwargs.items():
                newvals[k] = max(0, int(v))
            draw.rectangle(**newvals)
        draw.fill_color = Color(self.outputInnerColor.text())
        for coln in range(self.outputColumns.value()):
            for rown in range(self.outputRows.value()):
                left = mL + coln * oCW
                top = mT + rown * oCH
                if oIH:
                    drawrectangle(left=left, top=top, right=left + oCW + oIW, bottom=top + oIH)
                    drawrectangle(left=left, top=top + oCH, right=left + oCW + oIW, bottom=top + oCH + oIH)
                if oIW:
                    drawrectangle(left=left, top=top, right=left + oIW, bottom=top + oCH + oIH)
                    drawrectangle(left=left + oCW, top=top, right=left + oCW + oIW, bottom=top + oCH + oIH)
        if self.cropMarksThickness.value() > 0:
            cMT = self.cropMarksThickness.value()
            cML = self.cropMarksLength.value()
            cMC = self.cropMarksCenter.value()
            cMI = self.cropMarksInner.isChecked()
            draw.fill_color = Color(self.cropMarksColor.text())
            for coln in range(self.outputColumns.value() + 1):
                for rown in range(self.outputRows.value() + 1):
                    if (coln > 0 and coln < self.outputColumns.value() and
                        rown > 0 and rown < self.outputRows.value() and
                        not cMI
                    ):
                        continue
                    cent = (coln * oCW + oSH + mL + oIW / 2,
                            rown * oCH + oSV + mT + oIH / 2)
                    if cMI or coln == 0:
                        drawrectangle(
                            left=cent[0] - cML, top=cent[1]-cMT/2,
                            right=cent[0] - cMC, bottom=cent[1]+cMT/2,
                        )
                    if cMI or coln == self.outputColumns.value():
                        drawrectangle(
                            left=cent[0] + cMC, top=cent[1]-cMT/2,
                            right=cent[0] + cML, bottom=cent[1]+cMT/2,
                        )
                    if cMI or rown == 0:
                        drawrectangle(
                            left=cent[0]-cMT/2, top=cent[1] - cML,
                            right=cent[0]+cMT/2, bottom=cent[1] - cMC,
                        )
                    if cMI or rown == self.outputRows.value():
                        drawrectangle(
                            left=cent[0]-cMT/2, top=cent[1] + cMC,
                            right=cent[0]+cMT/2, bottom=cent[1] + cML,
                        )
        with Image(width=pageWidth, height=pageHeight, resolution=self.workResolution.value()) as outputImage:
            for oPageNum in range(totalOutputPages):
                firstcard = oPageNum * ncards
                page = Image(width=pageWidth, height=pageHeight)
                draw(page)
                for cardnumber in range(ncards):
                    self.statusbar.showMessage("Exporting... {0} {1}".format(oPageNum, cardnumber))
                    cardidx = cardnumber + firstcard
                    print("card", cardidx)
                    inputcard = self.cardImage(cardidx, force=True)
                    # scale to output
                    inputcard.resize(width=oCW-oIW, height=oCH-oIH)
                    row = cardnumber // oC
                    col = cardnumber % oC
                    page.composite(
                        inputcard,
                        int(col * oCW + oSH + mL + oIW),
                        int(row * oCH + oSV + mT + oIH),
                    )
                    inputcard.close()
                outputImage.sequence.append(page)
                page.close()
            del outputImage.sequence[0]
            outputImage.save(filename=filename)

        self.statusbar.showMessage("Export done.", 1500)

    def openLayout(self, layout='input', filename=None):
        if filename is None:
            filename, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open layout file...", None,
                "JSON (*.json);;All files (*)",
            )
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

    def cardImage(self, card, force=False):
        if card in self._image_cache and not force:
            return self._image_cache[card]
        page_idx = card // (self.inputRows.value() * self.inputColumns.value())
        card_idx = card %  (self.inputRows.value() * self.inputColumns.value())
        img = None
        if self.cardsDir is not None:
            try:
                cardname = os.listdir(self.cardsDir)[card]
            except IndexError:
                cardname = os.listdir(self.cardsDir)[0]
            img = Image(
                filename=os.path.join(self.cardsDir, cardname),
                resolution=self.workResolution.value()
            )
            self._image_cache[card] = img
            return img
        try:
            page = self.activePages[page_idx]
        except IndexError:
            page = self.activePages[0]
        with Image(blob=self._image, resolution=self.workResolution.value()) as img:
            p = img.sequence[page]
            l, t, w, h = self.getCropCoords(card_idx)
            img = p[l:l+w, t:t+h]
        self._image_cache[card] = img
        return img

    # Helpers
    def layoutToDict(self, layout='input'):
        result = {}
        for attrname in dir(self):
            if (
                attrname.startswith(layout) or
                layout == 'output' and attrname.startswith('cropMarks')
            ):
                widget = getattr(self, attrname)
                key = attrname
                if hasattr(widget, 'value'):
                    result[key] = widget.value()
                elif hasattr(widget, 'text'):
                    result[key] = widget.text()
        return result

    def dictToLayout(self, layoutDict, layout='input'):
        for k, v in layoutDict.items():
            widget = None
            if hasattr(self, k):
                widget = getattr(self, k)
            elif hasattr(self, layout + k):
                widget = getattr(self, layout + k)
            if widget:
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
            (colnum - middle_col) * self.inputCardWidth.value() +
            self.inputInnerWidth.value() / 2
        )
        top = (
            self._center[1] - self.inputShiftVert.value() +
            (rownum - middle_row) * self.inputCardHeight.value() +
            self.inputInnerHeight.value() / 2
        )
        width = self.inputCardWidth.value() - self.inputInnerWidth.value()
        height = self.inputCardHeight.value() - self.inputInnerHeight.value()
        return map(int, [left, top, width, height])


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('inputfile', metavar='FILE', nargs='?')
    parser.add_argument('-I', '--input-layout', dest='inputlayout', action='store')
    parser.add_argument('-O', '--output-layout', dest='outputlayout', action='store')
    parser.add_argument('-r', '--resolution', dest='resolution', action='store', default=300, type=int)
    parser.add_argument('-o', '--output', dest='outputfile', action='store')
    parser.add_argument('-x', '--extract-to', dest='extract', action='store')
    parser.add_argument('-d', '--cards-dir', dest='cardsdir', action='store')
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)

    yack = Yack(
        filename=args.inputfile, inputlayout=args.inputlayout,
        outputlayout=args.outputlayout, resolution=args.resolution,
        output=args.outputfile, extract=args.extract,
        cardsdir=args.cardsdir,
    )
    yack.show()

    sys.exit(app.exec_())

