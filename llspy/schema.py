from voluptuous import (All, Any, Coerce, Lower, Strip, Length, Range,
						Schema, Required, PREVENT_EXTRA)
from voluptuous.humanize import validate_with_humanized_errors
from .util import dotdict
from . import config
import os

intbool = Schema(lambda x: int(bool(x)))
twotupIntRange = Schema(All((All(int, Range(0, 200)),), Length(min=2, max=2)))


def CTiterable(v):
	if isinstance(v, int):
		v = [v]
	try:
		iter(v)
	except TypeError:
		raise TypeError('Not an iterable object')
	if not all([(isinstance(i, int) and i >= 0) for i in v]):
		raise ValueError('All values in Channel/Time range must be integers >= 0')
	return v


def dirpath(v):
	if not os.path.isdir(str(v)):
		raise ValueError('Not a valid directory')
	return v


def filepath(v):
	if not os.path.isfile(str(v)):
		raise ValueError('Not a valid directory')
	return v


def intRange(m, n):
	return Schema(All(Coerce(int), Range(m, n)))


__defaults__ = {
	'bFlashCorrect'		: (False,         'do Flash residual correction'),
	'flashCorrectTarget': ('cpu',         '{"cpu", "cuda", "parallel"} for FlashCor'),
	'bMedianCorrect'	: (False,         'do Keller median filter'),
	'bSaveCorrected' 	: (False,         'save corrected images after processing'),
	'edgeTrim'			: (((0, 0),) * 3, 'num ZYX pix to trim off raw data before processing'),
	'nIters'			: (10,            'deconvolution iters'),
	'nApodize'			: (15,            'num pixels to soften edge with for decon'),
	'nZblend'			: (0,             'num top/bot Z sections to blend to reduce axial ringing'),
	'bRotate'			: (False,         'do Rotation to coverslip coordinates'),
	'rotate'			: (None,          'angle to use for rotation'),
	'bSaveDeskewedRaw'	: (False,         'whether to save raw deskewed'),
	'bSaveDecon'		: (True,          'whether to save decon stacks'),
	'MIP'				: ((0, 0, 1),     'whether to save XYZ decon MIPs'),
	'MIPraw'			: ((0, 0, 0),     'whether to save XYZ raw MIPs'),
	'bMergeMIPs'		: (True,          'do MIP merge into single file (decon)'),
	'bMergeMIPsraw' 	: (True,          'do MIP merge into single file (deskewed)'),
	'buint16'			: (True,          'save decon as unsigned int16'),
	'buint16raw'		: (True,          'save deskewed raw as unsigned int16'),
	'bBleachCor'		: (False,         'do photobleach correction'),
	'bDoRegistration'  	: (False,         'do channel registration'),
	'regRefWave'		: (488,           'reference wavelength when registering'),
	'regMode'			: ('2step',       'transformation mode when registering'),
	'regCalibDir'		: (None,          'directory with registration calibration data'),
	'mincount'			: (10,            'minimum number of beads expected in regCal data'),
	'bReprocess'		: (False,         'reprocess already-done data when processing'),
	'tRange'			: (None,          'time range to process (None means all)'),
	'cRange'			: (None,          'channel range to process (None means all)'),
	'otfDir'			: (config.__OTFPATH__,
											'directory to look in for PSFs/OTFs'),
	'camparamsPath'		: (config.__CAMPARAMS__,
											'file path to camera Parameters .tif'),
	'verbose'			: (0,             'verbosity level when processing {0,1,2}'),
	'cropMode' 			: ('none',        '{manual, auto, none} - auto-cropping based on image content'),
	'autoCropSigma'		: (2,             'gaussian blur sigma when autocropping'),
	'autoCropPad' 		: (50,            'number of extra pixels on edges when autocropping'),
	'width' 			: (0,             'final width when not autocropping (0 = full)'),
	'shift' 			: (0,             'crop shift when not autocropping'),
	'bAutoBackground' 	: (True,          'do automatic background detection'),
	'background'		: (90,            'background to subtract when not autobgrd'),
	'bCompress'			: (False,         'do compression of raw data after processing'),
	'compressionType'	: ('lbzip2',      'compression binary {lbzip2, bzip2, pbzip2, pigz, gzip}')
}

