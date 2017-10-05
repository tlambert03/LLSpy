.. _api:

Developer Interface
===================

.. module:: llspy.llsdir

This part of the documentation covers the interfaces of LLSpy that one might use in
development or interactive sessions.  This page is a work in progress:  there is much
more undocumented functionality in the source code.


Main Functions
--------------

Processing routines can be called directly with a path to the LLS experiment directory.

.. autofunction:: preview
.. autofunction:: process


Main Classes
------------

Most routines in LLSpy begin with the instantiation of an :class:`LLSdir <LLSdir>` object.
This class is also instantiated by the :obj:`preview` and :obj:`process` functions

LLS directory
*************

.. autoclass:: LLSdir
   :members:

cudaDeconv wrapper
******************

.. autoclass:: CUDAbin
  :members:

\*Settings.txt parser
*********************

.. module:: llspy.settingstxt

.. autoclass:: LLSsettings
  :members:


Wrapped CUDA functions
----------------------

.. module:: llspy.libcudawrapper

.. autofunction:: deskewGPU(im, dz=0.5, dr=0.102, angle=31.5, width=0, shift=0)
.. autofunction:: affineGPU(im, tmat)
.. autofunction:: quickDecon(im, otfpath, savedeskew=False, **kwargs)
.. autofunction:: RL_init
.. autofunction:: RL_decon
.. autofunction:: rotateGPU(im, angle=32.5, xzRatio=0.4253, reverse=False)
.. autofunction:: camcor(imstack, camparams)

Exceptions
----------

.. autoexception:: llspy.llsdir.LLSpyError
.. autoexception:: llspy.cudabinwrapper.CUDAbinException

.. _Schema list:

Schema
------

Many functions such as the :obj:`preview` and :obj:`process` functions accept keyword
arguments that determine processing options.  These are all validated using the schema
in :obj:`llspy.schema`.  Options include:

.. include:: schema.rst

