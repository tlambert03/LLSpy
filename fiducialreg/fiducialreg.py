#!/usr/bin/env python
# -*- coding: utf-8 -*-
# fiducialreg.py
#
# Copyright (c) 2017, Talley LAmbert
# Copyright (c) 2008-2016, The President and Fellows of Harvard College
# Produced at the Cell Biology Microscopy Facility, HMS
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * Neither the name of the copyright holders nor the names of any
#   contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""Generate transformation matrices from arrays of fiducial markers for
image registration.

:Author:
  `Talley Lambert <http://www.talleylambert.com>`_

:Organization:
  Cell Biology Microscopy Facility, Harvard Medical School

:Version: 2017.07.11

Requirements
------------
* `Scipy <https://www.scipy.org>`_
* `Numpy <http://www.numpy.org>`_
* `Matplotlib 1.5 <http://www.matplotlib.org>`_ (optional for plotting)
* `Tifffile 2016.04.13 <http://www.lfd.uci.edu/~gohlke/>`_ (optional for reading)

Revisions
---------
2017.07.11

Notes
-----

Acknowledgements
----------------
*   David Baddeley for gaussian fitting from python-microscopy
*   Andriy Myronenko for CPD algorithm
*   Siavash Khallaghi for python CPD implementation: pycpd

References
----------
(1) Point-Set Registration: Coherent Point Drift.  Andriy Mryonenko & Xubo Song
	https://arxiv.org/abs/0905.2635

Examples
--------
>>> from fiducialreg import FiducialCloud
>>> arrays = [arr1, arr2, arr3].  # three channels of fiducial marker stacks
>>> R = FiducialCloud(arrays, labels=[488, 560, 640])
>>> 560_to_488_rigid = R.get_tform_by_label(560, 488, mode='rigid')
>>> print(560_to_488_rigid)

