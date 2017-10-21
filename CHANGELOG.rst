LLSpy Release History
#####################

Next Version
============

`0.3.1`_
========

**Added:**

* Hex pattern generator added to SLM Pattern Generator
* Ronchi-ruling pattern generator added to SLMgen
* Batch SLM pattern generation
* Docs for SLM generator GUI
* Option to dither SLM preview in SLM Pattern Generator
* User-adjustable LUTs for SLM pattern previews

**Changed:**

* SLM pattern generator moved into seperate package: *slmgen*
* Better multi-threading when batch-writing SLM patterns

**Fixed:**

* SLM pattern generator now writes 1-bit file usable on SLM, instead of 8-bit png (thank you for reporting Felix!)


`0.3.1`_
========

**Fixed:**

* fixed SLM preview glitch on Windows

`0.3.1`_
========

**Added:**

* added new SLM Pattern generator feature.
* ability to overlay channels in matplotlib viewer (still not possible in spimagine)
* support for multiple GPUs. Work will be split across GPUs enabled in config tab. `a798788  <https://github.com/tlambert03/LLSpy/commit/a79878831edc0e66dd6a2f7a4700b64f908c7fb8>`_
* new registration tab in gui with ability to quickly preview registration effectiveness `929f53b6 <https://github.com/tlambert03/LLSpy/commit/929f53b65396aa60aab69220b9ae5e8117dc65bf>`_
* ability to create reusable registration file and new RegFile class to parse registration files`03b67345 <https://github.com/tlambert03/LLSpy/commit/03b6734589a792fad7269d1049002a32c72ea08d>`_


**Changed:**

* many small changes implemented to take advantage of new regfile class
* registration now defaults to world coordinates (should work on datasets with different voxel sizes from fiducials)

**Fixed:**

* fixed "long division or modulo by zero" error that sometimes appeared in matplotlib viewer
* fixed bug that prevented processing of a subset of channels when the channel number was > 0
* fixed bug when joining MIPs on a dataset with only 1 timepoint
* various other small bug fixes


`0.2.4`_
========

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
========

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
========

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
