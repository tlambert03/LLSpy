.. LLSpy documentation master file, created by
   sphinx-quickstart on Tue Oct  3 07:29:21 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to LLSpy's documentation!
=================================

LLSpy: Lattice light-sheet post-processing utility
--------------------------------------------------

.. |copy|   unicode:: U+000A9

Copyright |copy| 2017 Talley Lambert, Harvard Medical School.

.. image:: http://cbmf.hms.harvard.edu/wp-content/uploads/2015/07/logo-horizontal-small.png
    :target: http://cbmf.hms.harvard.edu/lattice-light-sheet/


*LLSpy is a python library to facilitate lattice light sheet data processing. It extends the cudaDeconv binary created in the Betzig lab at Janelia Research Campus, adding features that auto-detect experimental parameters from the data folder structure and metadata (minimizing user input), auto-choose OTFs, perform image corrections and manipulations, and facilitate file handling.*


.. toctree::
   :maxdepth: 3
   :caption: Table of Contents:

   main
   gui
   cli
   api
   Channel Registration <registration>
   SLM Pattern Generator <slm>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
