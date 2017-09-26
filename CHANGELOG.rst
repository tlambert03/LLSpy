LLSpy Release History
#####################

`Next release`_
===============

**Added:**

* Allow cRange subset in Preview
* `spimagine <https://github.com/maweigert/spimagine>`_ preview option with fallback to matplotlib if not installed
* Option to close all preview windows in View menu
* Option to quit LLSpy without confirmation
* Allow to preview a subset of a compressed dataset without decompressing the whole thing
* Search path for available compression options in {lbzip2, pbzip2, pigz, gzip, bzip2}

**Changed:**

* Rewritten native pyqt matplotlib image previewer
* pigz default compression for windows, lbzip2 default for mac/linux
* Improved handling of compression binaries
* Improved shared library detection

**Fixed:**

* Native pyqt previewer eliminates the 'App already exists' bug on image preview

`0.1.0`_ | 2017-09-13
=====================

* Initial Release


.. _Next release: https://github.com/tlambert03/llspy2/

.. _0.1.0: https://github.com/tlambert03/llspy2/releases/v0.1.0
