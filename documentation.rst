LLSpy Documentation
===================


*LLSpy is a graphical and command line interface for lattice light sheet post-processing. It depends on the cudaDeconv binary created in the Betzig lab at Janelia Research Campus, and adds additional features that minimize user parameter input, perform image corrections and manipulations, and facilitate file handling*

Features of LLSpy
-----------------

* graphical user interface with persistent/saveable processing settings
* command line interface for remote/server usage (coming)
* preview processed image to verify settings prior to processing full experiment
* *Pre-processing corrections*:
* correct "residual electron" issue on Flash4.0 when using overlap synchronous mode.  Includes CUDA and parallel CPU processing as well as GUI for generation of calibration file.
 apply selective median filter to particularly noisy pixels
 trim image edges prior to deskewing (helps with CMOS edge row artifacts)
 auto-detect background
* Processing:
  * select subset of acquired images (C or T) for processing
  * automatic parameter detection based on auto-parsing of Settings.txt
  * automatic OTF generation/selection from folder of raw PSF files, based on date of acquisition, mask used (if entered into SPIMProject.ini), and wavelength.
  * graphical progress bar and time estimation
* Post-processing:
  * proper voxel-size metadata embedding (newer version of Cimg)
  * join MIP files into single hyperstack viewable in ImageJ/Fiji
  * automatic width/shift selection based on image content ("auto crop to features")
  * automatic fiducial-based image registration (provided tetraspeck bead stack)
  * compress raw data after processing
* Watched-folder autoprocessing (experimental):
  * Server mode: designate a folder to watch for incoming *finished* LLS folders (with Settings.txt)
    file.  When new folders are detected, they are added to the processing queue and the queue is
    started if not already in progress.
  * Aquisition mode: designed to be used on the aquisition computer.  Designate folder to watch for
    new LLS folders, and process new files as they arrive.  Similar to built in GPU processing tab
    in Lattice Scope software, but with the addition of all the corrections and parameter selection
    in the GUI.
* easily return LLS folder to original (pre-processed) state
* compress and decompress folders and subfolders with lbzip2 (not working on windows)
* concatenate two experiments - renaming files with updated relative timestamps and stack numbers
* rename files acquired in script-editor mode with "Iter_" in the name to match standard naming
 with positions (work in progress)
* cross-platform: includes precompiled binaries and shared libraries that should work on all systems.


*Known Issues & Bugs*
*********************

* When unexpected errors occur mid-processing, sometimes the "cancel" button does nothing, forcing a restart.

Bug reports are very much appreciated: talley@hms.harvard.edu


Menu Bar
========

asdfdsa
----------------------

**File Menu**

* **Quit** *(ctrl-Q)*: Quit the program
* **Open LLSdir** *(ctrl-O)*: Opens file dialog to add an LLSdir to the queue
* **Save Settings as Default** *(ctrl-S)*: Saves the current GUI state as default
* **Load Default Settings** *(ctrl-D)*: Loads the default GUI state

NOTE: the program starts up not with the "default" settings, but with the GUI state
from the previous session.

**Process Menu**

* **Preview** *(ctrl-P)*: Preview the highlighted item in the list with the current settings
* **Run** *(ctrl-R)*: Start the processing queue


Toolbar
=======

*The toolbar provides shortcuts to some file-handling routines.*


dfdasdfdasf asdf dsaff
----------------------

**Reduce to Raw**

Deletes any GPUdecon, Deskwed, Corrected, and MIP folders, restoring folder to state immediately after aquisition.  Note, in the config tab, there is an option to "Save MIP folder during reduce to raw".  This alters the behavior of this function to leave any MIP folders for easy preview in the future.

**Compress Raw**

Uses lbzip2 (fast parallel compression) to compress the raw data of selected folders to save space.  Note, this currently only works on Linux and OS X, as I have not yet been able to compile lbzip2 or pbzip for Windows.  Alternatives exist (pigz), but bzip2 compression has a nice tradeoff between speed and compression ratio.

**Decompress Raw**

Decompress any compressed raw.tar.bz files in the selected folders.

**Concatenate**

Combine selected folders as if they had been acquired in a single acquisition.  Files are renamed such that the relative timestamp and stack number of the 'appended' dataset starts off where the first dataset ends.

**Rename Scripted**

In progress: Rename "Iter" files acquired in script editor mode to fit standard naming convention.

Process Tab
===========

*This tab has all of the settings for cudaDeconv and associated processing routines.*

Folder Queue ListBox
----------------------
Drag and drop LLS folders into the table (blank) area towards the top of the process tab to add them to the processing queue.  Folders without a settings.txt file will be ignored.  Basic experimental parameters are parsed from Settings.txt and folder structure and displayed.
Future option may allow overwriting angle, dz, and dx in this list.
