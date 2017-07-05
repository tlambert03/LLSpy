from __future__ import division, print_function

from llspy.config import config
from llspy.core.settingstxt import LLSsettings
from llspy.core import parse
from llspy.core import compress
from llspy.core.cudabinwrapper import CUDAbin
from llspy.util import util
from llspy.camera.camera import CameraParameters, CameraROI

import os
import shutil
import warnings
import numpy as np
import pprint
from tifffile import TiffFile, imsave, imread

try:
	import pathlib as plib
	plib.Path().expanduser()
except (ImportError, AttributeError):
	import pathlib2 as plib
except (ImportError, AttributeError):
	raise ImportError('no pathlib detected. For python2: pip install pathlib2')

try:
	from joblib import Parallel, delayed
	from multiprocessing import cpu_count
	hasjoblib = True
except ImportError:
	warnings.warn("Warning: joblib module not found... parallel processing disabled")
	hasjoblib = False


# FIXME: fix metadata on save
def correctTimepoint(fnames, camparams, outpath, median):
	'''accepts a list of filenames (fnames) that represent Z stacks that have
	been acquired in an interleaved manner (i.e. ch1z1,ch2z1,ch1z2,ch2z2...)
	'''
	stacks = [imread(f) for f in fnames]
	outstacks = camparams.correct_stacks(stacks, median=median)
	outnames = [str(outpath.joinpath(os.path.basename(
		str(f).replace('.tif', '_COR.tif')))) for f in fnames]
	for n in range(len(outstacks)):
		with warnings.catch_warnings():
			warnings.simplefilter("ignore")
			imsave(outnames[n], outstacks[n], imagej=True)


