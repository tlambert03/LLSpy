from __future__ import print_function, division

from . import plib
from . import config
from .settingstxt import LLSsettings
from . import parse, compress, schema
from .otf import get_otf_by_date
from .cudabinwrapper import CUDAbin
from . import util
from .camera import CameraParameters
from . import arrayfun

from llspy.libcudawrapper import deskewGPU, affineGPU, quickDecon
from fiducialreg.fiducialreg import CloudSet

import os
import sys
import shutil
import warnings
import numpy as np
import pprint
import json
import re
import glob
import tifffile as tf

np.seterr(divide='ignore', invalid='ignore')

# this is for multiprocessing with pyinstaller on windows
# https://github.com/pyinstaller/pyinstaller/wiki/Recipe-Multiprocessing
try:
    # Python 3.4+
    if sys.platform.startswith('win'):
        import multiprocessing.popen_spawn_win32 as forking
    else:
        import multiprocessing.popen_fork as forking
except ImportError:
    import multiprocessing.forking as forking

if sys.platform.startswith('win'):
    # First define a modified version of Popen.
    class _Popen(forking.Popen):
        def __init__(self, *args, **kw):
            if hasattr(sys, 'frozen'):
                # We have to set original _MEIPASS2 value from sys._MEIPASS
                # to get --onefile mode working.
                os.putenv('_MEIPASS2', sys._MEIPASS)
            try:
                super(_Popen, self).__init__(*args, **kw)
            finally:
                if hasattr(sys, 'frozen'):
                    # On some platforms (e.g. AIX) 'os.unsetenv()' is not
                    # available. In those cases we cannot delete the variable
                    # but only set it to the empty string. The bootloader
                    # can handle this case.
                    if hasattr(os, 'unsetenv'):
                        os.unsetenv('_MEIPASS2')
                    else:
                        os.putenv('_MEIPASS2', '')

    # Second override 'Popen' class with our modified version.
    forking.Popen = _Popen

from multiprocessing import Process, cpu_count, Pool


def correctTimepoint(fnames, camparams, outpath, median, target='cpu'):
	'''accepts a list of filenames (fnames) that represent Z stacks that have
	been acquired in an interleaved manner (i.e. ch1z1,ch2z1,ch1z2,ch2z2...)
	'''
	stacks = [util.imread(f) for f in fnames]
	outstacks = camparams.correct_stacks(stacks, median=median, target=target)
	outnames = [str(outpath.joinpath(os.path.basename(
		str(f).replace('.tif', '_COR.tif')))) for f in fnames]
	for n in range(len(outstacks)):
		with warnings.catch_warnings():
			warnings.simplefilter("ignore")
			util.imsave(util.reorderstack(np.squeeze(outstacks[n]), 'zyx'),
					outnames[n])


def unwrapper(tup):
	return correctTimepoint(*tup)