# 560_to_488_rigid can then be used to transform a stack from 560 channel
# to a stack from the 488 channel...
>>> out = affine(im560, 560_to_488_rigid)
"""

from scipy import ndimage, optimize, stats
from os import path as osp
import itertools
import numpy as np
import logging
import json
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
np.seterr(divide='ignore', invalid='ignore')


# TODO: try seperable gaussian filter instead for speed
def log_filter(img, xysigma=1, zsigma=2.5, mask=None):
	# sigma that works for 2 or 3 dimensional img
	sigma = [zsigma, xysigma, xysigma][-img.ndim:]
	# LOG filter image
	filtered_img = -ndimage.gaussian_laplace(img.astype('f'), sigma)
	# eliminate negative pixels
	filtered_img *= (filtered_img > 0)
	if mask is not None:
		filtered_img *= mask
	return filtered_img


def bead_centroids(img, labeled, nlabels):
	# get center of mass of each object
	return [ndimage.center_of_mass(img, labeled, l) for l in range(1, nlabels + 1)]


def get_thresh(im, mincount=10, steps=100):
	"""intelligently find coordinates of local maxima in an image
	by searching a range of threshold parameters to find_local_maxima

	Accepts: variable number of input 2D arrays

	Returns:
	a tuple of sets of tuples ({(x,y),..},{(x,y),..},..) corresponding to
	local maxima in each image provided.  If nimages in == 1, returns a set

	"""
	if im.ndim == 3:
		im = im.max(0)
	threshrange = np.linspace(im.min(), im.max(), steps)
	object_count = [ndimage.label(im > t)[1] for t in threshrange]
	object_count = np.array(object_count)
	modecount = stats.mode(object_count[(object_count > mincount)], axis=None)[0][0]
	logging.debug('Threshold detected: {}'.format(threshrange[np.argmax(object_count == modecount)]))
	return threshrange[np.argmax(object_count == modecount)], modecount


def mad(arr, axis=None, method='median'):
	""" Median/Mean Absolute Deviation: a "Robust" version of standard deviation.
	Indices variabililty of the sample.
	https://en.wikipedia.org/wiki/Median_absolute_deviation
	"""
	if method == 'median':
		return np.median(np.abs(arr - np.median(arr, axis)), axis)
	elif method == 'mean':
		return np.mean(np.abs(arr - np.mean(arr, axis)), axis)
	else:
		raise ValueError('Unrecognized option for method: {}'.format(method))


def get_closest_points(pc1, pc2):
	"""returns the distance and index of the closest matching point in pc2
	for each point in pc1.

	len(nn) == len(pc1)

	can be used to eliminate points in pc2 that don't have a partner in pc1
	"""
	pc1 = pc1.T
	pc2 = pc2.T
	d = [((pc2 - point)**2).sum(axis=1) for point in pc1]
	nn = [(np.min(p), np.argmin(p)) for p in d]
	return nn


def get_matching_points(pc1, pc2, method=None):
	""" return modified point clouds such that every point in pc1 has a
	neighbor in pc2 that is within distance maxd
	"""
	pc2neighbor_for_pc1 = np.array(get_closest_points(pc1, pc2))
	if method == 'mean':
		mdist = np.mean(pc2neighbor_for_pc1, 0)[0]
		mdev = mad(pc2neighbor_for_pc1, 0, method='mean')[0]
	else:
		mdist = np.median(pc2neighbor_for_pc1, 0)[0]
		mdev = mad(pc2neighbor_for_pc1, 0, method='median')[0]
	passing = abs(pc2neighbor_for_pc1[:, 0] - mdist) < mdev * 4
	goodpc1 = pc1.T[passing]
	goodpc2 = pc2.T[pc2neighbor_for_pc1[:, 1][passing].astype('int')]

	return goodpc1.T, goodpc2.T


def mat2to3(mat2):
	""" 2D to 3D matrix:
		| a b c |       | a b 0 c |
		| d e f |  =>   | d e 0 f |
		| g h i |       | 0 0 1 0 |
						| g h 0 i |
	"""
	mat3 = np.eye(4)
	mat3[0:2, 0:2] = mat2[0:2, 0:2]
	mat3[3, 0:2] = mat2[2, 0:2]
	mat3[0:2, 3] = mat2[0:2, 2]
	mat3[3, 3] = mat2[2, 2]
	return mat3


# ### INFER TRANSFORMS ####

def infer_affine(X, Y, homo=1):
	""" calculate affine transform which maps a set of points X onto Y

	X - 3xM XYZ points in starting coordinate system.
	Y - 3xM XYZ points in destination coordinate system.

	(The resulting transform will take points from X space and map
	them into Y space).
	"""
	ndim = X.shape[0]
	if homo:
		X = np.vstack((X, np.ones((1, X.shape[1]))))
	affT = np.linalg.lstsq(X.T, Y.T)[0].T
	M = np.eye(ndim+1)
	M[:ndim, :] = affT
	return M


def infer_rigid(X, Y, scale=False):
	n = X.shape[1]
	tVec = np.mean(Y - X, 1)

	# And the mean-corrected positions
	Mx = X - np.tile(np.mean(X, 1), (n, 1)).T
	My = Y - np.tile(np.mean(Y, 1), (n, 1)).T

	# Now solve for rotation matrix, using [1]
	CC = np.dot(My, Mx.T) / n
	U, _, V  = np.linalg.svd(CC)
	F = np.eye(3)
	F[2, 2] = np.linalg.det(np.dot(U, V))  # Prevents reflection.
	rMat = np.dot(np.dot(U, F), V)

	if scale:
		sigmaXsq = np.sum(Mx**2) / n
		scaling = np.trace(np.dot(rMat.T, CC)) / sigmaXsq
	else:
		scaling = 1
	# return rMat, tVec, rotCent, scaling
	# rotCent = np.mean(X, 1)

	# construct matrix
	ndim = X.shape[0]
	M = np.eye(ndim+1)
	M[:ndim, :ndim] = rMat * scaling
	M[:ndim, ndim] = tVec
	return M


def infer_similarity(X, Y):
	return infer_rigid(X, Y, scale=True)


def infer_2step(X, Y):
	Yxyz = Y
	Yxy = Yxyz[:2]
	Xxy = X[:2]
	Xz = X[2:]
	T1 = infer_affine(Xxy, Yxy)
	M = mat2to3(T1)
	Xxy_reg = affineXF(Xxy, T1)
	Xxyz_reg = np.concatenate((Xxy_reg, Xz), axis=0)
	T2 = infer_similarity(Xxyz_reg, Yxyz)
	M[0:3, -1] += T2[0:3, -1]
	M[2, 2] *= T2[2, 2]
	return M


def infer_translation(X, Y):
	ndim = X.shape[0]
	M = np.eye(ndim+1)
	M[0:ndim, -1] = np.mean(Y - X, 1)
	return M


# ### APPLY TRANSFORMS ####

def cart2hom(X):
	return np.vstack((X, np.ones((1, X.shape[1]))))


def intrinsicToWorld(intrinsicXYZ, dxy, dz, worldStart=0.5):
	""" where intrinsicXYZ is a 1x3 vector np.array([X, Y, Z]) """
	return worldStart + (intrinsicXYZ - 0.5) * np.array([dxy, dxy, dz])


def worldToInstrinsic(worldXYZ, dxy, dz, worldStart=0.5):
	""" where XYZ coord is a 1x3 vector np.array([X, Y, Z]) """
	return .5 + (worldXYZ - worldStart) / np.array([dxy, dxy, dz])


def affineXF(X, T, invert=False):
	ndim = X.shape[0]
	X = np.vstack((X, np.ones((1, X.shape[1]))))
	if not invert:
		return np.dot(T, X)[:ndim, :]
	else:
		return np.dot(np.linalg.inv(T), X)[:ndim, :]


def rigidXF(X, rMat, tVec, rotCent=None, scaling=1, invert=False):
	xlen = X.shape[1]

	if rotCent is None:
		rotCent = np.mean(X, 1)

	X - np.tile(rotCent, (xlen, 1)).T

	if not invert:
		Y = np.dot(rMat, X - np.tile(rotCent, (xlen, 1)).T)
		Y *= scaling
		Y += np.tile(rotCent + tVec, (xlen, 1)).T
	else:
		Y = np.dot(np.linalg.inv(rMat), X - np.tile(rotCent + tVec, (xlen, 1)).T)
		Y /= scaling
		Y += np.tile(rotCent, (xlen, 1)).T
	return Y


def translateXF(X, T, invert=False):
	T = np.tile(T[0:3, 3], (X.shape[1], 1))
	if not invert:
		return X + T.T
	else:
		return X - T.T


class lazyattr(object):
	"""Lazy object attribute whose value is computed on first access."""
	__slots__ = ('func',)

	def __init__(self, func):
		self.func = func

	def __get__(self, instance, owner):
		if instance is None:
			return self
		value = self.func(instance)
		if value is NotImplemented:
			return getattr(super(owner, instance), self.func.__name__)
		setattr(instance, self.func.__name__, value)
		return value


def f_Gauss3d(p, X, Y, Z):
	"""3D PSF model function with constant background
	parameter vector [A, x0, y0, z0, background]
	"""
	A, x0, y0, z0, wxy, wz, b = p
	# return A*scipy.exp(-((X-x0)**2 + (Y - y0)**2)/(2*s**2)) + b
	# print X.shape
	return A * np.exp(-((X - x0)**2 + (Y - y0)**2) / (2 * wxy**2) - ((Z - z0)**2) / (2 * wz**2)) + b


def weightedMissfitF(p, fcn, data, weights, *args):
	"""Helper function which evaluates a model function (fcn) with parameters (p)
	and additional arguments (*args) and compares this with measured data (data),
	scaling with precomputed weights corresponding to the errors in the measured
	data (weights).
	"""
	model = fcn(p, *args)
	model = model.ravel()
	# print model.shape
	# print data.shape
	# print sigmas.shape
	return (data - model) * weights


def FitModelWeighted(modelFcn, startParameters, data, sigmas, *args):
	return optimize.leastsq(
		weightedMissfitF, startParameters,
		(modelFcn, data.ravel(), (1.0 / sigmas).astype('f').ravel()) + args,
		full_output=1)


class GaussFitResult:
	def __init__(self, fitResults, dx, dz, slicekey=None, resultCode=None,
		fitErr=None):
		self.fitResults = fitResults
		self.dx = dx
		self.dz = dz
		self.slicekey = slicekey
		self.resultCode = resultCode
		self.fitErr = fitErr

	def A(self):
		return self.fitResults[0]

	def x(self, realspace=True):
		r = self.fitResults[1]
		return r if realspace else r / self.dx

	def y(self, realspace=True):
		r = self.fitResults[2]
		return r if realspace else r / self.dx

	def z(self, realspace=True):
		r = self.fitResults[3]
		return r if realspace else r / self.dz

	def wxy(self, realspace=True):
		r = self.fitResults[4]
		return r if realspace else r / self.dx

	def wz(self, realspace=True):
		r = self.fitResults[5]
		return r if realspace else r / self.dz

	def background(self):
		return self.fitResults[6]


class GaussFitter3D(object):
	def __init__(self, data, dz=0.3, dx=0.1, wx=0.17, wz=0.37):
		self.data = data
		self.dz = dz
		self.dx = dx
		self.wx = wx
		self.wz = wz

	def __getitem__(self, key):
		""" return gaussian fit of a 3D roi defined by a 3-tuple of slices """
		zslice, yslice, xslice = key
		# cut region out of data stack
		dataROI = self.data[zslice, yslice, xslice].astype('f')

		# generate grid to evaluate function on
		Z, Y, X = np.mgrid[zslice, yslice, xslice]
		# adjust for voxel size
		X = self.dx * X
		Y = self.dx * Y
		Z = self.dz * Z

		A = dataROI.max() - dataROI.min()  # amplitude

		drc = dataROI - dataROI.min()  # subtract background
		drc = np.maximum(drc - drc.max() / 2, 0)
		drc = drc / drc.sum()  # normalize sum to 1

		x0 = (X * drc).sum()
		y0 = (Y * drc).sum()
		z0 = (Z * drc).sum()

		startParameters = [3 * A, x0, y0, z0, self.wx, self.wz, dataROI.min()]

		# should use gain and noise map from camera Parameters
		# for now assume uniform noise characteristcs and sCMOS read noise
		electrons_per_ADU = 0.5
		TrueEMGain = 1
		NoiseFactor = 1
		ReadNoise = 1.2

		# estimate noise as read noise plus poisson noise
		sigma = np.sqrt(ReadNoise**2 + NoiseFactor**2 * electrons_per_ADU *
			TrueEMGain * np.maximum(dataROI, 1)) / electrons_per_ADU

		(res1, cov_x, infodict, mesg1, resCode) = FitModelWeighted(
			f_Gauss3d, startParameters, dataROI, sigma, X, Y, Z)
		# misfit = (infodict['fvec']**2).sum()  # nfev is the number of function calls

		fitErrors = None
		try:
			fitErrors = np.sqrt(
				np.diag(cov_x) * (infodict['fvec'] * infodict['fvec']).sum() /
				(dataROI.size - len(res1)))
		except Exception:
			pass

		return GaussFitResult(res1, self.dx, self.dz, key, resCode, fitErrors)


class FiducialCloud(object):

	def __init__(self, data=None, dz=0.3, dx=0.1, xysig=1, zsig=2.5, threshold='auto',
		mincount=20, imref=None):
		# data is a numpy array or filename
		self.data = None
		if data is not None:
			if isinstance(data, str) and osp.isfile(data):
				# fc = FiducialCloud('/path/to/file')
				try:
					import tifffile as tf
					self.filename = osp.basename(data)
					self.data = tf.imread(data).astype('f')
				except ImportError:
					raise ImportError('The tifffile package is required to read a '
						'filepath into an array.')
			elif isinstance(data, np.ndarray):
				# fc = FiducialCloud(np.ndarray)
				self.data = data
			else:
				raise ValueError('Input to Registration must either be a '
					'filepath or a numpy arrays')
		self.dx = dx
		self.dz = dz
		self.xysig = xysig
		self.zsig = zsig
		self.threshold = threshold
		self._mincount = mincount
		self.imref = imref
		self.coords = None
		if self.data is not None:
			self.update_coords()

	@property
	def mincount(self):
		return self._mincount

	@mincount.setter
	def mincount(self, value):
		self._mincount = value
		self.update_coords()
		print("found {} spots".format(self.count))

	@property
	def count(self):
		if self.coords is not None and self.coords.shape[1] > 0:
			return self.coords.shape[1]
		else:
			return 0

	@lazyattr
	def filtered(self):
		if self.data is not None:
			return log_filter(self.data, self.xysig, self.zsig)
		else:
			return None

	def autothresh(self, mincount=None):
		if mincount is None:
			mincount = self._mincount
		return get_thresh(self.filtered, mincount)[0]

	def update_coords(self, thresh=None):
		if self.filtered is None:
			return
		if thresh is None:
			thresh = self.threshold
		if thresh == 'auto':
			thresh = self.autothresh()
		labeled = ndimage.label(self.filtered > thresh)[0]
		objects = ndimage.find_objects(labeled)

		# FIXME: pass sigmas to wx and wz parameters of GaussFitter
		fitter = GaussFitter3D(self.data, dz=self.dz, dx=self.dx)
		gaussfits = []
		for chunk in objects:
			try:
				# TODO: filter by bead intensity as well to reject bright clumps
				F = fitter[chunk]
				if ((F.x(0) < self.data.shape[2]) and (F.x(0) > 0) and
					(F.y(0) < self.data.shape[1]) and (F.y(0) > 0) and
					(F.z(0) < self.data.shape[0]) and (F.z(0) > 0)):
						gaussfits.append(F)
			except Exception:
				pass
				# import warnings
				# warnings.warn('skipped a spot')
		self.coords = np.array([[n.x(0), n.y(0), n.z(0)] for n in gaussfits]).T
		if not len(self.coords):
			logging.warning('PointCloud has no points! {}'.format(
				self.filename if 'filename' in dir(self) else ''))

	@property
	def coords_inworld(self):
		return intrinsicToWorld(self.coords.T, self.dx, self.dz).T

	def show(self, withimage=True, filtered=True):
		import matplotlib.pyplot as plt
		if withimage and self.filtered is not None:
			if filtered:
				im = self.filtered.max(0)
			else:
				im = self.data.max(0)
			plt.imshow(im, cmap='gray', vmax=im.max() * 0.7)
		if self.count:
			plt.scatter(self.coords[0], self.coords[1], c='red', s=5)

	def toJSON(self):
		D = self.__dict__.copy()
		D.pop('filtered', None)
		D.pop('data', None)
		D['coords'] = self.coords.tolist()
		return json.dumps(D)

	def fromJSON(self, Jstring):
		J = json.loads(Jstring)
		for k, v in J.items():
			setattr(self, k, v)
		self.coords = np.array(self.coords)
		return self


class CloudSet(object):
	"""docstring for CloudSet"""

	def __init__(self, data=None, labels=None, **kwargs):
		if data is not None:
			if not isinstance(data, (list, tuple, set)):
				raise ValueError('CloudSet expects a list of np.ndarrays or '
					'filename strings')
			if labels is not None:
				if len(labels) != len(data):
					raise ValueError('Length of optional labels list must match '
						'length of the data list')
			self.N = len(data)
			self.clouds = [FiducialCloud(i, **kwargs) for i in data]
		else:
			self.clouds = []
			self.N = 0
		self.labels = labels

	def toJSON(self):
		return json.dumps({
			'N': self.N,
			'clouds': [cloud.toJSON() for cloud in self.clouds],
			'labels': self.labels
		})

	def fromJSON(self, Jstring):
		J = json.loads(Jstring)
		self.N = J['N']
		self.clouds = [FiducialCloud().fromJSON(js) for js in J['clouds']]
		self.labels = J['labels']
		return self

	@property
	def count(self):
		return [c.count for c in self.clouds]

	@property
	def count_matching(self):
		return self.matching()[0].shape[1]

	@property
	def mincount(self):
		return [c.mincount for c in self.clouds]

	@mincount.setter
	def mincount(self, value):
		for c in self.clouds:
			c.mincount = value
		self._matching = self._get_matching()

	def _get_matching(self, inworld=False):
		""" enforce matching points in cloudset """
		if inworld:
			coords = [C.coords_inworld for C in self.clouds]
		else:
			coords = [C.coords for C in self.clouds]
		while True:
			# for n in range(1, self.N):
			# 	self.clouds[0], self.clouds[n] = get_matching_points(
			# 		self.clouds[0], self.clouds[n])
			for m, n in itertools.combinations(range(self.N), 2):
				coords[m], coords[n] = get_matching_points(coords[m], coords[n])
			if len({c.shape for c in coords}) == 1:
				break
		if not all([len(c) for c in coords]):
			raise IndexError('At least one point cloud has no points')
		return coords

	def matching(self):
		if '_matching' in dir(self):
			return self._matching
		else:
			self._matching = self._get_matching()
			return self._matching

	def __getitem__(self, key):
		if isinstance(key, str):
			if self.labels is not None:
				if key in self.labels:
					return self.clouds[self.labels.index(key)]
				else:
					raise ValueError('Unrecognized label for CloudSet')
			else:
				raise ValueError('Cannot index CloudSet by string without '
					'provided labels')
		elif isinstance(key, int) and key < self.N:
			return self.clouds[key]
		else:
			raise ValueError('Index must either be label or int < numClouds in Set')

	# Main Method
	def tform(self, movingLabel=None, fixedLabel=None, mode='2step', inworld=False):
		""" get tform matrix that maps moving point cloud to fixed point cloud"""
		if self.labels is None:
			logging.warning('No label list provided... cannot get tform by label')
			return
		movingLabel = movingLabel if movingLabel is not None else self.labels[1]
		fixedLabel = fixedLabel if fixedLabel is not None else self.labels[0]

		try:
			movIdx = self.labels.index(movingLabel)
		except ValueError:
			raise ValueError('Could not find label {} in reg list: {}'.format(
				movingLabel, self.labels))
		try:
			fixIdx = self.labels.index(fixedLabel)
		except ValueError:
			raise ValueError('Could not find label {} in reg list: {}'.format(
				fixedLabel, self.labels))

		funcDict = {
			'translate'		: infer_translation,
			'translation'	: infer_translation,
			'rigid'			: infer_rigid,
			'similarity'	: infer_similarity,
			'affine'		: infer_affine,
			'2step'			: infer_2step,
			'cpd_rigid'		: CPDrigid,
			'cpd_similarity': CPDsimilarity,
			'cpd_affine'	: CPDaffine,
			'cpd_2step'		: cpd_2step,
		}

		mode = mode.lower()
		if mode in funcDict:
			if mode.startswith('cpd'):
				if inworld:
					moving = self.clouds[movIdx].coords_inworld.T
					fixed = self.clouds[fixIdx].coords_inworld.T
				else:
					moving = self.clouds[movIdx].coords.T
					fixed = self.clouds[fixIdx].coords.T
				if '2step' in mode:
					tform = funcDict[mode](moving, fixed)
				else:
					reg = funcDict[mode](moving, fixed)
					tform = reg.register(None)[4]
			else:
				if inworld:
					matching = self._get_matching(inworld=True)
					moving = matching[movIdx]
					fixed = matching[fixIdx]
				else:
					moving = self.matching()[movIdx]
					fixed = self.matching()[fixIdx]
				tform = funcDict[mode](moving, fixed)
			return tform
		else:
			raise ValueError('Unrecognized transformation mode: {}'.format(mode))

	def show(self, matching=False, withimage=True, filtered=True):
		"""show points in clouds overlaying image, if matching is true, only
		show matching points from all sets"""
		import matplotlib.pyplot as plt
		if withimage:
			if filtered:
				im = self.clouds[0].filtered.max(0)
			else:
				im = self.clouds[0].max(0)
			plt.imshow(im, cmap='gray', vmax=im.max() * 0.7)

		colors = ['red', 'purple', 'magenta', 'blue', 'green']
		for i in reversed(range(self.N)):
			if matching:
				X = self.matching()[i][0]
				Y = self.matching()[i][1]
			else:
				X = self.clouds[i].coords[0]
				Y = self.clouds[i].coords[1]
			plt.scatter(X, Y, c=colors[i], s=5)
		plt.show()

	def show_matching(self, **kwargs):
		self.show(matching=True, **kwargs)

	def showtform(self, movingLabel=None, fixedLabel=None, **kwargs):
		import matplotlib.pyplot as plt
		T = self.tform(movingLabel, fixedLabel, **kwargs)
		movingpoints = self[movingLabel].coords
		fixedpoints = self[fixedLabel].coords
		shiftedpoints = affineXF(movingpoints, T)
		fp = plt.scatter(fixedpoints[0], fixedpoints[1], c='b', s=5)
		mp = plt.scatter(movingpoints[0], movingpoints[1], c='m', marker='x', s=5)
		sp = plt.scatter(shiftedpoints[0], shiftedpoints[1], c='r', s=5)
		plt.legend((fp, mp, sp), ('Fixed', 'Moving', 'Registered'))
		plt.show()


def imshowpair(im1, im2, method=None, mip=False):
	# normalize
	if not im1.shape == im2.shape:
		raise ValueError('images must be same shape')

	if not mip:
		try:
			from tifffile import imshow
		except ImportError:
			from matplotlib.pyplot import imshow
			mip = True
	else:
		from matplotlib.pyplot import imshow
		if im1.ndim < 3:
			mip = False

	im1 = im1.astype(np.float) if not mip else im1.astype(np.float).max(0)
	im2 = im2.astype(np.float) if not mip else im2.astype(np.float).max(0)
	im1 -= im1.min()
	im1 /= im1.max()
	im2 -= im2.min()
	im2 /= im2.max()

	ndim = im1.ndim
	if method == 'diff':
		im3 = im1-im2
		im3 -= im3.min()
		im3 /= im3.max()
		imshow(im3, cmap='gray', vmin=0.2, vmax=.8)
	elif method == '3D':
		im3 = np.stack((im1, im2, im1), ndim)
		fig, subpl, ax = imshow(im3, subplot=221)
		imshow(np.rot90(im3.max(1)), figure=fig, subplot=222)
		imshow(im3.max(2), figure=fig, subplot=223)
	else:  # falsecolor
		im3 = np.stack((im1, im2, im1), ndim)
		imshow(im3)

###############################################################################
# code below is a *very* slightly modified version of the pycpd repo from
# Siavash Kallaghi.
#
# The MIT License
#
# Copyright (c) 2010-2016 Siavash Khallaghi, http://siavashk.github.io
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
###############################################################################


def cpd_2step(moving, fixed):
	fixXYZ = fixed
	fixXY = fixXYZ[:, :2]
	movXY = moving[:, :2]
	movZ = moving[:, 2:]
	reg1 = CPDaffine(fixXY, movXY)
	TmovXY, _, _, _, M = reg1.register(None)
	M = mat2to3(M)
	reg2 = CPDrigid(fixXYZ, np.concatenate((TmovXY, movZ), axis=1))
	tR = reg2.register(None)[3]
	M[2, 3] = tR[2]
	return M


class CPDregistration(object):
	def __init__(self, X, Y, R=None, t=None, s=None, sigma2=None, maxIterations=100, tolerance=0.001, w=0):
		if X.shape[1] != Y.shape[1]:
			raise ValueError('Both point clouds must have the same number of dimensions!')

		self.X             = X
		self.Y             = Y
		self.TY            = Y
		(self.N, self.D)   = self.X.shape
		(self.M, _)        = self.Y.shape
		self.R             = np.eye(self.D) if R is None else R
		self.t             = np.atleast_2d(np.zeros((1, self.D))) if t is None else t
		self.s             = 1 if s is None else s
		self.sigma2        = sigma2
		self.iteration     = 0
		self.maxIterations = maxIterations
		self.tolerance     = tolerance
		self.w             = w
		self.q             = 0
		self.err           = 0

	@property
	def matrix(self):
		M = np.eye(self.D + 1)
		M[:self.D, :self.D] = self.R * self.s
		M[:self.D, self.D] = self.t
		return M

	def register(self, callback):
		self.initialize()
		while self.iteration < self.maxIterations and self.err > self.tolerance:
			self.iterate()
			if callback:
				callback(iteration=self.iteration, error=self.err, X=self.X, Y=self.TY)
		return self.TY, self.s, self.R, self.t, self.matrix

	def iterate(self):
		self.EStep()
		self.MStep()
		self.iteration = self.iteration + 1

	def MStep(self):
		self.updateTransform()
		self.transformPointCloud()
		self.updateVariance()

	def transformPointCloud(self, Y=None):
		if not Y:
			self.TY = self.s * np.dot(self.Y, np.transpose(self.R)) + np.tile(np.transpose(self.t), (self.M, 1))
			return
		else:
			return self.s * np.dot(Y, np.transpose(self.R)) + np.tile(np.transpose(self.t), (self.M, 1))

	def initialize(self):
		self.Y = self.s * np.dot(self.Y, np.transpose(self.R)) + np.repeat(self.t, self.M, axis=0)
		self.TY = self.s * np.dot(self.Y, np.transpose(self.R)) + np.repeat(self.t, self.M, axis=0)
		if not self.sigma2:
			XX = np.reshape(self.X, (1, self.N, self.D))
			YY = np.reshape(self.Y, (self.M, 1, self.D))
			XX = np.tile(XX, (self.M, 1, 1))
			YY = np.tile(YY, (1, self.N, 1))
			diff = XX - YY
			err  = np.multiply(diff, diff)
			self.sigma2 = np.sum(err) / (self.D * self.M * self.N)

		self.err  = self.tolerance + 1
		self.q    = -self.err - self.N * self.D / 2 * np.log(self.sigma2)

	def EStep(self):
		P = np.zeros((self.M, self.N))

		for i in range(0, self.M):
			diff     = self.X - np.tile(self.TY[i, :], (self.N, 1))
			diff    = np.multiply(diff, diff)
			P[i, :] = P[i, :] + np.sum(diff, axis=1)

		c = (2 * np.pi * self.sigma2) ** (self.D / 2)
		c = c * self.w / (1 - self.w)
		c = c * self.M / self.N

		P = np.exp(-P / (2 * self.sigma2))
		den = np.sum(P, axis=0)
		den = np.tile(den, (self.M, 1))
		den[den == 0] = np.finfo(float).eps

		self.P   = np.divide(P, den)
		self.Pt1 = np.sum(self.P, axis=0)
		self.P1  = np.sum(self.P, axis=1)
		self.Np  = np.sum(self.P1)

		def updateTransform(self):
				raise NotImplementedError()

		def updateVariance(self):
				raise NotImplementedError()


class CPDsimilarity(CPDregistration):

	def __init__(self, *args, **kwargs):
		super(CPDsimilarity, self).__init__(*args, **kwargs)

	def updateTransform(self):
		muX = np.divide(np.sum(np.dot(self.P, self.X), axis=0), self.Np)
		muY = np.divide(np.sum(np.dot(np.transpose(self.P), self.Y), axis=0), self.Np)
		self.XX = self.X - np.tile(muX, (self.N, 1))
		YY      = self.Y - np.tile(muY, (self.M, 1))
		self.A = np.dot(np.transpose(self.XX), np.transpose(self.P))
		self.A = np.dot(self.A, YY)
		U, _, V = np.linalg.svd(self.A, full_matrices=True)
		C = np.ones((self.D, ))
		C[self.D - 1] = np.linalg.det(np.dot(U, V))
		self.R = np.dot(np.dot(U, np.diag(C)), V)
		self.YPY = np.dot(np.transpose(self.P1), np.sum(np.multiply(YY, YY), axis=1))
		self.s = np.trace(np.dot(np.transpose(self.A), self.R)) / self.YPY
		self.t = np.transpose(muX) - self.s * np.dot(self.R, np.transpose(muY))

	def updateVariance(self):
		qprev = self.q
		trAR     = np.trace(np.dot(self.A, np.transpose(self.R)))
		xPx      = np.dot(np.transpose(self.Pt1), np.sum(np.multiply(self.XX, self.XX), axis=1))
		self.q   = (xPx - 2 * self.s * trAR + self.s * self.s * self.YPY) / (2 * self.sigma2) + self.D * self.Np / 2 * np.log(self.sigma2)
		self.err = np.abs(self.q - qprev)
		self.sigma2 = (xPx - self.s * trAR) / (self.Np * self.D)
		if self.sigma2 <= 0:
			self.sigma2 = self.tolerance / 10


class CPDrigid(CPDsimilarity):

	def __init__(self, *args, **kwargs):
		super(CPDrigid, self).__init__(*args, **kwargs)
		self.s = 1

	@property
	def matrix(self):
		M = np.eye(self.D + 1)
		M[:self.D, :self.D] = self.R
		M[:self.D, self.D] = self.t
		return M

	def updateTransform(self):
		muX = np.divide(np.sum(np.dot(self.P, self.X), axis=0), self.Np)
		muY = np.divide(np.sum(np.dot(np.transpose(self.P), self.Y), axis=0), self.Np)
		self.XX = self.X - np.tile(muX, (self.N, 1))
		YY      = self.Y - np.tile(muY, (self.M, 1))
		self.A = np.dot(np.transpose(self.XX), np.transpose(self.P))
		self.A = np.dot(self.A, YY)
		U, _, V = np.linalg.svd(self.A, full_matrices=True)
		C = np.ones((self.D, ))
		C[self.D - 1] = np.linalg.det(np.dot(U, V))
		self.R = np.dot(np.dot(U, np.diag(C)), V)
		self.YPY = np.dot(np.transpose(self.P1), np.sum(np.multiply(YY, YY), axis=1))
		self.s = 1
		self.t = np.transpose(muX) - np.dot(self.R, np.transpose(muY))

	def transformPointCloud(self, Y=None):
		if not Y:
			self.TY = np.dot(self.Y, np.transpose(self.R)) + np.tile(np.transpose(self.t), (self.M, 1))
			return
		else:
			return np.dot(Y, np.transpose(self.R)) + np.tile(np.transpose(self.t), (self.M, 1))


class CPDaffine(CPDregistration):

	def __init__(self, *args, **kwargs):
		super(CPDaffine, self).__init__(*args, **kwargs)

	def updateTransform(self):
		muX = np.divide(np.sum(np.dot(self.P, self.X), axis=0), self.Np)
		muY = np.divide(np.sum(np.dot(np.transpose(self.P), self.Y), axis=0), self.Np)
		self.XX = self.X - np.tile(muX, (self.N, 1))
		YY      = self.Y - np.tile(muY, (self.M, 1))
		self.A = np.dot(np.transpose(self.XX), np.transpose(self.P))
		self.A = np.dot(self.A, YY)
		self.YPY = np.dot(np.transpose(YY), np.diag(self.P1))
		self.YPY = np.dot(self.YPY, YY)
		Rt = np.linalg.solve(np.transpose(self.YPY), np.transpose(self.A))
		self.R = np.transpose(Rt)
		self.t = np.transpose(muX) - np.dot(self.R, np.transpose(muY))

	def updateVariance(self):
		qprev = self.q
		trAR     = np.trace(np.dot(self.A, np.transpose(self.R)))
		xPx      = np.dot(np.transpose(self.Pt1), np.sum(np.multiply(self.XX, self.XX), axis=1))
		trRYPYP  = np.trace(np.dot(np.dot(self.R, self.YPY), np.transpose(self.R)))
		self.q   = (xPx - 2 * trAR + trRYPYP) / (2 * self.sigma2) + self.D * self.Np / 2 * np.log(self.sigma2)
		self.err = np.abs(self.q - qprev)
		self.sigma2 = (xPx - trAR) / (self.Np * self.D)
		if self.sigma2 <= 0:
			self.sigma2 = self.tolerance / 10