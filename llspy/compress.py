from __future__ import print_function, division
from . import config
from . import util

import os
import fnmatch
import subprocess
import glob


EXTENTIONS = {
	'.bz2': 'lbzip2',
	'.gz': 'pigz',
}

archive_extension = {
	'lbzip2': 'bz2',
	'bzip2': 'bz2',
	'pbzip2': 'bz2',
	'pigz': 'gz',
	'gzip': 'gz',
}


def findtar(path):
	for file in os.listdir(path):
		if fnmatch.fnmatch(file, '*.tar*'):
			return os.path.join(path, file)
	return None


def decompress(fpath):
	# find tarball
	tarball = findtar(fpath)
	if not tarball:
		print('did not find .tar file in {}!'.format(fpath))
		return

	# get compression binary by extension
	arch_ext = os.path.splitext(tarball)[1]
	compression_program = EXTENTIONS.get(arch_ext, None)
	if not compression_program:
		raise ValueError('Unrecognized compression extension: {}'.format())

	# decompress the tar file
	subprocess.call([compression_program, '-d', '-v', tarball])

	# extract the contents of the tarball
	tarball = tarball.strip(arch_ext)
	try:
		subprocess.call(['tar', '-xvf', tarball, '-C', fpath])
		# remove the tarball
		os.remove(tarball)
	except subprocess.CalledProcessError:
		print('did not delete {}... '
			'unclear whether it was extracted correctly'.format(tarball))


def untar(fpath, verbose=True):
	"""look for and decompress tarball in folder"""

	# find the tarball
	tarball = glob.glob(os.path.join(fpath, '*.tar*'))
	if not len(tarball):
		if verbose:
			print('did not find .tar file!')
		return 0
	else:
		tarball = tarball[0]

	if verbose:
		print('thawing {}...'.format(fpath))

	# TODO: allow user adjustment of this
	if tarball.endswith('.bz2'):
		archive_extension = '.bz2'
		compression_program = 'lbzip2'
	elif tarball.endswith('.gz'):
		archive_extension = '.gz'
		compression_program = 'pigz'
	else:
		print("ERROR: unknown compression type")
		return 0

	cmdlist = [compression_program, '-d', tarball]
	if verbose:
		cmdlist.extend(['-v'])
		subprocess.call(cmdlist)
	else:
		subprocess.check_output(cmdlist, stderr=subprocess.STDOUT)

	tarball = tarball.strip(archive_extension)
	cmdlist = ['tar', '-x']
	if verbose:
		cmdlist.extend(['-v'])
	cmdlist.extend(['-f', tarball])
	cmdlist.extend(['-C', fpath])

	try:
		if verbose:
			subprocess.call(cmdlist)
		else:
			subprocess.check_output(cmdlist, stderr=subprocess.STDOUT)
		os.remove(tarball)
		return 1
	except subprocess.CalledProcessError:
			# raise subprocess.CalledProcessError(e.cmd, e.returncode, e.output)
			if verbose:
				print('did not delete {}...'
					'unclear whether it was extracted correctly'.format(tarball))
			return 0


def checktar():
	o = subprocess.check_output(['tar', '--help'])
	if '--remove-files' not in str(o):
		print('tar compression requires GNU-tar, see readme for installation instructions')
		return 0
	return 1


def make_tar(rawpath, compression='lbzip2', verbose=True):
	'''
	compress all of the tiff files in rawpath into single .tar.bz2/gz file

	compression options:
		lbzip2
		bzip2
		pbzip2
		pigz
		gzip
	'''
	if not checktar():
		return 0

	if not util.which(compression):
		raise IOError('could not find compression program: {}'.format(compression))
		return 0

	if not os.path.exists(rawpath):
		return 0

	# make sure there are tiff files in the folder
	tifflist = [f for f in os.listdir(rawpath) if f.endswith('.tif')]
	if not len(tifflist):
		if verbose:
			print("No tiff files to compress in {}".format(rawpath))
		return 0
	basename = tifflist[0].split('_')[0]

	# figure out what type of folder this is
	if '_deskewed' in tifflist[0]:
		folder_type = 'DESKEWED'
	elif '_decon' in tifflist[0]:
		folder_type = 'DECON'
	else:
		folder_type = 'RAW'

	if verbose:
		print('compressing {} files in {}...'.format(folder_type, rawpath))

	# determine compression type
	archive_extension = {
		'lbzip2': 'bz2',
		'bzip2': 'bz2',
		'pbzip2': 'bz2',
		'pigz': 'gz',
		'gzip': 'gz',
	}

	# build command
	cmdlist = ['tar', '-c', '--use-compress-program={}'.format(compression)]

	# don't include these files/folders
	excludelist = ['*Settings.txt', '*MIP*', '*.DS_Store',
					'*' + config.__OUTPUTLOG__ + '*']
	for item in excludelist:
		cmdlist.extend(["--exclude=%s" % item])
		tifflist = [t for t in tifflist if item.strip('*') not in t]

	# if the exlusions obliterated the list of files, abort
	if not len(tifflist):
		if verbose:
			print("No tiff files to compress in {}".format(rawpath))
		return 0

	cmdlist.extend(["--exclude=*.tar.%s" % archive_extension[compression]])
	if verbose:
		cmdlist.extend(['-v'])
	cmdlist.extend(['--remove-files'])
	archive_name = os.path.join(rawpath, '%s_%s.tar.%s' %
		(basename, folder_type, archive_extension[compression]))
	cmdlist.extend(['-f', archive_name])
	cmdlist.extend(['-C', rawpath])
	cmdlist.extend(tifflist)

	if verbose:
		subprocess.call(cmdlist)
	else:
		subprocess.check_output(cmdlist, stderr=subprocess.STDOUT)
	return 1
