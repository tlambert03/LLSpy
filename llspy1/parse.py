from __future__ import division, print_function

import os
import re
import warnings
import parse


# ############### Patterns and regex constants ####################

# declare the filename template... could go in config file
# this only is used for generating filenames (gen_filename)...
# which isn't really used
# example: cell5_ch0_stack0000_488nm_0000000msec_0020931273msecAbs.tif
DELIM = '_'
FNAME_TEMPLATE = ('{basename}' +
					DELIM + 'ch{channel}' +
					DELIM + 'stack{stack:04d}' +
					DELIM + '{wave}nm' +  # FIXME this depends on the AOTF name
					DELIM + '{reltime:07d}msec' +
					DELIM + '{abstime:010d}msecAbs.tif')


# cleaner warnings printed to console
def custom_formatwarning(msg, *a, **k):
	# ignore everything except the message
	return str(msg) + '\n'


warnings.formatwarning = custom_formatwarning

# ####################### Filename manipulation ##########################

# 'cell5_ch1_stack0102_560nm_0001760msec_0020933033msecAbs.tif'
# {name}_ch{channel:1}_stack{stack:4}_{wave:3}nm_{reltime:7}msec_{abstime:10}msecAbs
filename_pattern = re.compile(r"""
	^(?P<basename>.+)			# any characters before _ch are basename
	_ch(?P<channel>\d)			# channel is a single digit following _ch
	_stack(?P<stack>\d{4})		# timepoint is 4 digits following _stack
	_\D*(?P<wave>\d+).*			# wave = contiguous digits in this section
	_(?P<reltime>\d{7})msec 	# 7 digits after _ and before msec
	_(?P<abstime>\d{10})msecAbs	# 10 digits after _ and before msecAbs
	""", re.VERBOSE)


def contains_LLSfiles(path):
	for item in os.listdir(path):
		if filename_pattern.match(item):
			return True
	return False


def contains_filepattern(path, pattern):
	for item in os.listdir(path):
		if parse.parse(pattern, item):
			return True
	return False


def parse_filename(fname, matchword=None, pattern=None):
	fname = os.path.basename(fname)
	# if not pattern:
	# 	pattern = filename_pattern
	# 	gd = pattern.search(fname)
	# 	if not hasattr(gd, 'groupdict'):
	# 		raise ValueError('Could not parse filename {}'.format(fname))
	# 	gd = gd.groupdict()
	# 	named = {k: (int(v) if (v.isdigit() and k != 'basename') else v) for k, v in gd.items()}
	if not pattern:
		pattern = '{basename}_ch{channel:d}_stack{stack:d}_{wave:d}nm_{reltime:d}msec_{abstime:d}msecAbs{}'
	R = parse.parse(pattern, fname)
	if not (R and hasattr(R, 'named')):
		raise ValueError('Could not parse filename:\n{} with pattern:\n{}'.format(fname, pattern))
	named = R.named
	if matchword in named:
		return named[matchword]
	else:
		return named


def gen_filename(d, template=FNAME_TEMPLATE):
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

def filter_t(filelist, trange, exclusive=False):
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
	if exclusive:
		for t in iterator:
			q.extend(
				[f for f in filelist if '_stack{:04d}_'.format(t) not in f])
	else:
		for t in iterator:
			q.extend(
				[f for f in filelist if '_stack{:04d}_'.format(t) in f])
	return q


def filter_c(filelist, channels, exclusive=False):
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
	if exclusive:
		for c in iterator:
			q.extend(
				[f for f in filelist if '_ch{}_'.format(c) not in f])
	else:
		for c in iterator:
			q.extend(
				[f for f in filelist if '_ch{}_'.format(c) in f])

	return q


# TODO: make this accept an iterator
def filter_w(filelist, w, exclusive=False):
	# f = [f for f in filelist if parse_filename(f, 'wave') == w]
	# above is more robust... this is faster
	# FIXME: this depends very much on the user's AOTF naming convention
	if str(w).endswith('nm'):
		w = str(w).strip('nm')
	if exclusive:
		f = [f for f in filelist if '_{}nm_'.format(w) not in f]
	else:
		f = [f for f in filelist if '_{}nm_'.format(w) in f]
	return f


def filter_reltime(filelist, trange, exclusive=False):
	''' return a list of filenames whose relative timepoints are within trange
	trange is a tuple of (min, max) relative time in the experiment
	'''
	# f = [f for f in filelist if parse_filename(f, 'wave') == w]
	# above is more robust... this is faster
	if not len(trange) == 2:
		raise ValueError('relative time range must be a 2x tuple of min/max')
	q = []
	if exclusive:
		for f in filelist:
			if (parse_filename(f, 'reltime') < trange[0] and
				parse_filename(f, 'reltime') > trange[1]):
				q.append(f)
	else:
		for f in filelist:
			if (parse_filename(f, 'reltime') >= trange[0] and
				parse_filename(f, 'reltime') <= trange[1]):
				q.append(f)
	return q


def filter_files(filelist, exclusive=False, **kwargs):
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
		filelist = funcdict[k](filelist, kwargs[k], exclusive=exclusive)
	return filelist
