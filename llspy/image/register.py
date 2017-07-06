from __future__ import print_function, division
from tifffile import imread, imshow
import numpy as np
from scipy import ndimage
from scipy import stats
import scipy
import os
try:
	import SimpleITK as sitk
	__sitkImported = True
except Exception:
	print("could not import SimpleITK module!")
	__sitkImported = False

try:
	import cv2
	__cv2Imported = True
except Exception:
	print("could not import opencv module!")
	__cv2Imported = False


def calcTranslationRegistration(moving, fixed):
	"""calculate the translation shift between two images"""

	fixedImage = sitk.ReadImage(fixed)
	movingImage = sitk.ReadImage(moving)
	parameterMap = sitk.GetDefaultParameterMap('translation')

	elastixImageFilter = sitk.ElastixImageFilter()
	elastixImageFilter.SetFixedImage(fixedImage)
	elastixImageFilter.SetMovingImage(movingImage)
	elastixImageFilter.SetParameterMap(parameterMap)
	elastixImageFilter.Execute()

	resultImage = elastixImageFilter.GetResultImage()
	transformParameterMap = elastixImageFilter.GetTransformParameterMap()

	return (transformParameterMap, resultImage)


def applyTranslationShift(ims, Tparams):
	"""Apply translation shift to image"""

	if not isinstance(ims, list):
		ims = [ims]

	transformixImageFilter = sitk.TransformixImageFilter()
	transformixImageFilter.SetTransformParameterMap(Tparams)

	for filename in ims:
		transformixImageFilter.SetMovingImage(sitk.ReadImage(filename))
		transformixImageFilter.Execute()
		fname = os.path.basename(filename)
		transformixImageFilter.GetResultImage()
		sitk.WriteImage(transformixImageFilter.GetResultImage(), "result_" + fname)


def find_local_maxima(img, threshold=100, neighborhood=3):
	"""finds coordinates of local maxima in an image

	Accepts: 2D numpy array

	Returns: set of tuples {(x,y),(x,y)...} corresponding to local max position
	"""
	data_max = ndimage.filters.maximum_filter(img, neighborhood)
	maxima = (img == data_max)
	data_min = ndimage.filters.minimum_filter(img, neighborhood)
	diff = ((data_max - data_min) > threshold)
	maxima[diff == 0] = 0
	labeled, num_objects = ndimage.label(maxima)
	slices = ndimage.find_objects(labeled)
	x, y = [], []
	for dy, dx in slices:
		x_center = (dx.start + dx.stop - 1) / 2
		x.append(x_center)
		y_center = (dy.start + dy.stop - 1) / 2
		y.append(y_center)
	return set(zip(x, y))


def autodetect_peaks(ims, minparticles=4, threshrange=range(200, 520, 20)):
	"""intelligently find coordinates of local maxima in an image
	by searching a range of threshold parameters to find_local_maxima

	Accepts: variable number of input 2D arrays

	Returns:
	a tuple of sets of tuples ({(x,y),..},{(x,y),..},..) corresponding to
	local maxima in each image provided.  If nimages in == 1, returns a set

	"""
	threshes = []
	for im in ims:
		npeaks = []
		for t in (threshrange):
			npeaks.append(len(find_local_maxima(im, t)))
		mod = stats.mode([p for p in npeaks if p > minparticles])[0]
		thrsindx = np.argmax(npeaks[::-1] == mod)
		threshes.append(threshrange[thrsindx - 1])
	peaks = [find_local_maxima(ims[i], threshes[i]) for i in range(len(threshes))]
	if len(threshes) > 1:
		return tuple(peaks)
	else:
		return peaks[0]

def normxcorr2(b,a):
	c = scipy.signal.convolve2d(a, np.flipud(np.fliplr(b)))
	a = scipy.signal.convolve2d(a**2, np.ones_like(b))
	b = np.sum(b.flatten()**2)
	return c/sqrt(a*b)



if __name__ == '__main__':
	img1 = imread('/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_registration_samp/janelia_reg_example/deskewed/488_beadfield_0,6umStep_deskewed.tif')
	img2 = imread('/Users/talley/DropboxHMS/CBMF/lattice_sample_data/lls_registration_samp/janelia_reg_example/deskewed/560_beadfield_0,6umStep_uncorrected_deskewed.tif')

	# crop top and bottom 5 planes to remove partial PSFs
	# check that the images are the same size

	# get img shape
	zslices, h, w = img1.shape

	# background subtraction by rolling ball?
	background = 10
	img1[img1 < background] = background
	img1bg = img1 - background
	img2[img2 < background] = background
	img2bg = img2 - background
	# sum images along Z axis
	img1sum = np.sum(img1bg, 0)
	img2sum = np.sum(img2bg, 0)

	# Auto Detect maximum threshold to detect alignment beads
	# get bead peak coordinates in the process
	peaks1, peaks2 = autodetect_peaks((img1sum, img2sum))

	# Rough align images using cross correlation
	temp = img2sum.astype(np.float32)
	crop = 20
	temp = temp[crop:-crop, crop:-crop]
	result = cv2.matchTemplate(img1sum.astype(np.float32), temp, cv2.TM_CCORR_NORMED)
	min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
	xshift = crop - max_loc[0]
	yshift = crop - max_loc[1]
	print(xshift)
	print(yshift)