def preview(E, tR=0, **kwargs):
	""" process a restricted time range (defaults to t=0) with same settings
	as autoprocess, but without file I/O"""

	if not isinstance(E, LLSdir):
		if isinstance(E, str):
			E = LLSdir(E)

	if E.is_compressed():
		E.decompress()

	if not E.ready_to_process:
		if not E.has_lls_tiffs:
			warnings.warn('No TIFF files to process in {}'.format(E.path))
		if not E.has_settings:
			warnings.warn('Could not find Settings.txt file in {}'.format(E.path))
		return

	kwargs['tRange'] = tR
	P = E.localParams(**kwargs)

	out = []
	for timepoint in P.tRange:
		stacks = [util.imread(f) for f in E.get_t(timepoint)]
		# print("shape_raw: {}".format(stacks[0].shape))
		if P.bFlashCorrect:
			camparams = CameraParameters(P.camparamsPath)
			camparams = camparams.get_subroi(E.settings.camera.roi)
			stacks = camparams.correct_stacks(stacks, trim=P.edgeTrim, median=P.bMedianCorrect)
		else:
			# camera correction trims edges, so if we aren't doing the camera correction
			# we need to call the edge trim on our own
			if P.edgeTrim is not None and any(P.edgeTrim):
				stacks = [arrayfun.trimedges(s, P.edgeTrim) for s in stacks]
			# camera correction also does background subtraction
			# so otherwise trigger it manually here
			stacks = [arrayfun.sub_background(s, b) for s, b in zip(stacks, P.background)]

		# FIXME: background is the only thing keeping this from just **P to deconvolve
		if P.nIters > 0:
			opts = {
				'nIters': P.nIters,
				'drdata': P.drdata,
				'dzdata': P.dzdata,
				'deskew': P.deskew,
				'rotate': P.rotate,
				'width': P.width,
				'shift': P.shift,
				'background': 0,  # zero here because it's already been subtracted above
			}
			for i, d in enumerate(zip(stacks, P.otfs)):
				stk, otf = d
				stacks[i] = quickDecon(stk, otf, **opts)
		else:
			# deconvolution does deskewing and cropping, so we do it here if we're
			#
			if P.deskew:
				stacks = [deskewGPU(s, P.dzdata, P.drdata, P.deskew) for s in stacks]
			stacks = [arrayfun.cropX(s, P.width, P.shift) for s in stacks]

		# FIXME: this is going to be slow until we cache the tform Matrix results
		if P.bDoRegistration:
			if P.regCalibDir is None:
				warnings.warn('Registration requested but no Calibration Directory provided')
			else:
				RD = RegDir(P.regCalibDir)
				if RD.isValid:
					for i, d in enumerate(zip(stacks, P.wavelength)):
						stk, wave = d
						if not wave == P.regRefWave:  # don't reg the reference channel
							stacks[i] = RD.register_image_to_wave(stk, imwave=wave,
								refwave=P.regRefWave, mode=P.regMode)
				else:
					warnings.warn('Registration Calibration dir not valid'
						'{}'.format(P.regCalibDir))

		out.append(np.stack(stacks, 0))

	return np.stack(out, 0) if len(out) > 1 else out[0]


def process(E, binary=None, **kwargs):
	"""Main method for easy processing of the folder"""

	if not isinstance(E, LLSdir):
		if isinstance(E, str):
			E = LLSdir(E)

	if E.is_compressed():
		E.decompress()

	if not E.ready_to_process:
		if not E.has_lls_tiffs:
			warnings.warn('No TIFF files to process in {}'.format(E.path))
		if not E.has_settings:
			warnings.warn('Could not find Settings.txt file in {}'.format(E.path))
		return

	P = E.localParams(**kwargs)

	if binary is None:
		binary = CUDAbin()

	if P.bFlashCorrect:
		E = E.correct_flash(trange=P.tRange, median=P.bMedianCorrect)

	for chan in P.cRange:
		opts = {
			'background': P.background[chan] if not P.bFlashCorrect else 0,
			'drdata': P.drdata,
			'dzdata': P.dzdata,
			'wavelength': float(P.wavelength[chan])/1000,
			'deskew': P.deskew,
			'saveDeskewedRaw': P.saveDeskewedRaw,
			'MIP': P.MIP,
			'rMIP': P.rMIP,
			'uint16': P.uint16,
			'bleachCorrection': P.bleachCorrection,
			'RL': P.nIters,
			'rotate': P.rotate,
			'width': P.width,
			'shift': P.shift,
			# 'quiet': bool(quiet),
			# 'verbose': bool(verbose),
		}

		# filter by channel and trange
		if len(list(P.tRange)) == E.parameters.nt:
			filepattern = 'ch{}_'.format(chan)
		else:
			filepattern = 'ch{}_stack{}'.format(chan, util.pyrange_to_perlregex(P.tRange))

		response = binary.process(str(E.path), filepattern, P.otfs[chan], **opts)

		# if verbose:
		# 	print(response.output.decode('utf-8'))

	# FIXME: this is just a messy first try...
	if P.bDoRegistration:
		E.register(P.regRefWave, P.regMode, P.regCalibDir)

	if P.bMergeMIPs:
		E.mergemips()

	# if P.bMergeMIPsraw:
	# 	if E.path.joinpath('Deskewed').is_dir():
	# 		E.mergemips('Deskewed')

	if P.bCompress:
		E.compress()

	return response


