from llspy.config import config
from llspy.core.cudabinwrapper import CUDAbin

import re
import warnings
import numpy as np
from datetime import datetime, timedelta


psffile_pattern = re.compile(r"""
	^(?P<date>\d{8})
	_(?P<wave>\d{3})
	_(?P<psftype>[a-zA-Z_]*)
	(?P<outerNA>[0-9p]+)
	-(?P<innerNA>[0-9p]+)
	(?P<isotf>_otf)?.tif$""", re.VERBOSE)


default_otf_pattern = re.compile(r"""
	^(?P<wave>\d{3})
	(_otf.tif|.otf)$""", re.VERBOSE)


def get_otf_dict(otfdir):
	otf_dict = {}
	for t in list(otfdir.glob('*tif')):
		M = psffile_pattern.search(str(t.name))
		if M:
			M = M.groupdict()
			wave = int(M['wave'])
			if wave not in otf_dict:
				otf_dict[wave] = {'default': None}
			mask = (float(M['innerNA'].replace('p', '.')),
					float(M['outerNA'].replace('p', '.')))
			if mask not in otf_dict[wave]:
				otf_dict[wave][mask] = []
			if not M['isotf']:
				matching_otf = otfdir.joinpath(
					t.name.replace('.tif', '_otf.tif'))
				if not matching_otf.is_file():
					matching_otf = None
				else:
					matching_otf = None
			otf_dict[wave][mask].append({
				'date': datetime.strptime(M['date'], '%Y%m%d'),
				'path': str(t),
				'form': 'otf' if M['isotf'] else 'psf',
				'type': M['psftype'],
				'otf': str(matching_otf)
			})
		else:
			M = default_otf_pattern.search(str(t.name))
			if M:
				M = M.groupdict()
				wave = int(M['wave'])
				if wave not in otf_dict:
					otf_dict[wave] = {}
				otf_dict[wave]['default'] = str(t)
	return otf_dict


def get_otf_by_date(date, wave, mask=None, otfpath=config.__OTFPATH__, direction='nearest'):
	"""return otf with date closest to requested date.
	if OTF doesn't exist, but PSF does, generate OTF and return the path.i
	direction can be {'nearest', 'before', 'after'}, where 'before' returns an
	OTF that was collected before 'date' and 'after' returns one that was
	collected after 'date.'
	"""
	otf_dict = get_otf_dict(otfpath)
	otflist = []
	if wave not in otf_dict:
		raise KeyError('Wave: {} not in otfdict: \n{}'.format(wave, otf_dict))
	if mask is not None:
		if mask in otf_dict[wave]:
			otflist = otf_dict[wave][mask]
	else:
		keys = list(otf_dict[wave].keys())
		for k in keys:
			if k != 'default':
				[otflist.append(i) for i in otf_dict[wave][k]]

	if not otflist:
		return otf_dict[wave]['default']

	if direction == 'nearest':
		minIdx = np.argmin([np.abs(i['date'] - date) for i in otflist])
	elif direction == 'before':
		deltas = [date - i['date'] for i in otflist]
		test = [d > timedelta(minutes=0) for d in deltas]
		minIdx = next((obj for obj in test if obj), None)
	elif direction == 'after':
		deltas = [i['date'] - date for i in otflist]
		test = [d > timedelta(minutes=0) for d in deltas]
		minIdx = next((obj for obj in test if obj), None)
	else:
		raise ValueError('Unkown direction argument: {}'.format(direction))

	if minIdx is None:
		return otf_dict[wave]['default']

	matching_otfs = [i for i in otflist
		if i['date'] == otflist[minIdx]['date'] and i['form'] == 'otf']
	if len(matching_otfs):
		return matching_otfs[0]['path']
	else:
		matching_psfs = [i for i in otflist
			if i['date'] == otflist[minIdx]['date'] and i['form'] == 'psf']
		if matching_psfs:
			# generate new OTF from PSF
			otfbin = OTFbin()
			return otfbin.process(matching_psfs[0]['path'])


class OTFbin(CUDAbin):
	"""docstring for MakeOTF"""

	def __init__(self, binPath=config.__RADIALFT__):
		super(OTFbin, self).__init__(binPath)

	def process(self, inpath, **options):
		cmd = [self.path]
		outfile = inpath.replace('.tif', '_otf.tif')
		options.update({
			'input-file': inpath,
			'output-file': outfile,
			'fixorigin': '10',
			'nocleanup': True,
		})
		for o in options:
			if self.has_option('--' + o):
				if isinstance(options[o], bool):
					cmd.extend(['--' + o])
				else:
					cmd.extend(['--' + o, str(options[o])])
			else:
				warnings.warn('Warning: option not recognized, ignoring: {}'.format(o))
		if self._run_command(cmd):
			return outfile
