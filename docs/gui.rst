.. _gui:

************************
Graphical User Interface
************************

**The following sections all refer to the GUI interface for LLSpy**

Menu Bar
--------

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
-------

*The toolbar provides shortcuts to some file-handling routines.*


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
-----------

*This tab has all of the settings for cudaDeconv and associated processing routines.*

Folder Queue ListBox
********************
Drag and drop LLS folders into the table (blank) area towards the top of the process tab to add them to the processing queue.  Folders without a settings.txt file will be ignored.  Basic experimental parameters are parsed from Settings.txt and folder structure and displayed.
Future option may allow overwriting angle, dz, and dx in this list.


Pre-Processing
**************
*Most of these options pertain to image corrections or modifications prior to processing with cudaDeconv.*

**Camera Corrections**

Checking the "Do Flash Correction" button to enable correction of the residual electron artifact seen in the Flash4.0 when using overlap/synchronous readout mode as is commonly done in the Lattice Scope software.  In this readout mode, pixels in the chip are not reset between exposures causing "carryover" charge from the previous exposure in the next exposure.  This can be seen as a noisy ghosting artifact in the second image in regions that were bright in the first image, which becomes particularly noticeable in deskewed and max projected images.

For correction, a calibration image must be specified in the "Camparam Tiff" field. This file is a tiff that holds parameters that describe the probability of carryover charge for each pixel (as a function of the intensity of that pixel in the previous image), along with the pixels specific offset (and optionally, noise).  This can be used to subtract the predicted carryover charge, minimizing the artifact.  For more information, see the `Generate Camera Calibration File`_ in the config tab.  This calibration file also includes an offset and noise map that can be further utilized for various corrections (#todo).  The program will use the ROI metadata in file Settings.txt file to crop the calibration image to the corresponding region used for the given experiment.

Camera correction can be done serially in a single thread on the CPU (CPU), with multithreading (parallel), or on the GPU (CUDA).

The "Do Median Filter" option will additionally replace particularly noisy pixels with the median value of its 8 neighboring pixels.  For more information see the supplement in `Amat et al. 2015 <http://www.nature.com/nprot/journal/v10/n11/abs/nprot.2015.111.html>`_.


  Amat, F., Höckendorf, B., Wan, Y., Lemon, W. C., McDole, K., & Keller, P. J. (2015). Efficient processing and analysis of large-scale light-sheet microscopy data. Nature Protocols, 10(11), 1679–1696. http://doi.org/10.1038/nprot.2015.111
  http://www.nature.com/nprot/journal/v10/n11/abs/nprot.2015.111.html

If "Save Corrected" is checked, the corrected pre-processed images will be saved.  Otherwise, they are deleted after processing to save space.


**Trim Edges**

These settings allow you crop a number of pixesl from each edge of the raw data volume prior to processing.

Sometimes when imaging a subregion of the chip on a CMOS camera, the last 1 or 2 rows on the edge will be particularly bright, especially if there is a bright object just outside of the ROI.  After deskewing and max projection, those bright edges often corrupt the image. Use Trim X Left and Trim X Right to crop pixels on the sides of the images prior to processing.

Sometimes, when the camera has not taken an image in a while, dark current will accumulate in the photodiodes that causes the first image in a stack to appear noisier (this phenomenon again depends on using synchronous/overlap triggering mode).  This noise will corrupt a max-intensity image.  Setting "Trim Z first" to 1 or 2 is usually sufficient to remove the noise (though, obviously, will eliminate any data in those planes as well).

Trimming in the Y direction is mostly used to simply crop excess pixels from the image to save space.

**Background Subraction**

In addition to a manually set "Fixed Value", there is an option to "Autodetect" the background for each channel.  In this case, the mode value of the second image in the z stack is used as the background value for that channel.


Deskew/Deconvolution/Saving
***************************
*These options dictate what processing should be done, and what should be saved.*

**Deconvolution**

If "Do Deconvolution" is checked and Iterations is greater than zero, deconvolution will be performed.  nApodize and nZblend directly control the corresponding parameters in cudaDeconv.

"Save MIPs" check boxes determine which axes will have maximum-intensity-projections generated.

The 16-bit / 32-bit dropdown menu controls the bit-depth of the resulting deconvolved files.

**Raw Deskewed**

If "Save Deskewed" is checked, the raw (non-deconvolved) deskewed files will be saved.  Note: for experiments acquired in galvo/piezo scanning mode (i.e. not in sample-scan), this section does nothing.

"Save MIPs" check boxes determine which axes will have maximum-intensity-projections generated.

The 16-bit / 32-bit dropdown menu controls the bit-depth of the resulting deconvolved files.

**Join MIPS into single hyperstack**

This option applies to both Deskewed and Deconvolved MIP folders, and combines all of the tiff files in each of those folders into a single multichannel/timelapse hyperstack that wil be recognized by ImageJ/Fiji.


Post-Processing
***************
*While many of these options are technically performed during processing by the cudaDeconv binary, they all fall into the category of things done to the image after deconvolution/deskewing has already been performed.*

**Cropping**

The "Crop Result" checkbox will crop the resulting deskewed/deconvolved image (in the X direction only).  "AutoCrop" will automatically select a crop region based on image feature content.  This is done by processing all channels from the first and last timepoints, and summing their max-intensity projections prior to heavy gaussian blurring.  That summed & blurred image is segmented and a bounding box is calculated that contains the features in the image.  The "Pad" setting adds additional pixels to both sides of the calculated bounding box.

Whether or not AutoCrop is chosen, the "Preview" button can be used to preview and evaluate the current settings in the processed image.  If the Preview button is clicked when the AutoCrop option is selected, the autodetected "Width" and "Shift" values will be appear in the "Manual" cropping settings to the right where they can be further tuned and previewed prior to processing.

**Rotate to coverslip**

Rotate and interpolate data so that the Z axis of the image volume is orthogonal to the coverslip (does nothing beyond what cudaDeconv does).

.. _Channel Registration:

**Channel Registration (experimental)**

When "Do Channel Registration" is checked, the deskewed/deconvolved data will be registered using the provided calibration folder, specified in the "Calibration" text field.  This calibration folder should contain at least one Z-stack, for each channel, of a fiducial marker that appears in all channels, such as tetraspeck beads.  The folder must also contain a Settings.txt file (simply acquiring more than one timepoint is an easy way to generate an appropriate folder).

The beads will be detected and fit to a 3D gaussian to generate a point cloud of XYZ locations.  The algorithm then limits the point cloud to beads that appear in all channels.  This point cloud can then be used to calculate the transformation required to register the various channels in dataset to the specified "Reference Channel" chosen in the dropdown menu.

*Modes:*
   * Least-squares point cloud registration:
      * Translation: simply corrects for translational shifts between channels
      * Rigid: correct for translation and rotation differences
      * Similarity: correct for translation, rotation, and scaling (magnifiation) differences.
      * Affine: corrects translation, rotation, scaling, and shearing
      * 2-step: performs affine registration in XY and rigid registraion in Z
   * Coherent Point Drift registration
      * These options use the coherent point drift algorithm (Myronenko 2010) instead of least-squares.  This can be a bit more robust with low SNR datasets, when the algorithm fails to correctly limit the fiducial point cloud to strictly one-to-one matching points.

Note: some of these modes may fail/crash.  Test with preview prior to processing.  Bug reports welcome!

**Bleach Correction**

Enables setting in cudaDeconv to normalize all timepoints to the intensity of the first timepoint, minimizing the appearance of photobleaching over the course of the timelapse, but altering the intensity values of the resulting deskewed/deconvolved images.

**Compress Raw Data**

After processing, compress the raw data using lbzip2 parallel compression.


Preview Button
--------------

The Preview button (Ctrl-P) is used to process and show the first timepoint (by default) of the dataset selected in the processing queue, allowing evaluation of the current settings prior to processing of the entire folder.  After clicking "Preview", a multidimensional image window will appear after a moment of processing.  This window has a number of features (some non-obvious):

* hovering over the image will show the coordinate and intensity value of the pixel under the mouse.
* use the Magnifying glass icon and up/down/left/right icon to zoom and pan, respectively.
* use the Z slider or the mouse wheel to select the Z plane to show
* use the C slider to change the currently displayed channel
* the min/max sliders adjust scaling of the image
* click on the colorbar to the right, or press the "C" key to cycle the colormap through some LUTs.
* Press the following keys for various projections.  To return to standard Z-scrolling mode, press the same key again.

    * M - Max intensity projection
    * N - Min intensity projection
    * B - Mean intensity projection
    * V - Standard Deviation intensity projection
    * , - Median intensity projection

To preview multiple timepoints, or something other than the first timepoint, use the time subset field, which accepts a comma seperated string of (zero-indexed) timepoints, or ranges with start-stop[-step] syntax.

For instance:

   * 0-2,9 - process the first three and 10th timepoints.
   * 1-5-2 - start-stop-step syntax, processes the 2nd, 4th, and 6th timepoints
   * 0,2-4,7-15-3 - combination of list, range, and range-with-step syntax



Process Button and Time/Channel Subset
--------------------------------------

The Preview button (Ctrl-P) is used to process and show the first timepoint (by default) allowing evaluation of the current settings prior to processing of the entire folder.

To process a subset of timepoints or channels, use the time subset and channel subset fields, which accept a comma seperated string of (zero-indexed) timepoints, or ranges with start-stop[-step] syntax.

For instance:

  * 0-2,9 - process the first three and 10th timepoints.
  * 1-5-2 - start-stop-step syntax, processes the 2nd, 4th, and 6th timepoints
  * 0,2-4,7-15-3 - combination of list, range, and range-with-step syntax



Config Tab
----------

Use bundled cudaDeconv Binary
*****************************

By default the program will use bundled cudaDeconv binaries, autoselecting based on the operating system.  Tested on OS X, Linux, and Windows 7/10.

cudaDeconv binary
*****************
Unselect the "Use bundled cudaDeconv binary" option to enable this field which will allow you to specify the path to a specific cudaDeconv binary.  Note: many of the features in LLSpy assume that the bundled binary is used.  However, an attempt has been made to accomodate any binary by detecting the available options in the help menu, and disabling any non-matching features from LLSpy.  However, this is still experimental, and may cause unexpected issues.

.. _OTF directory:

OTF directory and OTF auto-selection
************************************

Path to the folder that holds OTF and PSF files.

As a fallback, the program will look in this path for an otf file that is labeled [Wavelength]_otf.tif
For example: 488_otf.tif

Before using the default otf, the program will attempt to find an appropriate PSF/OTF file to use based on the date of acquisition of the experiment, the mask used (provided the mask has been entered into SPIMProject.ini, see below), and the wavelength.  Currently, files in the OTF directory must have the following format:

``[date]_[wave]_[psf-type][outerNA]-[innerNA].tif``

for example: ``20170103_488_totPSFmb0p5-0p42.tif`` or ``20170103_488_totPSFmb0p5-0p42_otf.tif``

If a matching PSF file is found that does not have an OTF file already generated, it will generate an OTF file and save it with the _otf.tif suffix.  This allows you to simply acquire a PSF file, and drop it in the PSF folder with the appropriate naming convention, and an OTF will automatically be generated when that PSF is used.

In order to select and OTF based on mask pattern, the mask must be in the Settings.txt file in the experiment.  The easiest way to do this is to add an "Annular Mask" section to the SPIMProject.ini file in the Lattice Scope software, and update the values each time you change the mask.  For instance:

.. code:: ini

  [Annular Mask]
  outerNA = 0.5
  innerNA = 0.42


Default Reg Calib
*****************

Not used at the moment.  Instead, use the "Calibration" field provided in the "Do Channel Registration" section of the of Post-Processing tab.


.. _Generate Camera Calibration File:

Generating Camera Calibration File
**********************************

The calibration algorithm assumes that you have aquired a series of 2-channel Zstacks (not actually a 3D stack: set Z galvo range and Z and Sample Piezo range to zero). The first channel should be "bright" (many photons hitting the chip) and even like a flatfield image (such as 488 laser sheet exciting FITC) and the second channel is a "dark" image (I use another wavelength channel with the laser off.  Collect two ~100-plane Z stacks for many different intensities (laser power) in the "bright channel": start at very low power (0.1% laser) and gradually acquire stacks at higher power.  Due to the exponential relationship of the residual electron effect, it's particularly important to get a lot of low-powered stacks: 1%, 2%, 3% etc... then after 10% you can begin to take bigger steps. (Of course, the exact laser powers will depend on the power and efficiency of your system.

Upon clicking the "Generate Camera Calibration File" button, select the path to the folder that contains all of the bright/dark images acquired above. By default, the program will look for an image called Dark_AVG.tif in the selected Image Folder, but the average projection image can also be manually selected.  Optionally, a standard deviation projection of the dark image stack (i.e. noise map) can be also provided in the same folder, named Dark_STD.tif, and it will be included in the calibration file.

Even with parallel processing, this process takes a while: about ~30 minutes for a 1024x512 ROI on a computer with a 4 core, 4 GHz processer (i7-6700K).  However, it should only need to be calculated once.  I have been using the same correction file for about a year, and it continues to be appropriate for my camera.

The output file will appear in the Image Folder.  Put it somewhere you will remember and enter the path on the Config Tab in the LLSpy GUI.

Reprocess folders that have already been processed
**************************************************

If left unchecked, LLSpy will skip over any folders that have already been processed (i.e. folders that already contain a ProcessingLog.txt file)

Save MIP Folder during "Reduce to Raw"
**************************************

The "Reduce to Raw" shortcut in the toolbar deletes any GPUdecon, Deskwed, Corrected, and MIP folders, restoring folder to state immediately after aquisition.  This option in the config tab alters the behavior of the "reduce" function to leave any MIP folders for easy preview in the future.

Warn when quitting with unprocessed items
*****************************************

By default, LLSpy will warn you if you have unprocessed items remaining in the queue.  Turn this option off here.

Preview Type
*****************************************

Choose between a standard single-plane viewer (with various projection modes), and the Spimagine 4D viewer.


Watch Directory (experimental)
******************************

These options designate a folder to watch and auto-process when a new LLS folder appears.

**Watch Modes**
   * *Server mode*: designate a folder to watch for incoming *finished* LLS folders (with Settings.txt) file.  When new folders are detected, they are added to the processing queue and the queue is started if not already in progress.
   * *Aquisition mode*: designed to be used on the aquisition computer.  Designate folder to watch for new LLS folders, and process new files as they arrive.  Similar to built in GPU processing tab in Lattice Scope software, but with the addition of all the corrections and parameter selection in the GUI.

Error reporting Opt Out
***********************

In order to improve the stability of LLSpy, crashes and uncaught exceptions/errors are collected and sent to sentry.io.  These bug reports are extremely helpful for improving the program.  No personal information is collected, and the full error-reporting logic may be inspected in :obj:`llspy.gui.exceptions`.  However, you may opt out of automatic error reporting with this checkbox.


Log Tab
-------
Any output from cudaDeconv or LLSpy will appear in this tab.  *Note:* a program log is also written to disk, the location of this file varies with OS.  On mac it is in the Application Support folder.  On windows, it is in the %APPDATA% folder.


Progress and Status Bar
-----------------------
During cudaDeconv processing, the current file number will appear in the status bar at the bottom of the window, and the percent progress is represented by the progress bar.  The timer countdown on the right provides an estimate of the time remaining for the current LLS directory (not for the entire queue).  If a folder is being monitored for new data, it will show up at the bottom right corner of the status bar.