def mergemips(folder, axis, write=True, dx=1, dt=1, delete=True):
	"""combine folder of MIPs into a single multi-channel time stack.
	return dict with keys= axes(x,y,z) and values = numpy array
	"""
	folder = plib.Path(folder)
	if not folder.is_dir():
		raise IOError('MIP folder does not exist: {}'.format(str(folder)))

	try:
		filelist = []
		tiffs = []
		channelCounts = []
		c = 0
		while True:
			channelFiles = sorted(folder.glob('*ch{}_stack*MIP_{}.tif'.format(c, axis)))
			if not len(channelFiles):
				break  # no MIPs in this channel
				# this assumes that there are no gaps in the channels (i.e. ch1, ch3 but not 2)
			for file in channelFiles:
				tiffs.append(tf.imread(str(file)))
				filelist.append(file)
			channelCounts.append(len(channelFiles))
			c += 1
		if not len(filelist):
			return None  # there were no MIPs for this axis
		if c > 0:
			nt = np.max(channelCounts)

			if (len(set(channelCounts)) > 1):
				raise ValueError('Cannot merge MIPS with different number of '
					'timepoints per channel')
			if len(tiffs) != c * nt:
				raise ValueError('Number of images does not equal nC * nT')

			stack = np.stack(tiffs)
			stack = stack.reshape((c, 1, nt,
						stack.shape[-2], stack.shape[-1]))  # TZCYX
			stack = np.transpose(stack, (2, 1, 0, 3, 4))

		if write:
			basename = parse.parse_filename(str(filelist[0]), 'basename')
			suffix = filelist[0].name.split('msecAbs')[1]
			if 'decon' in str(folder).lower():
				miptype = '_decon_'
			elif 'deskewed' in str(folder).lower():
				miptype = '_deskewed_'
			else:
				miptype = '_'
			suffix = suffix.replace('MIP', miptype + 'comboMIP')
			outname = basename + suffix
			util.imsave(stack, str(folder.joinpath(outname)), dx=dx, dt=dt)

		if delete:
			[file.unlink() for file in filelist if 'comboMIP' not in str(file)]

		return stack

	except ValueError:
		print("ERROR: failed to merge MIPs from {}".format(str(folder)))
		print("skipping...\n")


