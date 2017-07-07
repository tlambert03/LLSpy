from __future__ import print_function, division

from llspy.image import deskew

import tifffile as tf
import numpy as np
from skimage.filters import gaussian, threshold_li
from scipy.stats import mode

def imcontentbounds(im, sigma=2):
	"""Get image content bounding box via gaussian filter and threshold."""
	# get rid of the first two planes in case of high dark noise
	if im.ndim == 3:
		im = np.squeeze(np.max(im[2:], 0))
	im = im.astype(np.float)
	fullwidth = im.shape[-1]
	# from scipy.ndimage.filters import median_filter
	# mm = median_filter(b.astype(float),3)
	mm = im
	imgaus = gaussian(mm, sigma=sigma)
	mask = imgaus > threshold_li(imgaus)
	linesum = np.sum(mask, 0)
	abovethresh = np.where(linesum > 0)[0]
	right = abovethresh[-1]
	left = abovethresh[0]
	return [left, right, fullwidth]


def feature_width(E, background=None, pad=50, sigma=2):
	"""automated detection of post-deskew image content width.

	the width can be used during deskewing to crop the final image to
	reasonable bounds
	"""

	# first deskew just first and last timepoints of each channel
	P = E.parameters
	# first and last timepoint
	raw_stacks = [tf.imread(f) for f in E.get_files(t=(0, P.nt - 1))]
	raw_stacks = [sub_background(f, background) for f in raw_stacks]
	if P.samplescan:
		deskewed_stacks = [deskew(s, P.dz, P.dx, P.angle) for s in raw_stacks]
	else:
		deskewed_stacks = raw_stacks

	# then get minimum bounding box of features
	bounds = np.array([imcontentbounds(d, sigma) for d in deskewed_stacks])
	topmax = np.max(bounds[:, 1])
	topmin = np.min(bounds[:, 0])
	deskewedWidth = bounds[0, 2]
	width = int(topmax - topmin + pad)
	middle = np.floor(topmax - width / 2)
	offset = int(np.floor(middle - deskewedWidth / 2))
	# print "width: %d,   offset: %d" % (width, offset)
	return {'width': width, 'offset': offset, 'deskewed_nx': deskewedWidth}


def detect_background(im):
	if im.ndim == 3:
		im = im[2]  # pick the third plane... avoid noise in first plane on lattice
	return mode(im.flatten())[0][0]


def sub_background(im, background=None):
	if background is None:
		background = detect_background(im)
	out = im.astype(np.float) - background
	out[out < 0] = 0
	return out
