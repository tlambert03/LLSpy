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
# for GPU transformation, check out gputools.transforms.transformations.affine
>>> from gputools import affine
>>> out = affine(im560, 560_to_488_rigid)
"""

from scipy import ndimage, optimize, stats
import os
import itertools
import numpy as np
np.seterr(divide='ignore', invalid='ignore')


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
	goodpc1 = pc1[passing]
	goodpc2 = pc2[pc2neighbor_for_pc1[:, 1][passing].astype('int')]

	return goodpc1, goodpc2


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
	M[:ndim, :ndim] = rMat
	M *= scaling
	M[:ndim, ndim] = tVec
	return M


def infer_similarity(X, Y):
	return infer_rigid(X, Y, scale=True)


def infer_2step(X, Y):
	Yxyz = Y
	Yxy = Yxyz[:2]
	Xxy = X[:2]
	Xz = X[2:]
	Txy = infer_affine(Xxy, Yxy)
	M = mat2to3(Txy)
	Xxy_reg = affineXF(Xxy, Txy)
	Xxyz_reg = np.concatenate((Xxy_reg, Xz), axis=0)
	M[0:3, -1] += np.mean(Yxyz - Xxyz_reg, 1)
	return M


def infer_translation(X, Y):
	ndim = X.shape[0]
	M = np.eye(ndim+1)
	M[0:ndim, -1] = np.mean(Y - X, 1)
	return M


# ### APPLY TRANSFORMS ####

def cart2hom(X):
	return np.vstack((X, np.ones((1, X.shape[1]))))


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
	return optimize.leastsq(weightedMissfitF, startParameters, (modelFcn, data.ravel(), (1.0 / sigmas).astype('f').ravel()) + args, full_output=1)


class GaussFitResult:
	def __init__(self, fitResults, dx, dz, slicekey=None, resultCode=None, fitErr=None):
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
		drc = np.maximum(drc - drc.max() / 2, 0)  # subtract off half of the peak amplitude?
		drc = drc / drc.sum()  # normalize sum to 1

		x0 = (X * drc).sum()
		y0 = (Y * drc).sum()
		z0 = (Z * drc).sum()

		startParameters = [3 * A, x0, y0, z0, self.wx, self.wz, dataROI.min()]

		# should use gain and noise map from camera Parameters
		# for now assume uniform noise characteristcs
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

		r = GaussFitResult(res1, self.dx, self.dz, key, resCode, fitErrors)
		return r


class FiducialCloud(object):

	def __init__(self, data, labels=None, dz=0.3, dx=0.1, xysig=1, zsig=2.5,
		threshold='auto', mincount=20):
		# data is a list or tuple of 3D arrays

		if all([isinstance(f, str) for f in data]) and all([os.path.isfile(f) for f in data]):
			# user provided list of filenames
			try:
				import tifffile as tf
				self.data = [tf.imread(A).astype('f') for A in data]
			except ImportError:
				raise ImportError('The tifffile package is required to read a '
					'list of filepaths into arrays.')
		elif all([isinstance(f, np.ndarray) for f in data]):
			# user provided list of numpy arrays
			self.data = data
		else:
			raise ValueError('Input to Registration must either be a '
				'list of filepaths or a list of numpy arrays')
		self.N = len(self.data)
		if labels is not None:
			if len(labels) != self.N:
				raise ValueError('Length of optional labels list must match '
					'length of the data list')

		self.labels = labels
		self.dx = dx
		self.dz = dz
		self.xysig = xysig
		self.zsig = zsig
		self.threshold = threshold
		self._mincount = mincount
		self.update()
		self.eliminate_orphans()

	@property
	def mincount(self):
		return self._mincount

	@mincount.setter
	def mincount(self, value):
		self._mincount = value
		self.update()
		print("found {} spots".format(self.count))

	@property
	def count(self):
		return max([len(c) for c in self.clouds])

	def update(self):
		self.find_spots()
		self.fit_spots()

	def _filtereddata(self):
		# If we've already done the filtering, return our saved copy
		if ("filtered" in dir(self)):
			return self.filtered
		else:  # Otherwise do filtering
			self.filtered = [log_filter(im, self.xysig, self.zsig) for im in self.data]
			return self.filtered

	def autothresh(self, mincount=None):
		if mincount is None:
			mincount = self._mincount
		return [get_thresh(img, mincount)[0] for img in self._filtereddata()]

	def find_spots(self, thresh=None):
		if thresh is None:
			thresh = self.threshold
		if thresh == 'auto':
			thresh = self.autothresh()
		else:
			thresh = [thresh] * self.N
		labeled = [ndimage.label(
			self._filtereddata()[i] > thresh[i])[0] for i in range(self.N)]
		self.objects = [ndimage.find_objects(l) for l in labeled]

	def fit_spots(self, realspace=False):
		self.fitters = [GaussFitter3D(im, dz=self.dz) for im in self.data]
		self.fits = []
		self.clouds = []
		for i in range(self.N):
			Ft = self.fitters[i]
			Ob = self.objects[i]
			gaussfits = []
			for k in Ob:
				try:
					gaussfits.append(Ft[k])
				except Exception:
					pass
					# import warnings
					# warnings.warn('skipped a spot')
			self.fits.append(gaussfits)
			self.clouds.append(np.array(
				[[n.x(realspace), n.y(realspace), n.z(realspace)]
				for n in gaussfits])
			)
		if not all([len(c) for c in self.clouds]):
			raise IndexError('At least one point cloud has no points')

	def eliminate_orphans(self):
		""" enforce matching points """
		while True:
			# for n in range(1, self.N):
			# 	self.clouds[0], self.clouds[n] = get_matching_points(
			# 		self.clouds[0], self.clouds[n])
			for m, n in itertools.combinations(range(self.N), 2):
				self.clouds[m], self.clouds[n] = get_matching_points(
					self.clouds[m], self.clouds[n])
			if len({len(c) for c in self.clouds}) == 1:
				break
		if not all([len(c) for c in self.clouds]):
			raise IndexError('At least one point cloud has no points')

	def get_transVec(self, movIdx=1, fixIdx=0):
		"""get translation vector to map A to B"""
		return (self.clouds[fixIdx] - self.clouds[movIdx]).mean(0)

	def get_rigid_Matrix(self, movIdx=1, fixIdx=0):
		reg = CPDrigid(self.clouds[fixIdx], self.clouds[movIdx])
		_, _, _, _, M = reg.register(None)
		return M

	def get_affine_Matrix(self, movIdx=1, fixIdx=0):
		reg = CPDaffine(self.clouds[fixIdx], self.clouds[movIdx])
		_, _, _, _, M = reg.register(None)
		return M

	def get_affineXY_rigidZ(self, movIdx=1, fixIdx=0):
		fixXYZ = self.clouds[fixIdx]
		fixXY = fixXYZ[:, :2]
		movXY = self.clouds[movIdx][:, :2]
		movZ = self.clouds[movIdx][:, 2:]
		reg1 = CPDaffine(fixXY, movXY)
		TmovXY, _, _, _, M = reg1.register(None)
		M = mat2to3(M)
		reg2 = CPDrigid(fixXYZ, np.concatenate((TmovXY, movZ), axis=1))
		_, _, _, tR, _ = reg2.register(None)
		M[2, 3] = tR[2]
		return M

	def get_tform_by_label(self, movingLabel, fixedLabel=None, mode='rigid'):
		if self.labels is None:
			print('No label list provided... cannot get tform by label')
			return
		if fixedLabel is None:
			# default to first array in list as reference
			fixedLabel = self.labels[0]
		# try/except?
		movIdx = self.labels.index(movingLabel)
		fixIdx = self.labels.index(fixedLabel)

		if mode == 'rigid':
			return self.get_rigid_Matrix(movIdx, fixIdx)
		elif mode == 'affine':
			return self.get_affine_Matrix(movIdx, fixIdx)
		elif mode == 'translate':
			return self.get_transVec(movIdx, fixIdx)
		else:
			raise ValueError('Unrecognized transformation mode: {}'.format(mode))

	def show(self, withimage=True, filtered=True):
		import matplotlib.pyplot as plt
		if withimage:
			if filtered:
				im = self.filtered[0].max(0)
			else:
				im = self.data[0].max(0)
			plt.imshow(im, cmap='gray', vmax=im.max() * 0.7)

		colors = ['red', 'purple', 'magenta', 'blue']
		for i in reversed(range(self.N)):
			X = self.clouds[i][:, 0]
			Y = self.clouds[i][:, 1]
			plt.scatter(X, Y, c=colors[i], s=5)


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


class CPDregistration(object):
	def __init__(self, X, Y, R=None, t=None, s=None, sigma2=None, maxIterations=100, tolerance=0.001, w=0):
		if X.shape[1] != Y.shape[1]:
			raise 'Both point clouds must have the same number of dimensions!'

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
		M[:self.D, :self.D] = self.R
		M *= self.s
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
		self.Y = self.sself.sself.s * np.dot(self.Y, np.transpose(self.R)) + np.repeat(self.t, self.M, axis=0)
		self.TY = self.sself.sself.s * np.dot(self.Y, np.transpose(self.R)) + np.repeat(self.t, self.M, axis=0)
		if not self.sself.sself.sigma2:
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
				raise NotImplementedError

		def updateVariance(self):
				raise NotImplementedError


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