class LLSdir(object):
	'''Top level class for an LLS experiment folder

	Detect parameters of an LLS experiment from a folder of files.
	'''

	def __init__(self, path, ditch_partial=True):
		self.path = plib.Path(path)
		self.ditch_partial = ditch_partial
		self.settings_files = self.get_settings_files()
		self.has_settings = bool(len(self.settings_files))
		if not self.path.is_dir():
			return
		self.basename = self.path.name
		self.date = None
		self.parameters = util.dotdict()
		self.tiff = util.dotdict()
		if self.has_settings:
			if len(self.settings_files) > 1:
				warnings.warn('Multiple Settings.txt files detected...')
			self.settings = LLSsettings(self.settings_files[0])
			self.date = self.settings.date
			self.parameters.update(self.settings.parameters)
		else:
			pass
			# warnings.warn('No Settings.txt folder detected, is this an LLS folder?')
		if self.has_lls_tiffs:
			self.register_tiffs()

	@property
	def isValid(self):
		if self.path.is_dir() and self.has_settings:
			return True
		else:
			return False

	@property
	def ready_to_process(self):
		if self.path.is_dir():
			if self.has_lls_tiffs and self.has_settings:
				return True
		return False

	@property
	def has_lls_tiffs(self):
		if self.path.is_dir():
			for f in self.path.iterdir():
				if parse.filename_pattern.match(f.name):
					return True
		return False

	def get_settings_files(self):
		return [str(s) for s in self.path.glob('*Settings.txt')]

	def register_tiffs(self):
		if self.get_all_tiffs():
			if self.ditch_partial:
				self.ditch_partial_tiffs()
			else:
				self.tiff.raw = self.tiff.all
			self.detect_parameters()
			self.read_tiff_header()

	def get_all_tiffs(self):
		'''a list of every tiff file in the top level folder (all raw tiffs)'''
		all_tiffs = sorted(self.path.glob('*.tif'))
		if not all_tiffs:
			warnings.warn('No raw/uncompressed Tiff files detected in folder')
			return 0
		self.tiff.numtiffs = len(all_tiffs)
		# self.tiff.bytes can be used to get size of raw data: np.sum(self.tiff.bytes)
		self.tiff.bytes = [f.stat().st_size for f in all_tiffs]
		self.tiff.size_raw = round(np.median(self.tiff.bytes), 2)
		self.tiff.all = [str(f) for f in all_tiffs]
		return self.tiff.numtiffs

	def ditch_partial_tiffs(self):
		'''yields self.tiff.raw: a list of tiffs that match in file size.
		this excludes partially acquired files that can screw up various steps
		perhaps a better (but slower?) approach would be to look at the tiff
		header for each file?
		'''
		self.tiff.raw = []
		for idx, f in enumerate(self.tiff.all):
			if abs(self.tiff.bytes[idx] - self.tiff.size_raw) < 1000:
				self.tiff.raw.append(str(f))
			else:
				warnings.warn('discarding small file:  {}'.format(f))
		self.tiff.rejected = list(
			set(self.tiff.raw).difference(set(self.tiff.all)))
		if not len(self.tiff.raw):
			raise IndexError('We seem to have discarded of all the tiffs!')

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
					shutil.rmtree(str(self.path.joinpath(folder)))
				except Exception as e:
					print("unable to remove directory: {}".format(
						self.path.joinpath(folder)))
					print(e)
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

	def localParams(self, **kwargs):
		""" provides a validated dict of processing parameters that are specific
		to this LLSdir instance.
		accepts any kwargs that are recognized by the LLSParams schema.

		>>> E.localParams(nIters=0, bRotate=True, bleachCorrection=True)
		"""
		P = self.parameters
		S = schema.procParams(kwargs)

		if S.cRange is None:
			S.cRange = range(P.nc)
		else:
			if np.max(list(S.cRange)) > (P.nc - 1):
				warnings.warn('cRange was larger than number of Channels! Excluding C > {}'.format(P.nc - 1))
			S.cRange = sorted([n for n in S.cRange if n < P.nc])

		if S.tRange is None:
			S.tRange = range(P.nt)
		else:
			if np.max(list(S.tRange)) > (P.nt - 1):
				warnings.warn('tRange was larger than number of Timepoints! Excluding T > {}'.format(P.nt - 1))
			S.tRange = sorted([n for n in S.tRange if n < P.nt])

		# FIXME:
		# shouldn't have to get OTF if not deconvolving... though cudaDeconv
		# may have an issue with this...
		otfs = self.get_otfs(otfpath=S.otfDir)
		S.otfs = [otfs[i] for i in S.cRange]
		if S.nIters > 0 and any([(otf == '' or otf is None) for otf in S.otfs]):
			raise ValueError('Deconvolution requested but no OTF available.  Check OTF path')

		# note: background should be forced to 0 if it is getting corrected
		# in the camera correction step

		if S.bAutoBackground and self.has_lls_tiffs:
			B = self.get_background()
			S.background = [B[i] for i in S.cRange]
		else:
			S.background = [S.background] * len(list(S.cRange))

		if S.cropMode == 'auto':
			wd = self.get_feature_width()
			S.width = wd['width']
			S.shift = wd['offset']
		elif S.cropMode == 'none':
			S.width = 0
			S.shift = 0
		else:  # manual mode
			# use defaults
			S.width = S.width
			S.shift = S.shift
		# TODO: add constrainst to make sure that width/2 +/- shift is within bounds

		# add check for RegDIR
		# RD = RegDir(P.regCalibDir)
		# RD = self.path.parent.joinpath('tspeck')
		S.drdata = P.dx
		S.dzdata = P.dz
		S.dzFinal = P.dzFinal
		S.wavelength = P.wavelength
		S.deskew = P.angle if P.samplescan else 0
		S.saveDeskewedRaw = S.saveDeskewedRaw if P.samplescan else False
		if S.bRotate:
			S.rotate = S.rotate if S.rotate is not None else P.angle
		else:
			S.rotate = 0

		return util.dotdict(schema.__localSchema__(S))

	def autoprocess(self, **kwargs):
		"""Main method for easy processing of the folder"""
		return process(self, **kwargs)

	def mergemips(self, subdir=None, delete=True):
		""" look for MIP files in subdirectory, compress into single hyperstack
		and write file to disk"""
		if subdir is not None:
			if self.path.joinpath(subdir).is_dir():
				subdir = self.path.joinpath(subdir)
			else:
				warnings.warn('Could not find subdir: '.format('subdir'))
				return
		else:
			subdir = self.path

		# the "**" pattern means this directory and all subdirectories, recursively
		for MIPdir in subdir.glob('**/MIPs/'):
			# get dict with keys= axes(x,y,z) and values = numpy array
			for axis in ['z', 'y', 'x']:
				mergemips(MIPdir, axis, dx=self.parameters.dx, dt=self.parameters.interval[0])

	def process(self, filepattern, otf, indir=None, binary=None, **opts):
		if binary is None:
			binary = CUDAbin()

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

	def get_otfs(self, otfpath=config.__OTFPATH__):
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
				otf = get_otf_by_date(self.date, wave, (innerNA, outerNA),
					otfpath=otfpath, direction='nearest')
			else:
				otf = str(os.path.join(otfpath, str(wave) + '_otf.tif'))
			otfs[c] = otf
		return otfs

	def get_feature_width(self, **kwargs):
		# defaults background=100, pad=100, sigma=2
		w = {}
		w.update(arrayfun.feature_width(self, **kwargs))
		# self.parameters.content_width = w['width']
		# self.parameters.content_offset = w['offset']
		# self.parameters.deskewed_nx = w['newX']
		return w

	# TODO: should calculate background of provided folder (e.g. Corrected)
	def get_background(self, **kwargs):
		if not self.has_lls_tiffs:
			warnings.warn('Cannot calculate background on folder with no Tiffs')
			return
		# defaults background and=100, pad=100, sigma=2
		bgrd = []
		for c in range(self.parameters.nc):
			i = util.imread(self.get_files(t=0, c=c)).squeeze()
			bgrd.append(arrayfun.detect_background(i))
		# self.parameters.background = bgrd
		return bgrd

	def correct_flash(self, trange=None, camparams=None, target='parallel', median=False):
		""" where trange is an iterable of timepoints

		"""
		if not self.has_settings:
			raise LLSpyError('Cannot correct flash pixels without settings.txt file')
		if not isinstance(camparams, CameraParameters):
			if isinstance(camparams, str):
				camparams = CameraParameters(camparams)
			else:
				camparams = CameraParameters()

		if not np.all(camparams.roi == self.settings.camera.roi):
			try:
				camparams = camparams.get_subroi(self.settings.camera.roi)
			except Exception:
				raise ValueError('ROI in parameters doesn not match data ROI')

		outpath = self.path.joinpath('Corrected')
		if not outpath.is_dir():
			outpath.mkdir()

		if trange is not None:
			timegroups = [self.get_t(t) for t in trange]
		else:
			timegroups = [self.get_t(t) for t in range(self.parameters.nt)]

		# FIXME: this is a temporary bug fix to correct for the fact that
		# LLSdirs acquired in script editor (Iter_0, etc...) don't correctly
		# detect the number of timepoints
		timegroups = [t for t in timegroups if len(t)]

		if target == 'parallel':
			# numthreads = cpu_count()
			# procs = []
			# for t in timegroups:
			# 	args = (t, camparams, outpath, median)
			# 	procs.append(Process(target=correctTimepoint, args=args))
			# while len(procs):
			# 	proccessGroup = procs[0:numthreads]
			# 	procs[0:numthreads] = []
			# 	[p.start() for p in proccessGroup]
			# 	[p.join() for p in proccessGroup]

			pool = Pool(processes=cpu_count())
			g = [(t, camparams, outpath, median) for t in timegroups]
			pool.map(unwrapper, g)

		elif target == 'cpu':
			for t in timegroups:
				correctTimepoint(t, camparams, outpath, median)
		elif target == 'cuda' or target == 'gpu':
			camparams.init_CUDAcamcor((self.parameters.nz*self.parameters.nc,
				self.parameters.ny, self.parameters.nx))
			for t in timegroups:
				correctTimepoint(t, camparams, outpath, median, target='cuda')
		else:
			for t in timegroups:
				correctTimepoint(t, camparams, outpath, median,  target='cpu')
		return LLSdir(outpath)

	def register(self, regRefWave, regMode, regCalibDir):
		if self.parameters.nc < 2:
			warnings.warn('Cannot register single channel dataset')
			return
		RD = RegDir(regCalibDir)
		if not RD.isValid:
			warnings.warn('Registration Calibration dir not valid: {}'.format(regCalibDir))
			return
		RD.cloudset()  # optional, intialized the cloud...

		subdirs = [x for x in self.path.iterdir() if x.is_dir() and
					x.name in ('GPUdecon', 'Deskewed')]
		for D in subdirs:
			files = [fn for fn in D.glob('*.tif') if not ('_REG' in fn.name or
				str(regRefWave) in fn.name)]
			for F in files:
				outname = str(F).replace('.tif', '_REG.tif')
				im = RD.register_image_to_wave(str(F), refwave=regRefWave, mode=regMode)
				util.imsave(util.reorderstack(np.squeeze(im), 'zyx'),
					str(D.joinpath(outname)),
					dx=self.parameters.dx, dz=self.parameters.dzFinal)

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


