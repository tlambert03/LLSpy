TODO:
	* *Program crashes if config not set properly!*
  	* replace warnings.warn with logging.warn
	* handle dzPSF and drPSF
	* cudaDeconv generates MIPs folder even when no mips are created
	* implement cudaDeconv arguments as voluptuous schema
	* calculated psf for deconvolution?
	* add button to open folder so that it can be done via ssh -X
	* break up schema into logical subsections (i.e. deconParams)
	* nT parameters are incorrectly detected on scripted folders with Iter_0
	* make timer countdown during file processing (and correct after each file)
	* progress indicator on camera correction
	* No Settings.txt folder detected, now shows up during camera correction... remove
	* can't yet abort while doing camera correction
	* and... if someone deletes or moves a folder while it is being processed... it will hang
	* probably best to pull log widget out of mainGUI

	* add note about gsettings to readme:

	    - sudo mv ~/anaconda3/bin/gsettings ~/anaconda3/bin/gsettingsBAK



User options:

	process subset of channels/timepoints

	Corrections
	-	Flash Correction
	-	Median Correction
	-	Trim edges (XYZ)
	-	Background (fixed/autodetec/rollingball?)
	-	Flat field correction?
	-	Bleedthrough?

	OTFs
		OTF directory
		Default OTFs
		naming string convention for OTF?

	Utilities:
		compress
		decompress
		reset
		concatenate experiments
		"rename iter"
		get info
		rotate
		crop to features
		register
		convert to HDF5?

	Settings:
		compression tool
		binary paths
		GPU/CPU
		overwrite existing?

	If no settings file: manually input parameters?