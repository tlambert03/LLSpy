.. _cli:

**********************
Command Line Interface
**********************

*In addition to the QT-based graphical user interface, LLSpy includes a command line interface (CLI).*

If the program has been installed using ``conda install -c talley -c conda-forge llspy``, or by using setuptools (i.e. running ``pip install .`` in the top level llspy directory, where setup.py resides) then an executable will be created that can be triggered by typing ``lls`` at the command prompt.  Alternatively, the CLI can be directly executed by running ``python llspy/bin/llspy_cli.py`` at the command prompt.  (For this documentation, it is assumed that the program was installed using ``conda install`` and run with ``lls``).

.. code:: bash

  $ lls --help
  Usage: lls [OPTIONS] COMMAND [ARGS]...

    LLSpy

    This is the command line interface for the LLSpy library, to facilitate
    processing of lattice light sheet data using cudaDeconv and other tools.

  Options:
    --version          Show the version and exit.
    -c, --config PATH  Config file to use instead of the system config.
    -h, --help         Show this message and exit.

  Commands:
    camera    Camera correction calibration
    compress  Compression & decompression of LLSdir
    config    Manipulate the system configuration for LLSpy
    decon     Deskew and deconvolve data in LLSDIR.
    deskew    Deskewing only (no decon) of LLS data
    gui       Launch the Graphical User Interface.
    info      Get info on LLSDIR.
    reg       Channel registration


You can configure the program either by providing a configuration .ini in the command using the ``--config`` flag, or by setting the system configuration using the ``llspy config`` command.  Minimally, you will want to establish the OTF directory by typing:

.. code:: bash

  $ lls config --set otfDir /path/to/OTFs/

To get a full list of keys available for configuration, type:

.. code:: bash

  $ lls config --info

To print the current system configuration, type:

.. code:: bash

  $ lls config --print

**Note**: System configuration values will be superceeded by key-value pairs included in ``config.ini`` files provided at the command prompt with ``--config``, and all configuration values will be superceeded by those privided directly using option flags in the decon command.

You can use ``--help`` to get more information on any specific subcommand.  Many are still under development.  The bulk of the program functionality resides in the ``decon`` subcommand.

.. code:: bash

  $ lls decon --help
  Usage: lls decon [OPTIONS] LLSDIR

    Deskew and deconvolve data in LLSDIR.

  Options:
    -c, --config PATH              Overwrite defaults with values in specified
                                   file.
    --otfDir DIRECTORY             Directory with otfs. OTFs should be named
                                   (e.g.): 488_otf.tif
    -b, --background INT           Background to subtract. -1 = autodetect.
                                   [default: -1]
    -i, --iters [INT: 0-30]        Number of RL-deconvolution iterations
                                   [default: 10]
    -R, --rotate                   rotate image to coverslip coordinates after
                                   deconvolution  [default: False]
    -S, --saveDeskewed             Save raw deskwed files, in addition to
                                   deconvolved.  [default: False]
    --cropPad INT                  additional edge pixels to keep when
                                   autocropping  [default: 50]
    -w, --width [INT: 0-3000]      Width of image after deskewing. 0 = full
                                   frame.[default: autocrop based on image
                                   content]
    -s, --shift [INT: -1500-1500]  Shift center when cropping  [default: 0]
    -m, --rMIP <BOOL BOOL BOOL>    Save max-intensity projection after
                                   deskewing along x, y, or z axis.  Takes 3
                                   binary numbers separated by spaces.
                                   [default: False, False, False]
    -M, --MIP <BOOL BOOL BOOL>     Save max-intensity projection after
                                   deconvolution along x, y, or z axis. Takes 3
                                   binary numbers separated by spaces  [default:
                                   False, False, True]
    --mergemips / --sepmips        Combine MIP files into single hyperstack (or
                                   not).  [default: True]
    --uint16 / --uint32            Save results as 16 (default) or 32- bit
    -p, --bleachCorrect            Perform bleach correction on timelapse data
                                   [default: False]
    --trimX <LEFT RIGHT>           Number of X pixels to trim off raw data
                                   before processing  [default: 0, 0]
    --trimY <TOP BOT>              Number of Y pixels to trim off raw data
                                   before processing  [default: 0, 0]
    --trimZ <FIRST LAST>           Number of Z pixels to trim off raw data
                                   before processing  [default: 0, 0]
    -f, --correctFlash             Correct Flash pixels before processing.
                                   [default: False]
    -F, --medianFilter             Correct raw data with selective median
                                   filter. Note: this occurs after flash
                                   correction (if requested).  [default: False]
    --keepCorrected                Process even if the folder already has a
                                   processingLog JSON file, (otherwise skip)
    -z, --compress                 Compress raw files after processing
                                   [default: False]
    -r, --reprocess                Process even if the folder already has a
                                   processingLog JSON file, (otherwise skip)
    --batch                        batch process folder: Recurse through all
                                   subfolders with a Settings.txt file
    --yes / --no                   autorespond to prompts
    -h, --help                     Show this message and exit.
