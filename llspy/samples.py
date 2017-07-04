try:
	import pathlib as plib
	plib.Path().expanduser()
except (ImportError, AttributeError):
	import pathlib2 as plib
except (ImportError, AttributeError):
	raise ImportError('no pathlib detected. For python2: pip install pathlib2')


basic = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_basic_samp/'
bidirectional = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_bidirectional/'
bleedthrough = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_bleedthrough_samp/'
multipoint = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_multipoint_samp/'
notLLS = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/'
stickypix = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_stickypix_samp/stickypix_data/'
objectivescan = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_objectivescan_samp/'
camparams = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_stickypix_samp/FlashParams.tif'

PSFpath = plib.Path('/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_PSFs/archive')