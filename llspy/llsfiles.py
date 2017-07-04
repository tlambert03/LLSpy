from __future__ import division, print_function

from llspy import util
from llspy import camera
from llspy.cudabinwrapper import CUDAbin

import os
import re
import io
import configparser
import warnings
import numpy as np
from datetime import datetime
from tifffile import TiffFile, imread, imsave

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


# ############### Patterns and regex constants ####################

# declare the filename template... could go in config file
DELIM = '_'
FNAME_TEMP = ('{basename}' +
					DELIM + 'ch{channel}' +
					DELIM + 'stack{stack:04d}' +
					DELIM + '{wave}nm' +  # FIXME this depends on the AOTF name
					DELIM + '{reltime:07d}msec' +
					DELIM + '{abstime:010d}msecAbs.tif')

# repating pattern definitions used for parsing settings file
numstack_pattern = re.compile(r"""
	\#\sof\sstacks\s\((?P<channel>\d)\) # channel number inside parentheses
	\s:\s+(?P<numstacks_requested>\d+)	# number of stacks after the colon
	""", re.MULTILINE | re.VERBOSE)

waveform_pattern = re.compile(r"""
	^(?P<waveform>.*)\sOffset,	# Waveform type, newline followed by description
	.*\((?P<channel>\d+)\)\s	# get channel number inside of parentheses
	:\s*(?P<offset>\d*\.?\d*)	# float offset value after colon
	\s*(?P<interval>\d*\.?\d*)	# float interval value next
	\s*(?P<numpix>\d+)			# integer number of pixels last
	""", re.MULTILINE | re.VERBOSE)

excitation_pattern = re.compile(r"""
	Excitation\sFilter,\s+Laser,	# Waveform type, newline followed by description
	.*\((?P<channel>\d+)\)\s	# get channel number inside of parentheses
	:\s+(?P<exfilter>[^\s]*)		# excitation filter: anything but whitespace
	\s+(?P<laser>\d+)			# integer laser line
	\s+(?P<power>\d*\.?\d*)		# float laser power value next
	\s+(?P<exposure>\d*\.?\d*)  # float exposure time last
	""", re.MULTILINE | re.VERBOSE)

PIXEL_SIZE = {
	'C11440-22C': 6.5,
	'C11440': 6.5,
}


# cleaner warnings printed to console
def custom_formatwarning(msg, *a, **k):
	# ignore everything except the message
	return str(msg) + '\n'

warnings.formatwarning = custom_formatwarning


# ####################### Filename manipulation ##########################

# 'cell5_ch1_stack0102_560nm_0001760msec_0020933033msecAbs.tif'
# {name}_ch{channel:1}_stack{stack:4}_{wave:3}nm_{reltime:7}msec_{abstime:10}msecAbs
filename_pattern = re.compile(r"""
	^(?P<basename>\w+)
	_ch(?P<channel>\d)
	_stack(?P<stack>\d{4})
	_(?P<wave>\d{3})nm
	_(?P<reltime>\d{7})msec
	_(?P<abstime>\d{10})msecAbs
	""", re.VERBOSE)


def parse_filename(fname, matchword=None, pattern=filename_pattern):
	fname = os.path.basename(fname)
	gd = pattern.search(fname).groupdict()
	gd = {k: (int(v) if v.isdigit() else v) for k, v in gd.items()}
	if matchword in gd:
		return gd[matchword]
	else:
		return gd


def gen_filename(d, template=FNAME_TEMP):
	''' generate filename from dict with file attributes.

	using dicts like this
	o = {
		'basename': 'cell5',
		'channel': 0,
		'stack': 4,
		'wave': '488',
		'reltime': 4932,
		'abstime': 12324,
	}
	'''
	return template.format(**d)


def clean_string(varStr):
	''' sanitize string for use as a variable name'''
	return re.sub('_+', '_', re.sub('\W|^(?=\d)', '_', varStr))


# ################### File list filtering functions ###################

def filter_t(filelist, trange):
	''' return a list of filenames whose stack numbers are within trange
	trange is either a single int, or an iterator with a range of stack
	numbers desired
	'''
	# f = [f for f in filelist if parse_filename(f).named['stack'] == t]
	# above is more robust... this is 100x faster
	try:
		iterator = iter(trange)
	except TypeError:
		iterator = [trange]
	q = []
	for t in iterator:
		q.extend(
			[f for f in filelist if '_stack{:04d}_'.format(t) in f])
	return q


def filter_c(filelist, channels):
	''' return a list of filenames whose channel numbers are within trange
	channels is either a single int, or an iterator with a range of channel
	numbers desired
	'''
	# f = [f for f in filelist if parse_filename(f,'channel') == c]
	# above is more robust... this is faster
	try:
		iterator = iter(channels)
	except TypeError:
		iterator = [channels]
	q = []
	for c in iterator:
		q.extend(
			[f for f in filelist if '_ch{}_'.format(c) in f])
	return q