# TODO: cache cloud result after reading files and filtering once
class RegDir(LLSdir):
	"""Special type of LLSdir that holds image registraion data like
	tetraspeck beads
	"""

	def __init__(self, path, t=0, **kwargs):
		super(RegDir, self).__init__(path, **kwargs)
		if self.path is not None:
			if self.path.joinpath('cloud.json').is_file():
				with open(self.path.joinpath('cloud.json')) as json_data:
					self = self.fromJSON(json.load(json_data))
		self.t = t
		if self.isValid:
			self.data = self.getdata()
			self.waves = [parse.parse_filename(f, 'wave') for f in self.get_t(t)]
			self.channels = [parse.parse_filename(f, 'channel') for f in self.get_t(t)]
			self.deskew = self.parameters.samplescan

	@property
	def isValid(self):
		return bool(len(self.get_t(self.t)))

	def getdata(self):
		return [util.imread(f) for f in self.get_t(self.t)]

	def has_data(self):
		return all([isinstance(a, np.ndarray) for a in self.data])

	def toJSON(self):
		D = self.__dict__.copy()
		D['_cloudset'] = self._cloudset.toJSON()
		D['path'] = str(self.path)
		# FIXME: make LLSsettings object serializeable
		D.pop('settings', None)
		# D['settings']['camera']['roi'] = self.settings.camera.roi.tolist()
		# D['settings']['date'] = self.settings.date.isoformat()
		D['date'] = self.date.isoformat()
		D.pop('data', None)
		D.pop('deskewed', None)
		return json.dumps(D)

	def fromJSON(self, Jstring):
		D = json.loads(Jstring)
		for k, v in D.items():
			setattr(self, k, v)
		super(RegDir, self).__init__(D['path'])
		self._cloudset = CloudSet().fromJSON(D['_cloudset'])
		return self

	def _deskewed(self, dz=None, dx=None, angle=None):
		if 'deskewed' in dir(self):
			return self.deskewed
		else:
			dx = dx if dx else self.parameters.dx
			dz = dz if dz else self.parameters.dz
			angle = angle if angle else self.parameters.angle
			if (not dx) or (not dz) or (not angle):
				raise ValueError('Cannot deskew without dx, dz & angle')

			self.deskewed = [deskewGPU(i, dz, dx, angle) for i in self.data]
			return self.deskewed

	def cloudset(self, redo=False):
		""" actually generates the fiducial cloud """
		if '_cloudset' in dir(self) and not redo:
			return self._cloudset
		self._cloudset = CloudSet(self._deskewed() if self.deskew else self.data, labels=self.waves)
		with open(self.path.joinpath('cloud.json'), 'w') as outfile:
			json.dump(self.toJSON(), outfile)
		return self._cloudset

	def cloudset_has_data(self):
		return self.cloudset().has_data()

	def reload_data(self):
		self.cloudset(redo=True)

	def get_tform(self, movingWave, refWave=488, mode='2step'):
		return self.cloudset().tform(movingWave, refWave, mode)

	def register_image_to_wave(self, img, imwave=None, refwave=488, mode='2step'):
		if isinstance(img, np.ndarray):
			if imwave is None:
				raise ValueError('Must provide wavelength when providing array '
					'for registration.')
		elif isinstance(img, str) and os.path.isfile(img):
			if imwave is None:
				try:
					imwave = parse.parse_filename(img, 'wave')
				except Exception:
					pass
				if not imwave:
					raise ValueError('Could not detect image wavelength.')
			img = util.imread(img)
		else:
			raise ValueError('Input to Registration must either be a np.array '
				'or a path to a tif file')

		return affineGPU(img, self.get_tform(imwave, refwave, mode))


