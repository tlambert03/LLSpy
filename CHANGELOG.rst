LLSpy Release History
#####################

`0.2.3`_
===============

**Added:**

* new registration tab in gui (929f53b65396aa60aab69220b9ae5e8117dc65bf)
* ability to reusable registration file (cc3f771d8907508b67648c89334affe2d693f709)

**Changed:**

* registration now defaults to world coordinates (should work with different voxel sizes)

**Fixed:**

* properly parse 24-hour timestamp in settings.txt (36d4ed0e71e5a6a7dcae62cd778a0e48f3d29610)


`0.2.2`_
===============

**Changed:**

* much improved docs structure and rtd build
* gui pngs added to conda.recipe

**Fixed:**

* version not properly reported in command line interface


`0.2.1`_
========

**Added:**

* Allow cRange subset in Preview
* `spimagine <https://github.com/maweigert/spimagine>`_ preview option with fallback to matplotlib if not installed
* Option to close all preview windows in View menu
* Option to quit LLSpy without confirmation
* Allow to preview a subset of a compressed dataset without decompressing the whole thing
* Search path for available compression options in {lbzip2, pbzip2, pigz, gzip, bzip2}
* much improved exception handling in gui
* log to file

**Changed:**

* Rewritten native pyqt matplotlib image previewer
* pigz default compression for windows, lbzip2 default for mac/linux
* Improved handling of compression binaries
* Improved shared library detection
* improved validation of OTF dir, cudaDeconv binary path, and Camera Params tiff
* simplified otf search, including approximate wavelength search
* logging module used instead of print statements
* better log tab handling in the gui

**Fixed:**

* Native pyqt previewer eliminates the 'App already exists' bug on image preview
* bugfix in abspath search
*

`0.1.0`_ | 2017-09-13
=====================

* Initial Release


.. _Next release: https://github.com/tlambert03/LLSpy/

.. _0.2.1: https://github.com/tlambert03/LLSpy/releases/0.2.1

.. _0.1.0: https://github.com/tlambert03/LLSpy/releases/v0.1.0
