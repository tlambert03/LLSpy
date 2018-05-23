LLSpy Release History
#####################

`0.3.8`_
========

**Fixed:**

* tifffile update broke ability to read tiff bit depth.
* dependency versions now explicity listed


`0.3.7`_
========

**Fixed:**

* hotfix: FlashParams filename roi was not getting correctly parsed, causing failure when the calibrated chip size was not 1024 x 512.

`0.3.6`_
========

**Added:**

* lots of documentation on the Flash camera artifact and LLSpy camera corrections.
* CLI ``lls compress`` command now has folder recursion and filtering by experiment age.  useful for data server maintenance: quickly compress/freeze old data.
* option in gui to delete unregistered files when performing channel registration

**Changed:**

* llspy/parse.py filter functions now allow exclusive filtering in addition to inclusive
* better error message in rename_iters when there is only a single Iteration being processed
* ``lls install`` now accepts llspy_extra.zip file as well as llspy_extra directory

**Fixed:**

* fixed erroneous "each iteration the same number of tiffs" error in rename_iters
* fixed "Cannot create a file" bug in rename_iters when there is only a single position in the acquisition script. (thanks Mathieu)
* (hopefully) fix IndexError in rename_iters in cases where Iter_n does not start at Iter_0.
* fixed IndexError when no *dark*.tif images are present in the camera calibration folder (thanks Mathieu)
* registration was skipping timepoints when the reference wavelength string appeared in the filename (thanks Lin)

`0.3.5`_
========

**Added:**

* CLI ```lls show``` command: quickly preview LLSdir (MIPS or z-stack) from command line.

**Fixed:**

* bug: reg-preview was not using the just-generated registration file
* many bug fixes related to previewing registration results

`0.3.4`_
========

**Added:**

* new option (in config tab) to enable adding folders without settings.txt file.  Pick default values for missing options, and ability to directly change dx/dz/angle in the process queue.
* new Merge Mips option under Tools menu (merge folder of individual MIPs after processing)
* reveal in finder/explorer option

**Changed:**

* CLI ```lls info``` command now calculates sizes
* CLI ```lls info``` recurses to specified depth
* changed internals representing timepoints (tset) and channels (cset) in LLSdir.  Should prevent unexpected bugs in long run, may introduce unexpected things in the short term.
* internal change, GUI queue box now stores/updates LLSdir instances.
* give more meaningful error when folder is added that has tiffs and a settings.txt file, but not with the recognized naming convention.

**Fixed:**

* bug: napodize and nzblend parameters were not getting passed to cudaDeconv
* memory leak when closing preview window (wasn't releasing RAM required for image)
* bugs resulting when the base part of the filename is interpreted as a non-string integer. (such as unsupported operand type(s) for +: 'int' and 'str' during mipmerge)



`0.3.3`_
========

**Added:**

* exposed "min bead number" parameter for automated bead detection in the gui, as well as manual intensity threshold.
* alert when automated bead detection gives suspicious results (dramatically different number of beads in each channel).
* ability to undo "Rename Scriped" (rename_iters function), under Process Menu

**Changed:**

* more robust settings.txt file parsing (thanks for sample Carlos!)
* refactored the rename_iters function to be more robust
* slightly stricter OTF file naming regex.  updated docs accordingly

**Fixed:**

* fixed "invalid literal for int() with base 10" bug in refRegWave validation
* (hopefully) fixed bug that bugs you to update llspy_extra when you've already done it.  If this still fails, consider reinstalling (deleting your 'llsenv' anaconda environment and starting again with a fresh one).

`0.3.2`_
========

*SLM pattern generator moved into seperate package: ```slmgen```.  Multiple additions and changes to SLM Pattern generator.  Please see https://github.com/tlambert03/llspy-slm for full changelog, and further development.*

**Added:**

* improved docs on registration

**Changed:**

* removed confusing error seen when using ```lls path/to/llspy_extra```
* modifications made to LLSpy to move SLMgen into seperate package.


`0.3.1`_
========

**Fixed:**

* fixed SLM preview glitch on Windows

`0.3.0`_
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

.. _0.3.4: https://github.com/tlambert03/LLSpy/releases/0.3.4
.. _0.3.3: https://github.com/tlambert03/LLSpy/releases/0.3.3
.. _0.3.2: https://github.com/tlambert03/LLSpy/releases/0.3.2
.. _0.3.1: https://github.com/tlambert03/LLSpy/releases/0.3.1
.. _0.3.0: https://github.com/tlambert03/LLSpy/releases/0.3.0
.. _0.2.4: https://github.com/tlambert03/LLSpy/releases/0.2.4
.. _0.2.3: https://github.com/tlambert03/LLSpy/releases/0.2.3
.. _0.2.2: https://github.com/tlambert03/LLSpy/releases/0.2.2
.. _0.2.1: https://github.com/tlambert03/LLSpy/releases/0.2.1
.. _0.1.0: https://github.com/tlambert03/LLSpy/releases/v0.1.0