def rename_iters(folder, splitpositions=True, verbose=False):
	"""
	Rename files in a folder acquired with LLS multi-position script.

	Assumes every time points is labeled Iter_n.

	This assumes that each position was acquired every iteration
	and that only a single scan is performed per position per iteration
	(i.e. it assumes that everything is a "stack0000")

	example, filename (if it's the second position in a scipted FOR loop):
		filename_Iter_2_ch1_stack0000_560nm_0000000msec_0006443235msecAbs.tif
	gets changes to:
		filename_pos01_ch1_stack0002_560nm_0023480msec_0006443235msecAbs.tif

	if splitpositions==True:
		files from different positions will be placed into subdirectories
	"""
	import re

	filelist = glob.glob(os.path.join(folder, '*Iter*stack*'))
	nPositions = 0
	if filelist:
		nIters = max([int(f.split('Iter_')[1].split('_')[0]) for f in filelist]) + 1
		nChan = 0
		while True:
			if any(['ch' + str(nChan) in f for f in filelist]):
				nChan += 1
			else:
				break
		nPositions = len(filelist) // (nChan * nIters)

		setlist = glob.glob(os.path.join(folder, '*Iter*Settings.txt'))
		for pos in range(nPositions):
			settingsFile = [f for f in setlist
							if 'Settings.txt' in f and 'Iter_%s' % pos in f][0]
			if nPositions > 1:
				newname = re.sub(r"Iter_\d+", 'pos%02d' % pos,
								os.path.basename(settingsFile))
			else:
				newname = re.sub(r"_Iter_\d+", '',
								os.path.basename(settingsFile))
			os.rename(settingsFile, os.path.join(folder, newname))
		for chan in range(nChan):
			t0 = []
			for i in range(nIters):
				flist = sorted([f for f in filelist
							if 'ch%s' % chan in f and 'Iter_%s_' % i in f])
				for pos in range(nPositions):
					base = os.path.basename(flist[pos])
					if i == 0:
						t0.append(int(base.split('msecAbs')[0].split('_')[-1]))
					newname = base.replace('stack0000', 'stack%04d' % i)
					deltaT = int(base.split('msecAbs')[0].split('_')[-1]) - t0[pos]
					newname = newname.replace('0000000msec_', '%07dmsec_' % deltaT)
					if nPositions > 1:
						newname = re.sub(r"Iter_\d+", 'pos%02d' % pos, newname)
					else:
						newname = re.sub(r"_Iter_\d+", '', newname)
					if verbose:
						print("{} --> {}".format(base, newname))
					os.rename(flist[pos], os.path.join(folder, newname))
	if splitpositions and nPositions > 1:
		# files from different positions will be placed into subdirectories
		pos = 0
		while True:
			movelist = glob.glob(os.path.join(folder, '*pos%02d*' % pos))
			if not len(movelist):
					break
			basename = os.path.basename(movelist[0]).split('_pos')[0]
			posfolder = os.path.join(folder, basename + '_pos%02d' % pos)
			if not os.path.exists(posfolder):
					os.mkdir(posfolder)
			for f in movelist:
				os.rename(f, os.path.join(posfolder, os.path.basename(f)))
			pos += 1


