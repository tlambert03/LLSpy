
*Object oriented python processing of Lattice Light Sheet Data*

Installation
------------

Install `Anaconda`_.
LLSpy is designed to be compatible with both python 2 and python 3, so chose whichever version you prefer.

.. _Anaconda: https://www.continuum.io/downloads

Download LLSpy and set up an environment with the appropriate dependencies:

.. code:: bash

    $ git clone git@github.com:tlambert03/llspy2.git
    $ cd llspy2
    $ conda env create --file environment.yml
    $ source activate llsenv
    $ ipython


Usage
-----

.. code:: python

    import llspy as LLS

    path_to_folder = '~/lls_experiment_folder/'

    # main LLSdirectory class to organize data and functions processing a typical experiment
    Experiment = LLS.LLSdir(path_to_folder)
    # extracts lots of useful info from the settings file and the filenames
    print(Experiment)
    # stuff parsed just from the settings.txt file is here
    print(Experiment.settings)

    # wrapper for binary file
    cudabin = LLS.CUDAbin('/usr/local/bin/cudaDeconv')
    # parses help text to get a useful dict of available options and descriptions
    print(cudabin.options)

    # binary class can be used directly
    cudabin.run('path_with_tifs', 'filepattern', 'path_to_otf')

    # or can be called from a LLSdir instance
    Experiment.autoprocess()

    # where autoprocess options are:
    def autoprocess(self, correct=False, median=True, width='auto', pad=50,
        shift=0, background=None, trange=None, crange=None, iters=10,
        MIP=(0, 0, 1), rMIP=None, uint16=True, rotate=False,
        bleachCorrection=False, saveDeskewedRaw=True, quiet=False, verbose=False,
        compress=False, mipmerge=True, binary=CUDAbin(), **kwargs):




To Do:
------
    - progress bar for cudaDeconv processes
    - batch processing
    - pretty-print info on directory
