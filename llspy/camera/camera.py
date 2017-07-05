from llspy.config import config

import os
import warnings
import numpy as np
# note: numba.cuda MUST be imported before gputools, otherwise segfault 11
from numba import jit, cuda
from tifffile import imread, imsave
import math

default_params = config.__CAMPARAMS__


# #THIS ONE WORKS BEST SO FAR
@jit(nopython=True, nogil=True, cache=True)
def calc_correction(stack, a, b, offset):
	res = np.empty_like(stack)
	for i in range(stack.shape[0]):
		for j in range(stack.shape[1]):
			for k in range(stack.shape[2]):
				if i == 0:
					d = stack[i, j, k] - offset[j, k]
					res[i, j, k] = d if d > 0 else 0
				else:
					cor = a[j, k] * (1 - math.exp(-b[j, k] *
							(stack[i - 1, j, k] - offset[j, k])))
					d = stack[i, j, k] - offset[j, k] - 0.88 * cor
					res[i, j, k] = d if d > 0 else 0
	return res


# FIXME: almost correct... but still returning some "blocky" output
# ... I think it's due to the the stack[z - 1, y, x] not finding the right value
# ... also, speed is likely not as fast as @ jit for this problem
@cuda.jit
def cuda_correct(stack, a, b):
	z, y, x = cuda.grid(3)
	if z < stack.shape[0] and y < stack.shape[1] and x < stack.shape[2]:
		if z == 0:
			stack[z, y, x] = stack[z, y, x] if stack[z, y, x] > 0 else 0
		else:
			cor = a[z, y, x] * (1 - math.exp(-b[z, y, x] * (stack[z - 1, y, x])))
			d = stack[z, y, x] - 0.88 * cor
			stack[z, y, x] = d if d > 0 else 0


# FIXME: this shouldn't go here
def savetiff(arr, outpath, dx=1, dz=1, dt=1, unit='micron'):
	"""sample wrapper for tifffile.imsave imagej=True."""
	# array must be in TZCYX order
	md = {
		'unit': unit,
		'spacing': dz,
		'finterval': dt,
		'hyperstack': 'true',
		'mode': 'composite',
		'loop': 'true',
	}
	bigT = True if arr.nbytes > 3758096384 else False  # > 3.5GB make a bigTiff
	with warnings.catch_warnings():
		warnings.simplefilter("ignore")
		imsave(outpath, arr, bigtiff=bigT, imagej=True,
						resolution=(1 / dx, 1 / dx), metadata=md)


def correctInsensitivePixels(
	stack, backgroundValue, medianRange=3, verbose=False, withMean=False):
	"""correct bad pixels on sCMOS camera.
	based on MATLAB code by Philipp J. Keller,
	HHMI/Janelia Research Campus, 2011-2014

	"""
	from scipy.ndimage.filters import median_filter

	with warnings.catch_warnings():
		warnings.simplefilter("ignore")

		deviationProjection = np.std(stack, 0, ddof=1)
		deviationProjectionMedianFiltered = median_filter(deviationProjection,
			medianRange, mode='constant')
		deviationDistances = np.abs(np.subtract(deviationProjection,
			deviationProjectionMedianFiltered))
		deviationDistances[deviationDistances == np.inf] = 0
		deviationThreshold = determineThreshold(sorted(deviationDistances.flatten()))

		deviationMatrix = deviationDistances > deviationThreshold

		if withMean:
			meanProjection = np.mean(stack, 0) - backgroundValue
			meanProjectionMedianFiltered = median_filter(meanProjection, medianRange)
			meanDistances = np.abs(np.divide(np.subtract(
				meanProjection, meanProjectionMedianFiltered),
				meanProjectionMedianFiltered))
			meanDistances[meanDistances == np.inf] = 0
			meanThreshold = determineThreshold(sorted(meanDistances.flatten()))

			meanMatrix = meanDistances > meanThreshold

			pixelMatrix = deviationMatrix | meanMatrix
			pixelCorrection = [deviationDistances,
				deviationThreshold, meanDistances, meanThreshold]
		else:
			pixelMatrix = deviationMatrix
			pixelCorrection = [deviationDistances, deviationThreshold]

		if verbose:
			pixpercent = 100 * np.sum(
				pixelMatrix.flatten()) / float(len(pixelMatrix.flatten()))
			print('Bad pixels detected: {} {:0.2f}'.format(
				np.sum(pixelMatrix.flatten()), pixpercent))

		dt = stack.dtype
		out = np.zeros(stack.shape, dt)
		# apply pixelMatrix to correct insensitive pixels
		for z in range(stack.shape[0]):
			frame = np.asarray(stack[z], 'Float32')
			filteredFrame = median_filter(frame, medianRange)
			frame[pixelMatrix == 1] = filteredFrame[pixelMatrix == 1]
			out[z] = np.asarray(frame, dt)

		return out, pixelCorrection


