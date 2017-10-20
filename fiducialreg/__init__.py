from .fiducialreg import (RegistrationError, GaussFitter3D, FiducialCloud,
	CloudSet, log_filter,
	infer_affine, infer_rigid, infer_similarity, infer_2step, affineXF)
from . import imref
from . import imwarp


__version__ = '0.1.0'
__all__ = ('RegistrationError', 'CloudSet', 'GaussFitter3D', 'FiducialCloud',
	'RegFile')