__validator__ = {
	'bFlashCorrect'		: Coerce(bool),
	'flashCorrectTarget': All(Coerce(str), Lower, Strip, Any('cpu', 'parallel', 'cuda'),
		msg='flashCorrectTarget must be {cpu, parallel, cuda}'),
	'bMedianCorrect'	: Coerce(bool),
	'bSaveCorrected'	: Coerce(bool),
	'edgeTrim'			: All((twotupIntRange,), Length(min=3, max=3),
		msg='edgeTrim argument must be a 3tuple of 2tuples of ints from 0-200'),
	'nIters'			: All(int, Range(0, 30),
		msg='Number of Deconvolution iterations must be int between 0-30'),
	'nApodize'			: All(int, Range(0, 50),
		msg='Number of apodize pixels must be int between 0-50'),
	'nZblend'			: All(int, Range(0, 30),
		msg='Number of Z slices to blend must be int between 0-30'),
	'bRotate'			: Coerce(bool),
	'rotate'			: Any(None, All(Coerce(float), Range(-180, 180),
		msg='Rotation angle must be float between -180 and 180')),
	'bSaveDeskewedRaw'	: Coerce(bool),
	'bSaveDecon'		: Coerce(bool),
	'MIP'				: All((intbool,), Length(min=3, max=3)),
	'MIPraw'			: All((intbool,), Length(min=3, max=3)),
	'bMergeMIPs'		: Coerce(bool),
	'bMergeMIPsraw' 	: Coerce(bool),
	'buint16'			: Coerce(bool),
	'buint16raw'		: Coerce(bool),
	'bBleachCor'		: Coerce(bool),
	'bDoRegistration'  	: Coerce(bool),
	'regRefWave'		: intRange(300, 1000),
	'regMode'			: All(Coerce(str), Lower, Strip,
		Any('translation', 'translate', 'affine', 'rigid', 'similarity', '2step',
			'cpd_affine', 'cpd_rigid', 'cpd_similarity', 'cpd_2step'),
		msg='Registration mode must be {translation, rigid, similarity, affine, 2step, '
			'cpd_affine, cpd_rigid, cpd_similarity, cpd_2step}'),
	'regCalibDir'		: Any(None, dirpath),
	'mincount'			: All(int, Range(0, 500),
		msg='mincount (min number of beads to detect) must be between 0-500'),
	'bReprocess'		: Coerce(bool),
	'tRange'			: Any(None, CTiterable,
		msg='tRange must be int or iterable of integers >= 0'),
	'cRange'			: Any(None, CTiterable,
		msg='cRange must be int or iterable of integers >= 0'),
	'otfDir'			: Any(None, dirpath),
	'camparamsPath'		: Any(None, filepath),
	'verbose'			: Any(0, 1, 2,
		msg='verbosity level must be 0, 1, or 2'),
	'cropMode' 			: All(Coerce(str), Lower, Strip, Any('none', 'auto', 'manual')),
	'autoCropSigma'		: All(Coerce(float), Range(0, 15)),
	'autoCropPad' 		: intRange(0, 200),
	'width' 			: intRange(0, 3000),
	'shift' 			: intRange(-1500, 1500),
	'bAutoBackground' 	: Coerce(bool),
	'background'		: Any([intRange(0, 10000)], intRange(0, 10000)),
	'bCompress'			: Coerce(bool),
	'compressionType'	: Any('lbzip2', 'bzip2', 'pbzip2', 'pigz', 'gzip',
		msg='Currently allowed compression types: {lbzip2, bzip2, pbzip2, pigz, gzip}')
}


__schema__ = Schema({
	Required(k, default=__defaults__[k][0]): v for k, v in __validator__.items()},
	extra=PREVENT_EXTRA)

__localSchema__ = __schema__.extend({
	'otfs' 		: [Any(None, filepath)],
	'drdata' 	: All(Coerce(float), Range(0, 0.5),
		msg='Data pixel size (drdata) must be float between 0.04 - 0.5'),
	'dzdata' 	: All(Coerce(float), Range(0, 50),
		msg='Data Z step size (dzdata) must be float between 0 - 50'),
	'dzFinal' 	: All(Coerce(float), Range(0, 50),
		msg='Data Z step size (dzdata) must be float between 0 - 50'),
	'wavelength': [All(Coerce(int), Range(300, 1000),
		msg='wavelength must be int between 300 - 1000')],
	'deskew'	: All(Coerce(float), Range(-180, 180),
		msg='deskew angle must be float between -180 and 180')
})
__localSchema__.extra = PREVENT_EXTRA


def localParams(*args, **kwargs):
	""" returns a validated dict of processing parameters
	with defaults filled in when not supplied, that ALSO
	contains parameters to a specific LLSdir instance.

	returned by llspy.core.llsdir.localParams()
	"""

	if len(args) == 1 and isinstance(args[0], dict):
		kwargs = args[0]
	S = validate_with_humanized_errors(kwargs, __localSchema__)
	return dotdict(S)


def procParams(*args, **kwargs):
	""" returns a validated dict of processing parameters
	with defaults filled in when not supplied.

	>>> P = procParams() # get default parameters
	>>> P = procParams(nIters=7, tRange=range(0,10))
	# check validitity of parameter name
	>>> 'regMode' in procParams()

	"""
	if len(args) == 1 and isinstance(args[0], dict):
		kwargs = args[0]
	S = validate_with_humanized_errors(kwargs, __schema__)
	return dotdict(S)


def printOptions():
	print()
	row_format = "{:>20}\t{:<27}{:<35}"
	print(row_format.format('Name', 'Default', 'Description'))
	print(row_format.format('----', '-------', '-----------'))
	toolong = []
	for k, v in __defaults__.items():
		if len(str(v[0])) < 28:
			print(row_format.format(k, str(v[0]), v[1]))
		else:
			toolong.append((k, v))
	if len(toolong):
		for k, v in toolong:
			print()
			print(row_format.format(k, str(v[0]), ''))
			print(row_format.format('', '', v[1]))



# cudaDeconvOptions = {
# 	'drdata': ,
# 	'dzdata': ,
# 	'drpsf': ,
# 	'dzpsf': ,
# 	'wavelength': ,
# 	'wiener': ,
# 	'background': ,
# 	'napodize': ,
# 	'nzblend': ,
# 	'NA': ,
# 	'RL': ,
# 	'deskew': ,
# 	'width': ,
# 	'shift': ,
# 	'rotate': ,
# 	'saveDeskewedRaw': ,
# 	'crop': ,
# 	'MIP': ,
# 	'rMIP': ,
# 	'uint16': ,
# 	'bleachCorrection': ,
# 	'input-dir': ,
# 	'otf-file': ,
# 	'filename-pattern': ,
# 	'DoNotAdjustResForFFT': ,
#  }