def determineThreshold(array, maxSamples=50000):
	array = np.array(array)
	elements = len(array)

	if elements > maxSamples:  # subsample
		step = elements / maxSamples
		array = array[0::step]
		elements = len(array)

	connectingline = np.linspace(array[0], array[-1], elements)
	distances = np.abs(array - connectingline)
	position = np.argmax(distances)

	threshold = array[position]
	if np.isnan(threshold):
		threshold = 0
	return threshold


# TODO: should subclass np.ndarray instead
class CameraROI(object):
	"""class to define camera roi"""
	def __init__(self, arr):
		self.arr = np.array(arr)
		if not len(arr) == 4:
			raise ValueError('camera roi must be a list of 4 values')
		self.left = arr[0]
		self.top = arr[1]
		self.right = arr[2]
		self.bottom = arr[3]
		self.width = abs(self.right - self.left) + 1
		self.height = abs(self.bottom - self.top) + 1
		self.shape = (self.width, self.height)

	def __repr__(self):
		return str(self.arr)

	def __str__(self):
		return str(self.arr)

	def __add__(self, other):
		if isinstance(other, CameraROI):
			return np.array(self.arr) + np.array(other.arr)
		elif isinstance(other, (list, np.ndarray, tuple)):
			return np.array(self.arr) + np.array(other)
		else:
			raise TypeError("unsupported operand type for +: 'CameraROI' and '{}"
				.format(type(other)))

	def __sub__(self, other):
		if isinstance(other, CameraROI):
			return np.array(self.arr) - np.array(other.arr)
		elif isinstance(other, (list, np.ndarray, tuple)):
			return np.array(self.arr) - np.array(other)
		else:
			raise TypeError("unsupported operand type for -: 'CameraROI' and '{}"
				.format(type(other)))


