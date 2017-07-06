import numpy as np
import math


def deskew(rawdata, dz=0.3, dx=0.105, angle=31.5, filler=0):
	try:
		import sys
		import os
		# silence gputools error if config file is missing
		#sys.stdout = open(os.devnull, "w")
		# the PyPI gputools repo doesn't yet have the required affine params
		sys.path.insert(0, '/Users/talley/Dropbox (HMS)/Python/repos/gputools/')
		import gputools
		#sys.stdout = sys.__stdout__
	except ImportError:
		#sys.stdout = sys.__stdout__
		print("could not import gputools, can't deskew")

	deskewFactor = np.cos(angle * np.pi / 180) * dz / dx
	T = np.array([[1, 0, deskewFactor, 0],
				[0, 1, 0, 0],
				[0, 0, 1, 0],
				[0, 0, 0, 1]])
	(nz, ny, nx) = rawdata.shape
	# Francois' method:
	# nxOut = math.ceil((nz - 1) * deskewFactor) + nx
	nxOut = np.int(np.floor((nz - 1) * dz *
			abs(np.cos(angle * np.pi / 180)) / dx) + nx)
	# +1 to pad left side with 1 column of filler pixels
	# otherwise, edge pixel values are smeared across the image
	paddedData = np.ones((nz, ny, nxOut), rawdata.dtype) * filler
	paddedData[..., :nx] = rawdata
	out = gputools.transforms.affine(
		paddedData, T, interpolation="linear", mode="wrap")
	return out # return is np.float32
