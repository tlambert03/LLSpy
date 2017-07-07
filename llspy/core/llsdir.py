from __future__ import print_function, division

from llspy.config import config
from llspy.core.settingstxt import LLSsettings
from llspy.core import parse
from llspy.core import compress
from llspy.core.cudabinwrapper import CUDAbin
from llspy.core.otf import get_otf_by_date
from llspy.util import util
from llspy.camera.camera import CameraParameters, CameraROI
from llspy import plib
from llspy.image.autodetect import feature_width, detect_background
from llspy.image.mipmerge import mergemips

import os
import shutil
import warnings
import numpy as np
import pprint
import tifffile as tf

try:
	from joblib import Parallel, delayed
	from multiprocessing import cpu_count
	hasjoblib = True
except ImportError:
	warnings.warn("Warning: joblib module not found... parallel processing disabled")
	hasjoblib = False


def correctTimepoint(fnames, camparams, outpath, median):
	'''accepts a list of filenames (fnames) that represent Z stacks that have
	been acquired in an interleaved manner (i.e. ch1z1,ch2z1,ch1z2,ch2z2...)
	'''
	stacks = [tf.imread(f) for f in fnames]
	outstacks = camparams.correct_stacks(stacks, median=median)
	outnames = [str(outpath.joinpath(os.path.basename(
		str(f).replace('.tif', '_COR.tif')))) for f in fnames]
	for n in range(len(outstacks)):
		with warnings.catch_warnings():
			warnings.simplefilter("ignore")
			util.imsave(util.reorderstack(np.squeeze(outstacks[n]), 'zyx'),
					outnames[n])