class CameraParameters(object):
	"""Class to store parameters for camera correction

	Filename: path to tif file that stores the camera correction parameters,
		first plane = param A
		second plane = param B
		third plane = dark image (offset map)
		#TODO: fourth plane = variance map
	"""
	def __init__(self, fname=default_params, data=None, roi=[513, 769, 1536, 1280]):
		if data is None and fname is None:
			raise ValueError('Must provide either filename or data array')
		if data is not None:
			self.data = data.astype(np.float32)
			self.path = None
			self.basename = None
		else:
			if not os.path.isfile(fname):
				raise IOError("No such file: {}".format(fname))
			self.path = fname
			self.basename = os.path.basename(fname)
			# TODO: ignore warnings from tifffile
			self.data = imread(fname).astype(np.float64)

		self.roi = CameraROI(roi)
		self.shape = self.data.shape
		if not self.shape[0] >= 3:
			raise ValueError("Camera parameter file must have at least "
				"3 planes. {} has only {}".format(fname, self.shape[0]))
		if not self.roi.width == self.shape[1]:
			raise ValueError("Tiff file provided does not have the same width "
				"({}) as the proivded roi ({})".format(
					self.shape[1], self.roi.width))
		if not self.roi.height == self.shape[2]:
			raise ValueError("Tiff file provided does not have the same height "
				"({}) as the proivded roi ({})".format(
					self.shape[2], self.roi.height))
		self.width = self.roi.width
		self.height = self.roi.height
		self.a = self.data[0]
		self.b = self.data[1]
		self.offset = self.data[2]

	def get_subroi(self, subroi):
		diffroi = subroi - self.roi
		# make sure the Parameter ROI contains the data ROI
		if (any([i < 0 for i in diffroi[0:1]]) or
			any([i > 0 for i in diffroi[2:3]])):
			raise ValueError(
				'ROI for correction file does not encompass data ROI')
		# either Labview or the camera is doing
		# something weird with the ROI... or I am calculating the required ROI
		# alignment wrong... this is the hack I empirically came up with
		vshift = self.roi.left + self.roi.right - subroi.left - subroi.right
		# it appears that the camera never shifts the roi horizontally...
		hshift = 0
		subP = self.data[:, diffroi[0] + vshift:diffroi[2] + vshift,
						diffroi[1] + hshift:diffroi[3] + hshift]
		return CameraParameters(data=subP, roi=subroi.arr)

	def correct_stacks(self, stacks, dampening=0.88, median=True, target='cpu'):
		"""interleave stacks and apply correction for "sticky" Flash pixels.

		Expects a list of 3D np.ndarrays ordered in order of acquisition:
			e.g. [stack_ch0, stack_ch1, stack_ch2, ...]

		Returns a corrected list of np.ndarrays of the same
		shape and length as the input
		"""
		if len({S.shape for S in stacks}) > 1:
			raise ValueError('All stacks in list must have the same shape')
		if not all([isinstance(S, np.ndarray) for S in stacks]):
			raise ValueError('All stacks in list must be of type: np.ndarray')

		# interleave stacks into single 3D so that they are in the order:
		#  ch0_XYt0, ch1_XYt0, chN_XYt0, ch0_XYt1, ch1_XYt1, ...
		nz, ny, nx = stacks[0].shape
		numStacks = len(stacks)
		typ = stacks[0].dtype
		interleaved = np.stack(stacks, 1).reshape((-1, ny, nx)).astype(np.float64)

		if target == 'cpu':
			# JIT VERSION
			interleaved = calc_correction(interleaved, self.a, self.b, self.offset)
		elif target == 'gpu':
			# CUDA VERSION ... doesn't really gain much
			iZ = interleaved.shape[0]
			tpb = (64, 4, 4)
			bpgZ = math.ceil(interleaved.shape[0] / tpb[0])
			bpgY = math.ceil(interleaved.shape[1] / tpb[1])
			bpgX = math.ceil(interleaved.shape[2] / tpb[2])
			bpg = (bpgZ, bpgY, bpgX)
			interleaved -= np.tile(self.offset, (iZ, 1, 1))
			cuda_correct[bpg, tpb](interleaved, np.tile(
				self.a, (iZ, 1, 1)), np.tile(self.b, (iZ, 1, 1)))
		elif target == 'numpy':
			# NUMPY VERSION
			interleaved = np.subtract(interleaved, self.offset)
			correction = self.a * (1 - np.exp(-self.b * interleaved[:-1, :, :]))
			interleaved[1:, :, :] -= dampening * correction
			interleaved[interleaved < 0] = 0
		else:
			raise ValueError(
				'unrecognized value for target parameter: {}'.format(target))

		# interleaved = np.subtract(interleaved, self.offset)
		# correction = self.a * (1 - np.exp(-self.b * interleaved[:-1, :, :]))
		# interleaved[1:, :, :] -= dampening * correction
		# interleaved[interleaved < 0] = 0

		if median:
			interleaved, pixCorrection = correctInsensitivePixels(interleaved, 0)

		interleaved = interleaved.astype(typ)
		deinterleaved = [s for s in np.split(interleaved, interleaved.shape[0])]
		deinterleaved = [np.concatenate(deinterleaved[q::numStacks])
						for q in range(numStacks)]

		return deinterleaved


if __name__=='__main__':

	from llspy import llsfiles, samples

	paramfile = samples.camparams  # path to the calibration file
	llsdir = samples.stickypix  # path to the raw data

	E = llsfiles.LLSdir(llsdir)  # special class for my data...
	# you'll need to work around this to generate a list of filenames you want to correct

	# get the master parameters TIF file and then crop it according to the
	# roi used for the raw data set... if raw data is the same as the calibration
	# you can use corrector = camparams
	camparams = CameraParameters(paramfile)
	corrector = camparams.get_subroi(CameraROI(E.settings.camera.roi))

	# this is the list you need to make
	stacks = [imread(str(t)) for t in E.raw if 'stack0001' in str(t)]

	niters = 5

	import time
	start = time.time()
	for _ in range(niters):
		d1 = corrector.correct_stacks(stacks, median=False, target='cpu')
	end = time.time()
	print("JitCPU Time: " + str((end - start) / niters))

	start = time.time()
	for _ in range(niters):
		d2 = corrector.correct_stacks(stacks, median=False, target='numpy')
	end = time.time()
	print("NumpyCPU Time: " + str((end - start) / niters))
	print("Equal? = " + str(np.allclose(d1[0], d2[0])))
	print("Equal? = " + str(np.allclose(d1[1], d2[1])))
	print("Equal? = " + str(np.allclose(d1[2], d2[2])))

	start = time.time()
	for _ in range(niters):
		d3 = corrector.correct_stacks(stacks, median=False, target='gpu')
	end = time.time()
	print("GPU Time: " + str((end - start) / niters))
	print("Equal? = " + str(np.allclose(d3[0], d2[0])))
	print("Equal? = " + str(np.allclose(d3[1], d2[1])))
	print("Equal? = " + str(np.allclose(d3[2], d2[2])))

	# batchFlashCorrect(llsdir,camparams)
