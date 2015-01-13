YACK - Yet Another Cardmaking Kit
=================================

[![Gitter](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/court-jus/yack?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

This project has started on this thread [(PnP Cards - thin white line or not?)](https://boardgamegeek.com/thread/1290914/pnp-cards-thin-white-line-or-not) where we were discussing about our prefered layout for PnP files. I already had this idea in mind but the thread put me on the rails, I've started to write a tool to allow anyone to change the layout of cards on the pages of a PDF file.

The principle is to open the original file, the one provided by the game designer, describe its layout (or choose a saved one) and then describe the desired layout (or again, choose a saved one).

The tool should display a live preview of how the output will look like and should also permit to extract the cards as individual files for POD services.

----

## Current status

Actively developed, open for test from whoever is willing to "do it the hard way". There is no automatic installation, not event a package, you will have to download the sources by yourself, find out what needs to be installed to make the software run.

## What is currently working :
- open an input file
- describe the input layout
- preview cards extracted by this layout (navigate in the pages and individual cards of the PDF)
- extract all the cards to individual files
- describe the output layout
- preview the expected output

## What is next on the roadmap :
- have the tool generate an output PDF
- create some package for easy installation on Linux and Windows (sorry, you Mac users but I don't own a Mac so I can't work on it)

----

## Technical stuff

The tool is written in Python, using the PyQT5 library for the UI and the ImageMagick "Wand" library for image manipulation.

I've uploaded a video showing the tool "at work" : http://youtu.be/bH9S_6dlvNg

Example:
![Screen shot](https://github.com/court-jus/yack/raw/master/scrot/yack_teasing1.jpg "Teasing")
