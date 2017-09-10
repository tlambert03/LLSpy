from . import util
from . import camera
import os
import re
import io
import configparser
import warnings
import math

from datetime import datetime


# repating pattern definitions used for parsing settings file
numstack_pattern = re.compile(r"""
	\#\sof\sstacks\s\((?P<channel>\d)\) # channel number inside parentheses
	\s:\s+(?P<numstacks_requested>\d+)	# number of stacks after the colon
	""", re.MULTILINE | re.VERBOSE)

waveform_pattern = re.compile(r"""
	^(?P<waveform>.*)\sOffset,	# Waveform type, newline followed by description
	.*\((?P<channel>\d+)\)\s	# get channel number inside of parentheses
	:\s*(?P<offset>[-\d]*\.?\d*)	# float offset value after colon
	\s*(?P<interval>[-\d]*\.?\d*)	# float interval value next
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


class LLSsettings(object):
	'''Class for parsing and storing info from LLS Settings.txt.'''

	def __init__(self, fname):
		self.path = os.path.abspath(fname)
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
		except IOError:
			warnings.warn('Settings file not found at {}'.format(self.path))
			return 0
		except Exception:
			return 0

	def __repr__(self):
		from pprint import pformat
		sb = {k: v for k, v in self.__dict__.items() if k not in {'raw_text', 'SPIMproject'}}
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
		cp = configparser.ConfigParser(strict=False)
		cp.read_string('[Camera Settings]\n' + camera_settings)
		# self.camera = cp[cp.sections()[0]]
		cp = cp[cp.sections()[0]]
		self.camera = util.dotdict()
		self.camera.model = cp.get('model')
		self.camera.serial = cp.get('serial')
		self.camera.exp = cp.get('exp(s)')
		self.camera.cycle = cp.get('cycle(s)')
		self.camera.cycleHz = cp.get('cycle(hz)')
		self.camera.roi = camera.CameraROI([int(i) for i in re.findall(
			r'\d+', cp.get('roi'))])
		self.camera.pixel = PIXEL_SIZE[self.camera.model.split('-')[0]]

		# parse the timing part
		# cp = configparser.ConfigParser(strict=False)
		# cp.read_string('[Timing Settings]\n' + timing_settings)
		# self.timing = cp[cp.sections()[0]]

		# parse the ini part
		cp = configparser.ConfigParser(strict=False)
		cp.optionxform = str 	# leave case in keys
		cp.read_string(ini_settings)
		self.SPIMproject = cp
		# read it (for example)
		# cp.getfloat('Sample stage',
		# 				'Angle between stage and bessel beam (deg)')
		self.sheet_angle = self.SPIMproject.getfloat(
			'Sample stage', 'Angle between stage and bessel beam (deg)')
		self.mag = self.SPIMproject.getfloat(
			'Detection optics', 'Magnification')
		self.camera.name = self.SPIMproject.get('General', 'Camera type')
		self.camera.trigger_mode = self.SPIMproject.get(
			'General', 'Cam Trigger mode')
		self.camera.twincam = self.SPIMproject.get(
			'General', 'Twin cam mode?') in ['TRUE', 'True', 1, 'YES', 'Yes']
		self.camera.cam2name = self.SPIMproject.get(
			'General', '2nd Camera type')
		self.pixel_size = round(self.camera.pixel / self.mag, 4)

		# not everyone will have added Annular mask to their settings ini
		for n in ['Mask', 'Annular Mask', 'Annulus']:
			if self.SPIMproject.has_section(n):
				self.mask = util.dotdict()
				for k, v in self.SPIMproject['Annular Mask'].items():
					self.mask[k] = float(v)

		# these will be overriden by the LLSDir file detection, but write anyway

		self.parameters = util.dotdict()
		self.parameters.update({
			'dx': self.pixel_size,
			'z_motion': self.z_motion,
			'samplescan': bool(self.z_motion == 'Sample piezo'),
			'angle': self.sheet_angle,
			'nc': len(self.channel),
			'nt': int(self.channel[0]['numstacks_requested']),
			'nx': self.camera.roi.height,  # camera is usually rotated 90deg
			'ny': self.camera.roi.width,  # camera is usually rotated 90deg
			'wavelength': [int(v['laser']) for k, v in self.channel.items()]
		})
		if self.parameters.samplescan:
			self.parameters.dz = abs(float(self.channel[0]['S PZT']['interval']))
			self.parameters.nz = int(self.channel[0]['S PZT']['numpix'])
			self.parameters.dzFinal = self.parameters.dz * math.sin(
										self.sheet_angle * math.pi / 180)
		else:
			self.parameters.dz = abs(float(self.channel[0]['Z PZT']['interval']))
			self.parameters.nz = int(self.channel[0]['Z PZT']['numpix'])
			self.parameters.dzFinal = self.parameters.dz

	def write(self, outpath):
		with open(outpath, 'w') as outfile:
			outfile.write(self.raw_text)

	def write_ini(self, outpath):
		with open(outpath, 'w') as outfile:
			self.SPIMproject.write(outfile)
