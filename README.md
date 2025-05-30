pdfminer.six
============

[![Continuous integration](https://github.com/pdfminer/pdfminer.six/actions/workflows/actions.yml/badge.svg)](https://github.com/pdfminer/pdfminer.six/actions/workflows/actions.yml)
[![PyPI version](https://img.shields.io/pypi/v/pdfminer.six.svg)](https://pypi.python.org/pypi/pdfminer.six/)
[![gitter](https://badges.gitter.im/pdfminer-six/Lobby.svg)](https://gitter.im/pdfminer-six/Lobby?utm_source=badge&utm_medium)

*We fathom PDF*

Pdfminer.six is a community maintained fork of the original PDFMiner. It is a tool for extracting information from PDF
documents. It focuses on getting and analyzing text data. Pdfminer.six extracts the text from a page directly from the
sourcecode of the PDF. It can also be used to get the exact location, font or color of the text.

It is built in a modular way such that each component of pdfminer.six can be replaced easily. You can implement your own
interpreter or rendering device that uses the power of pdfminer.six for other purposes than text analysis.

Check out the full documentation on
[Read the Docs](https://pdfminersix.readthedocs.io).


Features
--------

* Written entirely in Python.
* Parse, analyze, and convert PDF documents.
* Extract content as text, images, html or [hOCR](https://en.wikipedia.org/wiki/HOCR).
* Support for PDF-1.7 specification (well, almost).
* Support for CJK languages and vertical writing.
* Support for various font types (Type1, TrueType, Type3, and CID) support.
* Support for extracting embedded images (JPG, PNG, TIFF, JBIG2, bitmaps).
* Support for decoding various compressions (ASCIIHexDecode, ASCII85Decode, LZWDecode, FlateDecode, RunLengthDecode,
  CCITTFaxDecode)
* Support for RC4 and AES encryption.
* Support for AcroForm interactive form extraction.
* Table of contents extraction.
* Tagged contents extraction.
* Automatic layout analysis.

How to use
----------

* Install Python 3.9 or newer.
* Install pdfminer.six.
  ```bash
  pip install pdfminer.six

* (Optionally) install extra dependencies for extracting images.

  ```bash
  pip install 'pdfminer.six[image]'

* Use the command-line interface to extract text from pdf.

  ```bash
  pdf2txt.py example.pdf

* Or use it with Python. 
  ```python
  from pdfminer.high_level import extract_text

  text = extract_text("example.pdf")
  print(text)
  ```

Contributing
------------

Be sure to read the [contribution guidelines](https://github.com/pdfminer/pdfminer.six/blob/master/CONTRIBUTING.md). 

Acknowledgement
---------------

This repository includes code from `pyHanko` ; the original license has been included [here](/docs/licenses/LICENSE.pyHanko).
