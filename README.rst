##########################################
LLSpy: Lattice Light-sheet Data Processing
##########################################

.. image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
    :target: https://opensource.org/licenses/BSD-3-Clause

.. image:: https://img.shields.io/badge/python-2.7%2C%203.5%2C%203.6-blue.svg

|

.. image:: http://cbmf.hms.harvard.edu/wp-content/uploads/2015/07/logo-horizontal-small.png
    :target: http://cbmf.hms.harvard.edu/lattice-light-sheet/


*Copyright (c) 2017 Talley Lambert, Harvard Medical School, all rights reserved.*

|

LLSpy is a graphical and command line interface for lattice light sheet post-processing. It extends the cudaDeconv binary created in the Betzig lab at Janelia Research Campus, and adds additional features that auto-detect experimental parameters (minimizing user input), perform image corrections and manipulations, and facilitate file handling.

Full documentation available at http://llspy.readthedocs.io/


.. image:: http://cbmf.hms.harvard.edu/wp-content/uploads/2017/09/gui.png
    :height: 825 px
    :width: 615 px
    :scale: 100%
    :alt: alternate text
    :align: right


Installation
============


**Note**: *The cudaDeconv binary and associated code is owned by HHMI.  It is not included in this package and must be installed seperately.  See instructions below*



1. Install `CUDA <https://developer.nvidia.com/cuda-downloads>`_ (tested on CUDA 8.0)
2. Install `FFTW <http://www.fftw.org/>`_. (not necessary on Windows)

    **OS X**

    This is easiest using the `Homebrew <https://brew.sh/>`_ package manager for OS X:

    .. code::

        $ /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
        $ brew update
        $ brew install fftw

    **LINUX**

    .. code::

        $ sudo apt-get install fftw-dev


3. Install `Anaconda <https://www.anaconda.com/download/>`_ (python 3.6 is preferred, but 2.7 also works)
4. Launch a ``terminal`` window (OS X, Linux), or ``Anaconda Prompt`` (Windows)
5. *Optional but recommended*: Create a virtual environment (this makes it easier to uninstall cleanly and prevents conflicts with any other python environments)

    **WINDOWS**

    .. code::

        > conda create -y -n llsenv
        > activate llsenv

    **OS X & LINUX**


    .. code::

        $ conda create -y -n llsenv
        $ source activate llsenv

6. Install LLSpy

.. code::

    > conda install -y -c talley -c conda-forge llspy


7. Install Janelia binaries and libraries.  The binaries will (hopefully) be included in the LLS Dropbox share.  Use the ``lls install`` command to install the libraries and binaries to the virtual environment.

.. code::

    > lls install /path/to/lls_dropbox/llspy_extra

8. Each time you use the program, you will need to activate the virtual environment (if you created one in step 4).  The main command line interface is ``lls``, and the gui can be launched with ``lls gui``

.. code:: bash

    # Launch Anaconda Prompt and type...
    > activate llsenv  # Windows
    > source activate llsenv  # OS X or Linux

    # show the command line interface help menu
    > lls -h
    # process a dataset
    > lls decon /path/to/dataset
    # or launch the gui
    > lls gui


See complete usage notes in the `documentation <http://llspy.readthedocs.io/>`_.



Features of LLSpy
=================

* graphical user interface with persistent/saveable processing settings
* command line interface for remote/server usage (coming)
* preview processed image to verify settings prior to processing full experiment
* *Pre-processing corrections*:
* correct "residual electron" issue on Flash4.0 when using overlap synchronous mode.  Includes CUDA and parallel CPU processing as well as GUI for generation of calibration file.
* apply selective median filter to particularly noisy pixels
* trim image edges prior to deskewing (helps with CMOS edge row artifacts)
* auto-detect background
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
    * Server mode: designate a folder to watch for incoming *finished* LLS folders (with Settings.txt file).  When new folders are detected, they are added to the processing queue and the queue is started if not already in progress.
    * Aquisition mode: designed to be used on the aquisition computer.  Designate folder to watch for new LLS folders, and process new files as they arrive.  Similar to built in GPU processing tab in Lattice Scope software, but with the addition of all the corrections and parameter selection in the GUI.
* easily return LLS folder to original (pre-processed) state
* compress and decompress folders and subfolders with lbzip2 (not working on windows)
* concatenate two experiments - renaming files with updated relative timestamps and stack numbers
* rename files acquired in script-editor mode with ``Iter_`` in the name to match standard naming with positions (work in progress)
* cross-platform: includes precompiled binaries and shared libraries that should work on all systems.

To Do
=====

* give better feedback when hitting preview button
* allow cancel after hitting preview button
* ask Martin about sampler_t nearest for volume render


Bug Reports, etc...
===================

`Contact Talley <mailto:talley.lambert@gmail.com>`_

Please include the following in any bug reports:

- Operating system version
- GPU model
- CUDA version (type ``nvcc --version`` at command line prompt)
- Python version (type ``python --version`` at command line prompt, with ``llsenv`` conda environment active if applicable)


openCL troubleshooting on Linux
===============================

..code::bash

    # activate the conda environment that has pyopencl/gputools installed
    $ source activate <clenv>

    # use this to quickly test platform detection
    $ python -c "import pyopencl; pyopencl.get_platforms()"

    # the error i got the most was:
    $ python -c "import pyopencl; pyopencl.get_platforms()"
    Traceback (most recent call last):
      File "<string>", line 1, in <module>
      File "/opt/anaconda3/envs/testcl/lib/python3.6/site-packages/pyopencl/cffi_cl.py", line 672, in get_platforms
        _handle_error(_lib.get_platforms(platforms.ptr, platforms.size))
      File "/opt/anaconda3/envs/testcl/lib/python3.6/site-packages/pyopencl/cffi_cl.py", line 645, in _handle_error
        raise e
    pyopencl.cffi_cl.LogicError: clGetPlatformIDs failed: <unknown error -1001>

    # check the library loading path of pyopencl/_cffi.abi3.so
    $ ldd $CONDA_PREFIX/lib/python3.6/site-packages/pyopencl/_cffi.abi3.so
    # look specifically for the following line
        libOpenCL.so.1 => <CONDA_PREFIX>/lib/python3.6/site-packages/pyopencl/./../../../libOpenCL.so.1 (0x00007fdc13e50000)
        libOpenCL.so.1 => /usr/local/cuda/lib64/libOpenCL.so.1 (0x00007f3671ad7000)
        libOpenCL.so.1 => /usr/lib/x86_64-linux-gnu/libOpenCL.so.1 (0x00007f09c45c5000)

in my case, i think it was an openCL version mismatch... by deleting/moving/renaming the files at
<CONDA_PREFIX>/lib/python3.6/site-packages/pyopencl/./../../../libOpenCL.so.1
and
/usr/local/cuda/lib64/libOpenCL.so.1
it eventually fell back on
/usr/lib/x86_64-linux-gnu/libOpenCL.so.1
which DID work
Note, when it did finally work, I also no longer saw an error when running clinfo about library version

the null platform behavior at the end of clinfo should show some successes