def concatenate_folders(folderlist, raw=True, decon=True, deskew=True):
	"""combine a list of folders into a single LLS folder.

	renames stack numbers and relative timestamp in filenames
	to concatenate folders as if they were taken in a single longer timelapse
	useful when an experiment was stopped and restarted
	(for instance, to change the offset)
	"""

	# get timestamp of stack0000 for all folders
	stackzeros = []
	for folder in folderlist:
		try:
			firstfile = glob.glob(os.path.join(folder, '*ch0*stack0000*'))[0]
			basename = os.path.basename(firstfile).split('_ch0')[0]
			stackzeros.append([folder, firstfile, basename])
		except Exception:
			pass
	# sort by absolute timestamp
	tzeros = sorted([[int(t[1].split('msecAbs')[0].split('_')[-1]), t[0], t[2]]
					for t in stackzeros])

	# get relative time offset
	for t in tzeros:
		t.append(t[0] - tzeros[0][0])
		# example tzeros
		# [[23742190, '/top_folder/cell4', 'cell4', 0],
		#  [24583591, '/top_folder/cell4b', 'cell4b', 841401],
		#  [24610148, '/top_folder/cell4e', 'cell4e', 867958],
		#  [24901726, '/top_folder/cell4d', 'cell4d',1159536]]
	t0path = tzeros[0][1]
	basename = tzeros[0][2]

	channelcounts = [0] * 6
	for fi in sorted(os.listdir(t0path)):
		if fi.endswith('.tif'):
			chan = int(fi.split('_ch')[1].split('_')[0])
			channelcounts[chan] += 1
	tzeros[0].append(list(channelcounts))

	for t in tzeros[1:]:
		filelist = sorted(os.listdir(t[1]))
		tbase = t[2]
		deltaT = t[3]
		thisfoldercounts = [0] * 6
		for fi in filelist:
			if fi.endswith('.tif'):
				chan = int(fi.split('_ch')[1].split('_')[0])
				reltime = int(fi.split('msec_')[0].split('_')[-1])
				# change relative timestamp
				newname = re.sub(
					r"\d+msec_", '%07dmsec_' % int(reltime + deltaT), fi)
				newname = newname.replace(tbase, basename)
				# change stack number
				newname = re.sub(
					r"_stack\d+", '_stack%04d' % channelcounts[chan], newname)
				os.rename(os.path.join(t[1], fi), os.path.join(t0path, newname))
				channelcounts[chan] += 1
				thisfoldercounts[chan] += 1
			else:
				os.rename(os.path.join(t[1], fi), os.path.join(t0path, fi))
		t.append(thisfoldercounts)
		os.rmdir(t[1])

	with open(os.path.join(t0path, 'concatenationRecord.txt'), 'w') as outfile:
		json.dump(tzeros, outfile)


class LLSpyError(Exception):
	"""
	Generic exception indicating anything relating to the execution
	of LLSpy. A string containing an error message should be supplied
	when raising this exception.
	"""
	pass
