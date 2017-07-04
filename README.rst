LLSpy Module Repository
========================


Usage
-----

.. code:: python
	import llspy as LLS

	path_to_folder = '~/LLS_directory/'
	# main LLSdirectory class to organize data and functions processing a typical experiment
	Experiment = LLS.LLSdir(path_to_folder)
	# extracts lots of useful info from the settings file and the filenames
	print(Experiment)
	# stuff parsed just from the settings.txt file is here
	print(Experiment.settings)

	# wrapper for binary file
	cudabin = LLS.cudabin.CUDAbin('/usr/local/bin/cudaDeconv')
	# parses help text to get a useful dict of available options and descriptions
	print(cudabin.options)
	cudabin.describe_option('--wiener')
	# binary class can be used directly
	cudabin.run('path_with_tifs', 'filepattern', 'path_to_otf')

	# or can be called from a LLSdir instance
	Experiment.process()  # work in progress...
	# most pertinent settings for cudaDeconv here
	Experiment._get_cudaDeconv_options()
