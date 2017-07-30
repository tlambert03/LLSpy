from llspy import plib
from llspy.util.util import dotdict

basic = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_basic_samp/'
mitosis = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_mitosis_samp/'
bidirectional = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_bidirectional/'
bleedthrough = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_bleedthrough_samp/'
multipoint = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_multipoint_samp/'
notLLS = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/'
stickypix = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_stickypix_samp/stickypix_data/'
objectivescan = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_objectivescan_samp/'
camparams = '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_stickypix_samp/FlashParams.tif'
settext = 'Users/talley/DropboxHMS/Python/LLSpy2/tests/testdata/example_Settings.txt'

PSFpath = plib.Path('/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_PSFs/archive')

filename = 'cell5_ch0_stack0000_488nm_0000000msec_0020931273msecAbs.tif'

reg = dotdict({
	'ex1': dotdict({
		'tspeck': '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_registration_samp/reg_ex1/tspeck/',
		'data': '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_registration_samp/reg_ex1/data/',
	}),
	'ex2': dotdict({
		'tspeck': '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_registration_samp/reg_ex2/tspeck/',
		'data': '/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_registration_samp/reg_ex2/data/',
	}),
})
