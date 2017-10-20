
Introduction to Channel Registration
====================================

Because almost all multi-channel images have some degree of channel misregistration (particularly on multi-camera setups), LLSpy includes a standard fiducial-based channel registration procedure.  A calibration dataset is acquired with a sample of broad-spectrum diffraction limited objects (such as TetraSpeck beads).  The objects are then detected and localized by fitting to a 3D gaussian model, yielding a set of 3D coordinates (X, Y, Z) for each object, for each channel.  (In LLSpy, a single wavelength set of coordinates is instantiated by the :class:`fiducialreg.FiducialCloud` class and a set of FiducialClouds is instantiated by the :class:`fiducialreg.CloudSet` class).  A transformation can then be calculated that maps (or 'registers') a set of coordinates for one channel (the "moving" set) onto a set of coordinates for another channel (the 'reference' set).  Once calculated, that transformation matrix can then be used to register other data acquired in those two channels. (This of course assumes that nothing has changed in the microscope that would alter the spatial relationship between the images in those two channels... which is not always a safe assumption).

Contraints can be enforced when calculating these transformation matrices, allowing varying degreese of freedom or "flexibility" when mapping one coordinate set onto another.

* The simplest transformation is a 3D **translation**: which just states the number of pixels to shift the image of the "moving" channel in X, Y, and Z, relative to the reference channel.

In increasing degrees-of-freedom:

* a **rigid** transform allows for translation and rotation between two channels
* a **similarity** transform additional allows for scaling/magnification differences between the two channels
* a full **affine** transform additionally allows for shearing of one image with respect to the other.  When performing channel registraion, it is often beneficial to chose the "least flexible" transformation that "gets the job done", as increasing degrees of freedom can sometimes lead dramatically bad registrations.

CPD-Registration
****************

The standard registration modes mentioned above require a one-to-one relationship between fidicual markers in each channel.  LLSpy will therefore attempt to discard any coordinate points that do not have a corresponding point in both datasets being registered.  Sometimes, that automated filtering fails, in which case the calculated registration will usually be nonsense.
LLSpy also includes (experimental) support for `Coherent Point Drift <http://ieeexplore.ieee.org/document/5432191/>`_-based transformation estimation, using a slightly modified version of the `pycpd library <https://github.com/siavashk/pycpd>`_.  For registration modes with 'CPD' prepended to the name, a one-to-one relationship between fiducial markers across channels will **not** be enforced.  Please verify that your chosen registration mode correctly registers the fiducial dataset before applying it to experimental data, as described below in `A Typical Workflow`_.


LLSpy Registration File
-----------------------

In LLSpy, you first create a Registration File (LLSpy.reg file) from a fiducial dataset, choosing the channels you may later want to use as the reference channel.  Multiple transformations (e.g. translation, rigid, similarity, affine...) will be calculated that map all of the wavelengths in represented in the calibration data, to each of the reference wavelengths selected.  The output file is in JSON format, an example is shown below:

.. code-block:: json

	{
	  "tforms": [
	    {
	      "mode": "translation",
	      "reference": 488,
	      "moving": 560,
	      "inworld": true,
	      "tform": [
	         [  1.0000000000,  0.0000000000,  0.0000000000,  0.0771111160],
	         [  0.0000000000,  1.0000000000,  0.0000000000,  0.0138356744],
	         [  0.0000000000,  0.0000000000,  1.0000000000,  0.5431871957],
	         [  0.0000000000,  0.0000000000,  0.0000000000,  1.0000000000]
	      ]
	    },
	    {
	      "mode": "rigid",
	      "reference": 488,
	      "moving": 560,
	      "inworld": true,
	      "tform": [
	         [  0.9999998846, -0.0004796165, -0.0000280755,  0.0771111160],
	         [  0.0004796557,  0.9999988858,  0.0014136213,  0.0138356744],
	         [  0.0000273975, -0.0014136346,  0.9999990004,  0.5431871957],
	         [  0.0000000000,  0.0000000000,  0.0000000000,  1.0000000000]
	      ]
	    },
	  ]
	}

Using this template, you may also generate your own registration transformations using other software, and use them within LLSPy.  Minimally, the registration file must have a top level dict (``{ }``) with a key ``tforms``.  The value of ``tforms`` must be a list of dict, where each dict in the list represents one transformation matrix.  Each ``tform`` dict in the list must minimally have the following keys:

* **mode:** the type of registration performed.  currently, must be one of the following:
 		``translation``, ``translate``, ``affine``, ``rigid``, ``similarity``, ``2step``, ``cpd_affine``, ``cpd_rigid``, ``cpd_similarity``, ``cpd_2step``
* **reference:** the reference wavelength
* **moving:** the wavelength to be registered
* **tform:** the (forward) transformation matrix that maps the moving dataset onto the reference dataset.  Must be a 4x4 matrix where the last row is [0,0,0,1].

A Typical Workflow
------------------

To perform registration in LLSpy, one will typically generate a registration file from a fiducial dataset, then apply the transformations in that file to experimental data.  That file can be used until it is determined that the transformations no longer represent the channel-relationship in the data (the frequency with which the calibration must be performed will vary dramatically across systems and must be determined for your system.)  To generate a registration file in the LLSpy gui, use the **Registration** tab, click the **load** button next to the Fidicual Data field, and select a folder containing multi-channel fiducial markers, such as tetraspeck beads. (Note: this folder must also include a settings.txt file.  On the Lattice Scope software, the easiest way to generate a settings.txt file is simply to acquire more than one "timepoint").  Then select the **Ref Channels** to which you want to register, and click the **Generate Registration File** button.  You will be prompted to select a destination for the file (a file will also be saved in your OS-specific *application directory*, such as ``%APPDATA%\LLSpy\regfiles`` on windows).  The registration file will be automatically loaded into the **Registration File** field below, where you can then "test" out a given transformation **mode** and **Ref Channel**  by registering the fiducal dataset itself, using the **Register Fiducial Data** button.  Depending on the degree of channel misalignment, is very likely that some of the transformation modes will *not* work, so you should confirm which mode(s) worked in this window, before applying to experimental data.  Finally, the registration file can be loaded in the main **Process** tab under the **Post-Processing - Channel Registration** section, by clicking the **Use RegFile** button, and selecting the desired **Ref Wave** and transformation **Mode**.  If the **Do Channel Registration** checkbox is selected, that registration will then be applied to your deconvolved/deskewed data.  Registered tiffs will have ``_REG`` appeneded to their filenames.