def filter_w(filelist, w):
	# f = [f for f in filelist if parse_filename(f, 'wave') == w]
	# above is more robust... this is faster
	# FIXME: this depends very much on the user's AOTF naming convention
	if str(w).endswith('nm'):
		w = str(w).strip('nm')
	f = [f for f in filelist if '_{}nm_'.format(w) in f]
	return f


def filter_reltime(filelist, trange):
	''' return a list of filenames whose relative timepoints are within trange
	trange is a tuple of (min, max) relative time in the experiment
	'''
	# f = [f for f in filelist if parse_filename(f, 'wave') == w]
	# above is more robust... this is faster
	if not len(trange) == 2:
		raise ValueError('relative time range must be a 2x tuple of min/max')
	q = []
	for f in filelist:
		if (parse_filename(f, 'reltime') >= trange[0] and
			parse_filename(f, 'reltime') <= trange[1]):
			q.append(f)
	return q


def filter_files(filelist, **kwargs):
	''' Convenience function to filter a list of filenames according to
	stack number, channel number, wavelength name, relative time

	accepted arguments:
		t -> filter_t,
		time -> filter_t,
		s -> filter_t,
		stacks -> filter_t,
		timepoints -> filter_t,
		c -> filter_c,
		channel -> filter_c,
		channels -> filter_c,
		w -> filter_w,
		wave -> filter_w,
		waves -> filter_w,
		wavelengths -> filter_w,
		reltime -> filter_reltime,
		relative time -> filter_reltime,

	'''
	funcdict = {
		't': filter_t,
		'time': filter_t,
		's': filter_t,
		'stacks': filter_t,
		'timepoints': filter_t,
		'c': filter_c,
		'channel': filter_c,
		'channels': filter_c,
		'w': filter_w,
		'wave': filter_w,
		'waves': filter_w,
		'wavelengths': filter_w,
		'reltime': filter_reltime,
		'relative time': filter_reltime,
	}

	for k in kwargs:
		if k not in funcdict:
			raise AttributeError('Did not recognize filter argument: {}'.format(k))
		filelist = funcdict[k](filelist, kwargs[k])
	return filelist

# ################### otf files ###################

# 20170210_488_totPSF_mb0p5-0p42.tif

# 'cell5_ch1_stack0102_560nm_0001760msec_0020933033msecAbs.tif'
# {name}_ch{channel:1}_stack{stack:4}_{wave:3}nm_{reltime:7}msec_{abstime:10}msecAbs
psffile_pattern = re.compile(r"""
	^(?P<date>\d{8})
	_(?P<wave>\d{3})
	_(?P<psftype>[a-zA-Z_]*)
	(?P<innerNA>[0-9p]+)
	-(?P<outerNA>[0-9p]+)
	.tif$""", re.VERBOSE)


def check_otf_dir(dirname):
	dirname = plib.Path(dirname)



# ################### File moving/merging/deleting ###################



# ################### Class defs ###################


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
		self.get_all_tiffs()
		self.ditch_partial_tiffs()
		self.count_tiffs()
		self.get_volume_shape()

	def has_been_processed(self):
		return len([s for s in self.path.glob('*ProcessingLog.txt')])

	def raw_is_compressed(self):
		return len([s for s in self.path.glob('*.bz2')])

	def get_all_tiffs(self):
		'''a list of every tiff file in the top level folder (all raw tiffs)'''
		all_tiffs = sorted(self.path.glob('*.tif'))
		if not all_tiffs:
			warnings.warn('No Tiff files detected in folder')
		self.nFiles = len(all_tiffs)
		# self.bytes can be used to get size of raw data: np.sum(self.bytes)
		self.bytes = [f.stat().st_size for f in all_tiffs]
		self.all_tiffs = [str(f) for f in all_tiffs]

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
				self.wavelength.append(parse_filename(str(q[0]), 'wave'))
				if len(q) > 1:
					self.interval.append(
						parse_filename(str(q[1]), 'reltime') / 1000)
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
		if indir is None:
			indir = self.path
		opts = self._get_cudaDeconv_options()
		#otf = default_otfs[str(488)]
		output = binary.process(indir, filepattern, otf, **opts)
		return output

	def get_t(self, t):
		return filter_t(self.raw, t)

	def get_c(self, c):
		return filter_c(self.raw, c)

	def get_w(self, w):
		return filter_w(self.raw, w)

	def get_reltime(self, rt):
		return filter_reltime(self.raw, rt)

	def get_files(self, **kwargs):
		return filter_files(self.raw, **kwargs)

	def correct_flash(self, camparams=None, target='parallel', median=True):
		if camparams is None:
			camparams=camera.CameraParameters()
		dataroi = camera.CameraROI(self.settings.camera.roi)
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
		from pprint import pformat
		out = {
			'raw data size': util.format_size(np.mean(self.bytes))
		}
		for k, v in self.__dict__.items():
			if k not in {'all_tiffs', 'date', 'settings_files'}:
				out.update({k: v})
		return pformat(out)


