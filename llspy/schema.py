from .util import dotdict
from .exceptions import ParametersError
from voluptuous import (All, Any, Coerce, Lower, Strip, Length, Range,
                        Schema, Required, PREVENT_EXTRA, MultipleInvalid)
from voluptuous.humanize import validate_with_humanized_errors

import os

intbool = Schema(lambda x: int(bool(x)))
twotupIntRange = Schema(All((All(int, Range(0, 999)),), Length(min=2, max=2)))


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


def smartbool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        if v.lower() in ['false', 'no', 'none', '', 'f']:
            return False
        elif v.lower() in ['true', 'yes', 't', 'y']:
            return True
        elif v.isdigit():
            return float(v) != 0
        else:
            raise ValueError('Could not coerce string to bool: {}'.format(v))
    if isinstance(v, (int, float, complex)):
        return v != 0
    else:
        raise TypeError('Could not coerce value of type {} to bool'.format(type(v)))


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
    'correctFlash'      : (False,         'do Flash residual correction'),
    'moveCorrected'     : (True,          'move processed corrected files to original LLSdir'),
    'flashCorrectTarget': ('cpu',         '{"cpu", "cuda", "parallel"} for FlashCor'),
    'medianFilter'      : (False,         'do Keller median filter'),
    'keepCorrected'     : (False,         'save corrected images after processing'),
    'trimZ'             : ((0, 0),        'num Z pix to trim off raw data before processing'),
    'trimY'             : ((0, 0),        'num Y pix to trim off raw data before processing'),
    'trimX'             : ((0, 0),        'num X pix to trim off raw data before processing'),
    'nIters'            : (10,            'deconvolution iters'),
    'napodize'          : (15,            'num pixels to soften edge with for decon'),
    'nzblend'           : (0,             'num top/bot Z sections to blend to reduce axial ringing'),
    'bRotate'           : (False,         'do Rotation to coverslip coordinates'),
    'rotate'            : (None,          'angle to use for rotation'),
    'rotateRev'         : (False,         'reverse sign of rotation angle'),
    'saveDeskewedRaw'   : (False,         'whether to save raw deskewed'),
    'saveDecon'         : (True,          'whether to save decon stacks'),
    'MIP'               : ((False, False, True),     'whether to save XYZ decon MIPs'),
    'rMIP'              : ((False, False, False),     'whether to save XYZ raw MIPs'),
    'mergeMIPs'         : (True,          'do MIP merge into single file (decon)'),
    'mergeMIPsraw'      : (True,          'do MIP merge into single file (deskewed)'),
    'uint16'            : (True,          'save decon as unsigned int16'),
    'uint16raw'         : (True,          'save deskewed raw as unsigned int16'),
    'bleachCorrection'  : (False,         'do photobleach correction'),
    'doReg'             : (False,         'do channel registration'),
    'deleteUnregistered': (False,         'delete unregistered files when doing registration'),
    'regRefWave'        : (488,           'reference wavelength when registering'),
    'regMode'           : ('2step',       'transformation mode when registering'),
    'regCalibPath'       : (None,          'directory with registration calibration data'),
    'mincount'          : (10,            'minimum number of beads expected in regCal data'),
    'reprocess'         : (False,         'reprocess already-done data when processing'),
    'tRange'            : (None,          'time range to process (None means all)'),
    'cRange'            : (None,          'channel range to process (None means all)'),
    'otfDir'            : (None,          'directory to look in for PSFs/OTFs'),
    'camparamsPath'     : (None,          'file path to camera Parameters .tif'),
    'verbose'           : (0,             'verbosity level when processing {0,1,2}'),
    'cropMode'          : ('none',        '{manual, auto, none} - auto-cropping based on image content'),
    'autoCropSigma'     : (2,             'gaussian blur sigma when autocropping'),
    'width'             : (0,             'final width when not autocropping (0 = full)'),
    'shift'             : (0,             'crop shift when not autocropping'),
    'cropPad'           : (50,            'additional pixels to keep when autocropping'),
    'background'        : (-1,            'background to subtract. -1 = autodetect'),
    'compressRaw'       : (False,         'do compression of raw data after processing'),
    'compressionType'   : ('lbzip2',      'compression binary {lbzip2, bzip2, pbzip2, pigz, gzip}'),
    'writeLog'          : (True,          'write settings to processinglog.txt'),
    'padval'            : (0,             'value to pad image with when deskewing'),
    'FlatStart'         : (False,         'start decon from a flat image guess using the median image value'),
    'dupRevStack'       : (False,         'duplicate reversed stack prior to decon to reduce Z ringing'),
    'lzw'               : (False,         'use LZW tiff compression'),
    # 'bRollingBall': self.backgroundRollingRadio.


}