class LLSdir(object):
	'''Top level class for an LLS experiment folder

	Detect parameters of an LLS experiment from a folder of files.
	'''

	def __init__(self, path):
		self.path = plib.Path(path)
		self.basename = self.path.name
		self.date = None
		self.parameters = util.dotdict()
		self.tiff = util.dotdict()
		self.settings_files = self.get_settings_files()
		self.has_settings = bool(len(self.settings_files))
		if self.has_settings:
			if len(self.settings_files) > 1:
				warnings.warn('Multiple Settings.txt files detected...')
			self.settings = LLSsettings(self.settings_files[0])
			self.date = self.settings.date
			self.parameters.z_motion = self.settings.z_motion
			self.parameters.samplescan = bool(self.settings.z_motion == 'Sample piezo')
			if self.parameters.samplescan:
				self.parameters.dz = float(
					self.settings.channel[0]['S PZT']['interval'])
			else:
				self.parameters.dz = float(
					self.settings.channel[0]['Z PZT']['interval'])
			self.parameters.dx = self.settings.pixel_size
			self.parameters.angle = self.settings.sheet_angle
		else:
			warnings.warn('No Settings.txt folder detected, is this an LLS folder?')
		if self.get_all_tiffs():
			self.ditch_partial_tiffs()
			self.detect_parameters()
			self.read_tiff_header()

	def get_settings_files(self):
		return [str(s) for s in self.path.glob('*Settings.txt')]

	def get_all_tiffs(self):
		'''a list of every tiff file in the top level folder (all raw tiffs)'''
		all_tiffs = sorted(self.path.glob('*.tif'))
		if not all_tiffs:
			warnings.warn('No raw/uncompressed Tiff files detected in folder')
			return 0
		self.tiff.numtiffs = len(all_tiffs)
		# self.tiff.bytes can be used to get size of raw data: np.sum(self.tiff.bytes)
		self.tiff.bytes = [f.stat().st_size for f in all_tiffs]
		self.tiff.all = [str(f) for f in all_tiffs]
		return 1

	def ditch_partial_tiffs(self):
		'''yields self.tiff.raw: a list of tiffs that match in file size.
		this excludes partially acquired files that can screw up various steps
		perhaps a better (but slower?) approach would be to look at the tiff
		header for each file?
		'''
		self.tiff.size_raw = round(np.mean(self.tiff.bytes), 2)
		i = 0
		self.tiff.raw = []
		for f in self.tiff.all:
			if abs(self.tiff.bytes[i] - self.tiff.size_raw) < 1000:
				self.tiff.raw.append(str(f))
			else:
				warnings.warn('discarding small file:  {}'.format(f.name))
			i += 1
		self.tiff.rejected = list(
			set(self.tiff.raw).difference(set(self.tiff.all)))

	def detect_parameters(self):
		self.tiff.count = []
		self.parameters.wavelength = []
		self.parameters.interval = []
		for c in range(6):
			q = [f for f in self.tiff.raw if '_ch' + str(c) in f]
			if len(q):
				self.tiff.count.append(len(q))
				self.parameters.wavelength.append(
					parse.parse_filename(str(q[0]), 'wave'))
				if len(q) > 1:
					self.parameters.interval.append(
						parse.parse_filename(str(q[1]), 'reltime') / 1000)
		self.parameters.nc = len(self.tiff.count)
		self.parameters.nt = max(self.tiff.count)
		if len(set(self.tiff.count)) > 1:
			# different count for each channel ... decimated stacks?
			self.parameters.decimated = True
		else:
			self.parameters.decimated = False

		try:
			self.parameters.duration = max(
				[(a - 1) * b for a, b in zip(
					self.tiff.count, self.parameters.interval)])
		except Exception:
			self.parameters.duration = []

	def read_tiff_header(self):
		with warnings.catch_warnings():
			warnings.simplefilter("ignore")
			firstTiff = tf.TiffFile(self.tiff.raw[0])
		self.parameters.shape = firstTiff.series[0].shape
		self.parameters.nz, self.parameters.ny, self.parameters.nx = self.parameters.shape
		self.tiff.bit_depth = firstTiff.pages[0].bits_per_sample

	def is_compressed(self, subdir='.'):
		return bool(len([s for s in self.path.joinpath(subdir).glob('*.bz2')]))

	def has_been_processed(self):
		return bool(len([s for s in self.path.glob('*ProcessingLog.txt')]))

	def is_corrected(self):
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
		return compress.make_tar(str(self.path.joinpath(subfolder)), **kwargs)

	def decompress(self, subfolder='.', **kwargs):
		o = compress.untar(str(self.path.joinpath(subfolder)), **kwargs)
		if self.get_all_tiffs():
			self.ditch_partial_tiffs()
			self.detect_parameters()
			self.read_tiff_header()
		return o

	def reduce_to_raw(self, keepmip=True, verbose=True):
		"""
		need to consider the case of sepmips
		"""
		if verbose:
			print('reducing %s...' % str(self.path.name))

		subfolders = ['GPUdecon', 'CPPdecon', 'Deskewed', 'Corrected']

		if keepmip:
			miplist = list(self.path.glob('**/*_MIP_*.tif'))
			if len(miplist):
				if not self.path.joinpath('MIPs').exists():
					not self.path.joinpath('MIPs').mkdir()
				for mipfile in miplist:
					mipfile.rename(self.path.joinpath('MIPs', mipfile.name))
		else:
			subfolders.append('MIPs')

		for folder in subfolders:
			if self.path.joinpath(folder).exists():
				try:
					if verbose:
						print('\tdeleting %s...' % folder)
					shutil.rmtree(self.path.joinpath(folder))
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

	def autoprocess(self, correct=False, median=True, width='auto', pad=50,
		shift=0, background=None, trange=None, crange=None, iters=10,
		MIP=(0, 0, 1), rawMIP=None, uint16=True, rotate=False,
		bleachCorrection=False, saveDeskewedRaw=True, quiet=False, verbose=False,
		compress=False, mipmerge=True, binary=CUDAbin()):
		"""Main method for easy processing of the folder"""
		otfs = self.get_otfs()
		E = self

		if correct:
			E = E.correct_flash(trange=trange, median=median)

		P = E.parameters

		# filter by channel
		if crange is None:
			crange = range(P.nc)
		elif isinstance(crange, int):
			crange = [crange]
		else:
			crange = [item for item in crange if item < P.nc]

		if background is None:
			background = E.get_background()
		elif isinstance(background, (int, float)):
			background = [background] * len(crange)

		if (width == 'auto') and not rotate:
			wd = E.get_feature_width()

		for c in crange:
			opts = {
				'background': background[c] if not correct else 0,
				'drdata': P.dx,
				'dzdata': P.dz,
				'wavelength': P.wavelength[c] / 1000,
				'deskew': P.angle if P.samplescan else 0,
				'saveDeskewedRaw': bool(saveDeskewedRaw) if P.samplescan else False,
				'MIP': MIP,
				'rawMIP': rawMIP,
				'uint16': uint16,
				'bleachCorrection': bool(bleachCorrection),
				'RL': iters if iters is not None else 0,
				'rotate': P.angle if rotate else 0,
				'quiet': bool(quiet),
				'verbose': bool(verbose),
			}
			if width and not rotate:
				opts.update({
					'width': wd['width'] if width == 'auto' else width,
					'shift': wd['offset'] if width == 'auto' else shift,
				})
			# filter by channel and trange
			if trange is not None:
				if isinstance(trange, int):
					trange = [trange]
				filepattern = 'ch{}_stack{}'.format(
					c, util.pyrange_to_perlregex(trange))
			else:
				filepattern = 'ch{}_'.format(c)
			otf = otfs[c]
			response = binary.process(str(E.path), filepattern, otf, **opts)
			if verbose:
				print(response.output.decode('utf-8'))
		if mipmerge:
			# the "**" pattern means this directory and all subdirectories, recursively
			for MIPdir in E.path.glob('**/MIPs/'):
				arrays = mergemips(MIPdir)
				filelist = list(MIPdir.glob('*MIP*.tif'))
				cor = 'COR_' if 'COR' in filelist[0].name else ''
				for axis in arrays:
					array = arrays[axis]
					outname = '{}_{}MIP_{}.tif'.format(E.basename, cor, axis)
					util.imsave(array, str(MIPdir.joinpath(outname)),
						dx=E.parameters.dx, dt=E.parameters.interval[0])
				[file.unlink() for file in filelist]
		if compress:
			E.compress()

	def process(self, filepattern, otf, indir=None, binary=CUDAbin(), **opts):
		if indir is None:
			indir = str(self.path)
		output = binary.process(indir, filepattern, otf, **opts)
		return output

	def get_t(self, t):
		return parse.filter_t(self.tiff.raw, t)

	def get_c(self, c):
		return parse.filter_c(self.tiff.raw, c)

	def get_w(self, w):
		return parse.filter_w(self.tiff.raw, w)

	def get_reltime(self, rt):
		return parse.filter_reltime(self.tiff.raw, rt)

	def get_files(self, **kwargs):
		return parse.filter_files(self.tiff.raw, **kwargs)

	def get_otfs(self):
		""" intelligently pick OTF from archive directory based on date and mask
		settings..."""
		otfs = {}
		for c in range(self.parameters.nc):
			wave = self.parameters.wavelength[c]
			if hasattr(self.settings, 'mask'):
				innerNA = self.settings.mask.innerNA
				outerNA = self.settings.mask.outerNA
				# find the most recent otf that matches the mask settings
				# in the PSF directory and append it to the channel dict...
				otf = get_otf_by_date(
					self.date, wave, (innerNA, outerNA), direction='nearest')
			else:
				otf = str(config.__OTFPATH__.joinpath(str(wave) + '_otf.tif'))
			otfs[c] = otf
		return otfs

	def get_feature_width(self, **kwargs):
		# defaults background=100, pad=100, sigma=2
		w = {}
		w.update(feature_width(self, **kwargs))
		# self.parameters.content_width = w['width']
		# self.parameters.content_offset = w['offset']
		# self.parameters.deskewed_nx = w['newX']
		return w

	# FIXME: should calculate background of provided folder (e.g. Corrected)
	def get_background(self, **kwargs):
		# defaults background and=100, pad=100, sigma=2
		bgrd = {}
		for c in range(self.parameters.nc):
			i = tf.imread(self.get_files(t=0, c=c))
			bgrd[c] = detect_background(i)
		# self.parameters.background = bgrd
		return bgrd

	def correct_flash(self, trange=None, camparams=None, target='parallel', median=True):
		""" where trange is an iterable of timepoints

		"""
		if not self.has_settings:
			raise LLSpyError('Cannot correct flash pixels without settings.txt file')
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
		self.settings.write(str(outpath.joinpath(self.settings.basename)))

		if trange is not None:
			timegroups = [self.get_t(t) for t in trange]
		else:
			timegroups = [self.get_t(t) for t in range(self.parameters.nt)]

		if hasjoblib and target == 'parallel':
			Parallel(n_jobs=cpu_count(), verbose=9)(delayed(
				correctTimepoint)(t, camparams, outpath, median) for t in timegroups)
		elif target == 'gpu':
			pass
		else:
			for t in timegroups:
				correctTimepoint(t, camparams, outpath, median)
		return LLSdir(outpath)

	def toJSON(self):
		import json
		return json.dumps(self, default=lambda o: o.__dict__,
			sort_keys=True, indent=4)

	def __str__(self):
		out = {}
		if hasattr(self, 'bytes'):
			out.update({'raw data size': util.format_size(np.mean(self.tiff.bytes))})
		for k, v in self.__dict__.items():
			if k not in {'all_tiffs', 'date', 'settings_files'}:
				out.update({k: v})
		return pprint.pformat(out)


class LLSpyError(Exception):
	"""
	Generic exception indicating anything relating to the execution
	of LLSpy. A string containing an error message should be supplied
	when raising this exception.
	"""
	pass