class LLSsettings(object):
	'''Class for parsing and storing info from LLS Settings.txt.'''

	def __init__(self, fname):
		self.path = fname
		self.basename = os.path.basename(fname)
		if self.read():
			self.parse()

	def printDate(self):
		print(self.date.strftime('%x %X %p'))

	def read(self):
		# io.open grants py2/3 compatibility
		try:
			with io.open(self.path, 'r', encoding='utf-8') as f:
				self.raw_text = f.read()
			return 1
		except Exception:
			return 0

	def __repr__(self):
		from pprint import pformat
		sb = {k: v for k, v in self.__dict__.items() if not k in {'raw_text','SPIMproject'}}
		return pformat(sb)

	def parse(self):
		'''parse the settings file.'''

		# the settings file is seperated into sections by "*****"
		settingsSplit = re.split('[*]{5}.*\n', self.raw_text)
		general_settings = settingsSplit[1]
		waveform_settings = settingsSplit[2]	 # the top part with the experiment
		camera_settings = settingsSplit[3]
		# timing_settings = settingsSplit[4]
		ini_settings = settingsSplit[5]	 # the bottom .ini part

		# parse the top part (general settings)
		datestring = re.search('Date\s*:\s*(.*)\n', general_settings).group(1)
		self.date = datetime.strptime(datestring, '%m/%d/%Y %I:%M:%S %p')
		# print that with dateobject.strftime('%x %X %p')

		self.acq_mode = re.search(
			'Acq Mode\s*:\s*(.*)\n', general_settings).group(1)
		self.software_version = re.search(
			'Version\s*:\s*v ([\d*.?]+)', general_settings).group(1)
		self.cycle_lasers = re.search(
			'Cycle lasers\s*:\s*(.*)\n', waveform_settings).group(1)
		self.z_motion = re.search(
			'Z motion\s*:\s*(.*)\n', waveform_settings).group(1)

		# find repating patterns in settings file
		waveforms = [
			m.groupdict() for m in waveform_pattern.finditer(waveform_settings)]
		excitations = [
			m.groupdict() for m in excitation_pattern.finditer(waveform_settings)]
		numstacks = [
			m.groupdict() for m in numstack_pattern.finditer(waveform_settings)]

		# organize into channel dict
		self.channel = {}
		for item in waveforms:
			cnum = int(item.pop('channel'))
			if cnum not in self.channel:
				self.channel[cnum] = util.dotdict()
			wavename = item.pop('waveform')
			self.channel[cnum][wavename] = item
		for L in [excitations, numstacks]:
			for item in L:
				cnum = int(item.pop('channel'))
				if cnum not in self.channel:
					self.channel[cnum] = {}
				self.channel[cnum].update(item)
		del excitations
		del numstacks
		del waveforms

		# parse the camera part
		config = configparser.ConfigParser(strict=False)
		config.read_string('[Camera Settings]\n' + camera_settings)
		# self.camera = config[config.sections()[0]]
		config = config[config.sections()[0]]
		self.camera = util.dotdict()
		self.camera.model = config.get('model')
		self.camera.serial = config.get('serial')
		self.camera.exp = config.get('exp(s)')
		self.camera.cycle = config.get('cycle(s)')
		self.camera.cycleHz = config.get('cycle(hz)')
		self.camera.roi = [int(i) for i in re.findall(
			r'\d+', config.get('roi'))]
		self.camera.pixel = PIXEL_SIZE[self.camera.model.split('-')[0]]

		# parse the timing part
		# config = configparser.ConfigParser(strict=False)
		# config.read_string('[Timing Settings]\n' + timing_settings)
		# self.timing = config[config.sections()[0]]

		# parse the ini part
		config = configparser.ConfigParser(strict=False)
		config.optionxform = str 	# leave case in keys
		config.read_string(ini_settings)
		self.SPIMproject = config
		# read it (for example)
		# config.getfloat('Sample stage',
		# 				'Angle between stage and bessel beam (deg)')
		self.sheet_angle = self.SPIMproject.getfloat(
			'Sample stage', 'Angle between stage and bessel beam (deg)')
		self.mag = self.SPIMproject.getfloat(
			'Detection optics', 'Magnification')
		self.camera.name = self.SPIMproject.get('General', 'Camera type')
		self.camera.trigger_mode = self.SPIMproject.get(
			'General', 'Cam Trigger mode')
		self.pixel_size = round(self.camera.pixel / self.mag, 4)

		# not everyone will have added Annular mask to their settings ini
		for n in ['Mask', 'Annular Mask', 'Annulus']:
			if self.SPIMproject.has_section(n):
				self.mask = util.dotdict()
				for k, v in self.SPIMproject['Annular Mask'].items():
					self.mask[k] = float(v)

	def write(self, outpath):
		with open(outpath, 'w') as outfile:
			outfile.write(self.raw_text)

	def write_ini(self, outpath):
		with open(outpath, 'w') as outfile:
			self.SPIMproject.write(outfile)