__validator__ = {
    'correctFlash'      : smartbool,
    'moveCorrected'     : smartbool,
    'flashCorrectTarget': All(Coerce(str), Lower, Strip, Any('cpu', 'parallel', 'cuda'),
                              msg='flashCorrectTarget must be {cpu, parallel, cuda}'),
    'medianFilter'      : smartbool,
    'keepCorrected'     : smartbool,
    'trimZ'             : All(twotupIntRange,
                              msg='trimZ argument must be a 2tuples of ints from 0-999'),
    'trimY'             : All(twotupIntRange,
                              msg='trimY argument must be a 2tuples of ints from 0-999'),
    'trimX'             : All(twotupIntRange,
                              msg='trimX argument must be a 2tuples of ints from 0-999'),
    'nIters'            : All(Coerce(int), Range(0, 30),
                              msg='Number of Deconvolution iterations must be int between 0-30'),
    'napodize'          : All(Coerce(int), Range(0, 50),
                              msg='Number of apodize pixels must be int between 0-50'),
    'nzblend'           : All(Coerce(int), Range(0, 30),
                              msg='Number of Z slices to blend must be int between 0-30'),
    'bRotate'           : smartbool,
    'rotate'            : Any(None, All(Coerce(float), Range(-180, 180),
                              msg='Rotation angle must be float between -180 and 180')),
    'rotateRev'         : smartbool,
    'saveDeskewedRaw'   : smartbool,
    'saveDecon'         : smartbool,
    'MIP'               : All((intbool,), Length(min=3, max=3)),
    'rMIP'              : All((intbool,), Length(min=3, max=3)),
    'mergeMIPs'         : smartbool,
    'mergeMIPsraw'      : smartbool,
    'uint16'            : smartbool,
    'uint16raw'         : smartbool,
    'bleachCorrection'  : smartbool,
    'doReg'             : smartbool,
    'deleteUnregistered': smartbool,
    'regRefWave'        : Any(0, intRange(300, 1000)),
    'regMode'           : All(Coerce(str), Lower, Strip,
                              Any('none', Any('translation', 'translate', 'affine', 'rigid', 'similarity', '2step',
                                  'cpd_affine', 'cpd_rigid', 'cpd_similarity', 'cpd_2step')),
                              msg='Registration mode must be one of {translation, rigid, similarity, affine, 2step, '
                              'cpd_affine, cpd_rigid, cpd_similarity, cpd_2step}'),
    'regCalibPath'       : Any(None, dirpath, filepath,
                               msg='Unable to find Registration Calibration path.  Check filepath'),
    'mincount'          : All(Coerce(int), Range(0, 500),
                              msg='mincount (min number of beads to detect) must be between 0-500'),
    'reprocess'         : smartbool,
    'tRange'            : Any(None, CTiterable,
                              msg='tRange must be int or iterable of integers >= 0'),
    'cRange'            : Any(None, CTiterable,
                              msg='cRange must be int or iterable of integers >= 0'),
    'otfDir'            : Any(None, '', dirpath,
                              msg='Unable to find OTF path. Check filepath in config'),
    'camparamsPath'     : Any(None, filepath,
                              msg='Unable to find Camera Paramaters path.  Check filepath in config'),
    'verbose'           : Any(0, 1, 2,
                              msg='verbosity level must be 0, 1, or 2'),
    'cropMode'          : All(Coerce(str), Lower, Strip, Any('none', 'auto', 'manual')),
    'autoCropSigma'     : All(Coerce(float), Range(0, 15)),
    'width'             : intRange(0, 3000),
    'shift'             : intRange(-1500, 1500),
    'cropPad'           : intRange(0, 500),
    'background'        : Any(intRange(-1, 20000), [intRange(0, 20000)]),
    'compressRaw'       : smartbool,
    'compressionType'   : Any('lbzip2', 'bzip2', 'pbzip2', 'pigz', 'gzip',
                              msg='Currently allowed compression types: {lbzip2, bzip2, pbzip2, pigz, gzip}'),
    'writeLog'          : smartbool,
    'padval'            : intRange(0, 9999),
    'FlatStart'         : smartbool,
    'dupRevStack'       : smartbool,
    'lzw'               : smartbool,
}


__schema__ = Schema({
    Required(k, default=__defaults__[k][0]): v for k, v in __validator__.items()},
    extra=PREVENT_EXTRA)


__localSchema__ = __schema__.extend({
    'otfs'      : [Any(None, filepath)],
    'drdata'    : All(Coerce(float), Range(0, 0.5),
                      msg='Data pixel size (drdata) must be float between 0.04 - 0.5'),
    'dzdata'    : All(Coerce(float), Range(0, 50),
                      msg='Data Z step size (dzdata) must be float between 0 - 50'),
    'dzFinal'   : All(Coerce(float), Range(0, 50),
                      msg='Data Z step size (dzdata) must be float between 0 - 50'),
    'wavelength': [All(Coerce(int), Range(300, 1000),
                       msg='wavelength must be int between 300 - 1000')],
    'deskew'    : All(Coerce(float), Range(-180, 180),
                      msg='deskew angle must be float between -180 and 180')
})
__localSchema__.extra = PREVENT_EXTRA


def localParams(*args, **kwargs):
    """ returns a validated dict of processing parameters
    with defaults filled in when not supplied, that ALSO
    contains parameters to a specific LLSdir instance.

    returned by llspy.llsdir.localParams()
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
    # accept a single dict as well as expanded options
    if len(args) == 1 and isinstance(args[0], dict):
        kwargs = args[0]

    S = validate_with_humanized_errors(kwargs, __schema__)
    if S['nIters'] > 0 and S['otfDir'] is None:
        raise ParametersError('oftDir cannot be type None with nIters > 0')
    return dotdict(S)


def validateItems(**kwargs):
    for k in kwargs.keys():
        if k not in __validator__:
            print("ERROR! got unrecognized key: {}".format(k))
            return 0
    S = Schema({k: v for k, v in __validator__.items()}, extra=PREVENT_EXTRA)
    return validate_with_humanized_errors(kwargs, S)


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
