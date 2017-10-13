LLSpy Release History
#####################

Next Version
============

**Added:**

* new registration tab in gui `929f53b6 <https://github.com/tlambert03/LLSpy/commit/929f53b65396aa60aab69220b9ae5e8117dc65bf>`_
* create reusable registration file `03b67345 <https://github.com/tlambert03/LLSpy/commit/03b6734589a792fad7269d1049002a32c72ea08d>`_
* registration now defaults to world coordinates (should work with different voxel sizes)

`0.2.4`_
=========

**Added:**

* gpuCheckboxes added to config tab (disabled for now, future version will support multiple gpus)

**Changed:**

* camera calibration GUI calculates no longer requires dark_avg or dark_std... will calculate itself if \*dark\*.tifs present in selected folder.
* better feedback during camera calibration gui (still can't abort)
* disable acquisition watch mode until ready...

**Fixed:**

* important: fixed bug that causes crash when pressing preview button, if it had already failed once before f715f92
* improved robustness and error messages when looking for OTFs in OTFdir

`0.2.3`_
=========

**Added:**

* intelligible warning when openCL and CUDA clash.  Workaround for [Error -529697949] Windows Error 0xE06D7363 `b19c9bb <https://github.com/tlambert03/LLSpy/commit/b19c9bb15d589464df666cbc8537f91ee35c2456>`_
* option to disable spimagine import (and reenable easily) `39a761f <https://github.com/tlambert03/LLSpy/commit/39a761f1122416115d0d0df62f84f1e66ddaa700>`_
* list detected GPUs in logs at startup
* check for update on launch `41a8cb6 <https://github.com/tlambert03/LLSpy/commit/41a8cb6b465838f6542ffb6e4af2eadcf3aa4b63>`_

**Fixed:**

* properly parse 24-hour timestamp in settings.txt `36d4ed0e <https://github.com/tlambert03/LLSpy/commit/36d4ed0e71e5a6a7dcae62cd778a0e48f3d29610>`_
* fixed "handle is invalid" error on pyinstaller version
* fixed multi-argument parameters in the CLI
* don't allow trim sum greater than num pixels
* fixed bug: 'NoneType' object has no attribute 'text' when deleting items from queue `53e7fda <https://github.com/tlambert03/LLSpy/commit/53e7fda0c5cbf25a4071083a58e08de64de5bb38>`_

**Changed:**

* improved image scaling in matplotlib preview window
* better choosing of default binary for each platform
* much more useful information in the logs


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

.. _0.2.3: https://github.com/tlambert03/LLSpy/releases/0.2.3
.. _0.2.2: https://github.com/tlambert03/LLSpy/releases/0.2.2
.. _0.2.1: https://github.com/tlambert03/LLSpy/releases/0.2.1
.. _0.1.0: https://github.com/tlambert03/LLSpy/releases/v0.1.0