class LLSdir(object):
	'''Top level class for an LLS experiment folder

	Detect parameters of an LLS experiment from a folder of files.
	'''

	def __init__(self, path):
		self.path = plib.Path(path)
		self.settings_files = [str(s) for s in self.path.glob('*Settings.txt')]
		self.has_settings = len(self.settings_files) > 0
		if self.has_settings:
			self.settings = LLSsettings(self.settings_files[0])
			self.date = self.settings.date
		else:
			warnings.warn('No Settings.txt folder detected, is this an LLS folder?')
		if self.get_all_tiffs():
			self.ditch_partial_tiffs()
			self.count_tiffs()
			self.get_volume_shape()

	def get_all_tiffs(self):
		'''a list of every tiff file in the top level folder (all raw tiffs)'''
		all_tiffs = sorted(self.path.glob('*.tif'))
		if not all_tiffs:
			warnings.warn('No raw/uncompressed Tiff files detected in folder')
			return 0
		self.nFiles = len(all_tiffs)
		# self.bytes can be used to get size of raw data: np.sum(self.bytes)
		self.bytes = [f.stat().st_size for f in all_tiffs]
		self.all_tiffs = [str(f) for f in all_tiffs]
		return 1

	def ditch_partial_tiffs(self):
		'''yields self.raw: a list of tiffs that match in file size.
		this excludes partially acquired files that can screw up various steps
		perhaps a better (but slower?) approach would be to look at the tiff
		header for each file?
		'''
		self.file_size = round(np.mean(self.bytes), 2)
		i = 0
		self.raw = []
		for f in self.all_tiffs:
			if abs(self.bytes[i] - self.file_size) < 1000:
				self.raw.append(str(f))
			else:
				warnings.warn('discarding small file:  {}'.format(f.name))
			i += 1
		self.unraw = list(
			set(self.raw).difference(set(self.all_tiffs)))

	# FIXME
	# this is ugly code... refactor
	def count_tiffs(self):
		self.imagecount = []
		self.wavelength = []
		self.interval = []
		for c in range(6):
			q = [f for f in self.raw if 'ch' + str(c) in f]
			if len(q):
				self.imagecount.append(len(q))
				self.wavelength.append(parse.parse_filename(str(q[0]), 'wave'))
				if len(q) > 1:
					self.interval.append(
						parse.parse_filename(str(q[1]), 'reltime') / 1000)
		self.nc = len(self.imagecount)
		self.nt = max(self.imagecount)
		if all([f == self.imagecount[0] for f in self.imagecount]):
			# different count for each channel ... decimated stacks?
			self.decimated = False
		else:
			self.decimated = True
		try:
			self.duration = max(
				[(a - 1) * b for a, b in zip(self.imagecount, self.interval)])
		except Exception:
			self.duration = []

	def get_volume_shape(self):
		with warnings.catch_warnings():
			warnings.simplefilter("ignore")
			firstTiff = TiffFile(self.raw[0])
		self.shape = firstTiff.series[0].shape
		self.nz, self.ny, self.nx = self.shape
		self.bit_depth = firstTiff.pages[0].bits_per_sample

	def has_been_processed(self):
		return bool(len([s for s in self.path.glob('*ProcessingLog.txt')]))

	def has_corrected(self):
		corpath = self.path.joinpath('Corrected')
		if corpath.exists():
			if len(list(corpath.glob('*COR*'))) < self.nFiles:
				# partial correction
				warnings.warn('Corrected files incomplete')
				return False
			else:
				return True
		else:
			return False

	def compress(self, subfolder='.', **kwargs):
		return compress.make_tar(self.path.joinpath(subfolder), **kwargs)

	def decompress(self, subfolder='.', **kwargs):
		o = compress.untar(self.path.joinpath(subfolder), **kwargs)
		if self.get_all_tiffs():
			self.ditch_partial_tiffs()
			self.count_tiffs()
			self.get_volume_shape()
		return o

	def raw_is_compressed(self):
		return bool(len([s for s in self.path.glob('*.bz2')]))

	def reduce_to_raw(self, keepmip=True, verbose=True):
		"""
		need to consider the case of sepmips
		"""
		if verbose:
			print('reducing %s...' % str(self.path.name))
		subfolders = ['GPUdecon', 'CPPdecon', 'Deskewed', 'Corrected']
		if keepmip:
			for folder in subfolders:
				# see if there is are MIP.tifs in the folder itself
				L = list(self.path.joinpath(folder).glob('*MIP*.tif'))

				if not len(L):
					if self.path.joinpath(folder, 'MIPs').is_dir():
						L = [self.path.joinpath(folder, 'MIPs')]
				if len(L):
					if not self.path.joinpath('MIPs').exists():
						not self.path.joinpath('MIPs').mkdir()
					for f in L:
						f.rename(self.path.joinpath('MIPs', f.name))
					break

		for folder in subfolders:
			if self.path.joinpath(folder).exists():
				try:
					if verbose:
						print('\tdeleting %s...' % folder)
					shutil.rmtree(self.path.joinpath(folder))
					if not keepmip and self.path.joinpath('MIPs').exists():
						shutil.rmtree(self.path.joinpath('MIPs'))
				except Exception:
					print("unable to remove directory: {}".format(
						self.path.joinpath(folder)))
					return 0
		try:
			i = self.path.glob('*' + config.__OUTPUTLOG__)
			for n in i:
				n.unlink()
		except Exception:
			pass
		return 1

	def freeze(self, verbose=True, keepmip=True, **kwargs):
		"""Freeze folder for long term storage.

		Delete's all deskewed and deconvolved data
		(with the execption of MIPs unless requested),
		then compresses raw files into compressed tarball
		"""
		if verbose:
			print("freezing {} ...".format(self.path.name))
		if self.reduce_to_raw(verbose=verbose, keepmip=keepmip, **kwargs):
			if self.compress(verbose=verbose, **kwargs):
				return 1

	def _get_otfs(self, otfdir=None):
		if hasattr(self.settings, 'mask'):
			innerNA = self.settings.mask.innerNA
			outerNA = self.settings.mask.outerNA
			for c in self.settings.channel.keys():
				pass
				# find the most recent otf that matches the mask settings
				# in the PSF directory and append it to the channel dict...
		else:
			pass

	def _get_cudaDeconv_options(self):
		opts = {}
		opts['drdata'] = self.settings.pixel_size
		if self.settings.z_motion == 'Sample piezo':
			opts['deskew'] = self.settings.sheet_angle
			opts['dzdata'] = float(self.settings.channel[0]['S PZT']['interval'])
		else:
			opts['deskew'] = 0
			opts['dzdata'] = float(self.settings.channel[0]['Z PZT']['interval'])
		return opts

	def _get_extended_options(self, **kwargs):
		pass

	def process_channel():
		pass

	def process(self, indir=None, filepattern='488', binary=CUDAbin(), **options):
		print(options)
		return
		if indir is None:
			indir = self.path
		opts = self._get_cudaDeconv_options()
		#otf = default_otfs[str(488)]
		output = binary.process(indir, filepattern, otf, **opts)
		return output

	def get_t(self, t):
		return parse.filter_t(self.raw, t)

	def get_c(self, c):
		return parse.filter_c(self.raw, c)

	def get_w(self, w):
		return parse.filter_w(self.raw, w)

	def get_reltime(self, rt):
		return parse.filter_reltime(self.raw, rt)

	def get_files(self, **kwargs):
		return parse.filter_files(self.raw, **kwargs)

	def correct_flash(self, camparams=None, target='parallel', median=True):
		if camparams is None:
			camparams = CameraParameters()
		dataroi = CameraROI(self.settings.camera.roi)
		if not camparams.roi == dataroi:
			try:
				camparams = camparams.get_subroi(dataroi)
			except Exception:
				raise ValueError('ROI in parameters doesn not match data ROI')

		outpath = self.path.joinpath('Corrected')
		if not outpath.is_dir():
			outpath.mkdir()
		self.settings.write(outpath.joinpath(self.settings.basename))
		timegroups = [self.get_t(t) for t in range(self.nt)]

		if hasjoblib and target == 'parallel':
			Parallel(n_jobs=cpu_count(), verbose=9)(delayed(
				correctTimepoint)(t, camparams, outpath, median) for t in timegroups)
		elif target == 'gpu':
			pass
		else:
			for t in timegroups:
				correctTimepoint(t, camparams, outpath, median)

	def __repr__(self):
		out = {}
		if hasattr(self, 'bytes'):
			out.update({'raw data size': util.format_size(np.mean(self.bytes))})
		for k, v in self.__dict__.items():
			if k not in {'all_tiffs', 'date', 'settings_files'}:
				out.update({k: v})
		return pprint.pformat(out)
