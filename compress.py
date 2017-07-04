from __future__ import print_function, division
import os
import subprocess
from llspy.config import config


def untar(fpath, verbose=True):
	"""look for and decompress tarball in folder"""
	if verbose:
		print('thawing {}...'.format(fpath))
	tarball = glob.glob(os.path.join(fpath, '*.tar*'))
	if not len(tarball):
		if verbose:
			print('did not find .tar file!')
		return 0
	else:
		tarball = tarball[0]
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
	call(cmdlist)
	tarball = tarball.strip(archive_extension)
	cmdlist = ['tar', '-x']
	cmdlist.extend(['-v'])
	cmdlist.extend(['-f', tarball])
	cmdlist.extend(['-C', fpath])
	p = Popen(cmdlist, stdin=PIPE, stdout=PIPE, stderr=PIPE)
	# i don't understand why, but the output seems to be coming second
	output, err = p.communicate()
	if p.returncode == 0:
		os.remove(tarball)
		return 1
	else:
		if verbose:
			print('did not delete {}... \
				unclear whether it was extracted correctly'.format(tarball))
		return 0


def reduce_to_raw(fpath, keepmip=True, verbose=True):
	"""
	need to consider the case of sepmips
	"""
	if verbose:
		print('reducing %s...' % fpath)
	subfolders = ['GPUdecon', 'CPPdecon', 'Deskewed', 'Corrected']
	if keepmip:
		for folder in subfolders:
			# see if there is are MIP.tifs in the folder itself

			L = glob.glob(os.path.join(fpath, folder, '*MIP*.tif'))
			if not len(L):
				if os.path.isdir(os.path.join(fpath, folder, 'MIPs')):
					L = [os.path.join(fpath, folder, 'MIPs')]
			if len(L):
				if not os.path.exists(os.path.join(fpath, 'MIPs')):
					os.mkdir(os.path.join(fpath, 'MIPs'))
				for f in L:
					basename = os.path.basename(f)
					os.rename(f, os.path.join(fpath, 'MIPs', basename))
				break

	for folder in subfolders:
		if os.path.exists(os.path.join(fpath, folder)):
			try:
				if verbose:
					print('\tdeleting %s...' % os.path.join(fpath, folder))
				shutil.rmtree(os.path.join(fpath, folder))

				if not keepmip and os.path.exists(os.path.join(fpath, 'MIPs')):
					shutil.rmtree(os.path.join(fpath, 'MIPs'))

			except Exception:
				print("unable to remove directory: {}".format(os.path.join(fpath, folder)))
				return 0
	try:
		i = glob.glob(os.path.join(fpath, '*%s' % 'ProcessingLog.txt'))
		for n in i:
			os.remove(n)
	except Exception:
		pass
	return 1


def checktar():
	o = subprocess.check_output(['tar', '--help'])
	if '--remove-files' not in o:
		print('tar compression requires GNU-tar, \
				see readme for installation instructions')
		return 0
	return 1


def make_tar(rawpath, compression='lbzip2', verbose=True):
	'''
	compress all of the tiff files in rawpath into single .tar.bz2/gz file
	'''

	if not checktar():
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

	# cmdlist=['find', rawpath, '-maxdepth', '1', '-name', '"*.tif"',
	# 		'-exec', 'basename', '{}', '\;', '|', 'tar', '-c',
	# 		'--use-compress-program=lbzip2', '-vf', 'mydir.tar', '-C',
	# 		'lattice/sample_data/SampleData', '-T', '-']

	# build command
	cmdlist = ['tar', '-c', '--use-compress-program=%s' % compression]

	excludelist = ['*Settings.txt', '*MIP*', '*.DS_Store',
					'*%s*' % config.processingLogfile]
	for item in excludelist:
		cmdlist.extend(["--exclude=%s" % item])
		tifflist = [t for t in tifflist if item.strip('*') not in t]
	if not len(tifflist):  # if the exlusions obliterated the list of files, abort
		if verbose:
			print("No tiff files to compress in {}".format(rawpath))
		return 0
	cmdlist.extend(["--exclude=*.tar.%s" % archive_extension[compression]])
	cmdlist.extend(['-v'])
	cmdlist.extend(['--remove-files'])
	archive_name = os.path.join(rawpath, '%s_%s.tar.%s' %
		(basename, folder_type, archive_extension[compression]))
	cmdlist.extend(['-f', archive_name])
	cmdlist.extend(['-C', rawpath])
	cmdlist.extend(tifflist)
	call(cmdlist)
	return 1


def freeze(fpath, keepmip=True, verbose=True, compression='lbzip2'):
	"""Freeze folder for long term storage.

	Delete's all deskewed and deconvolved data
	(with the execption of MIPs unless requested),
	then compresses raw files into compressed tarball
	"""
	if verbose:
		print("freezing {} ...".format(fpath))
	if reduce_to_raw(fpath, keepmip=keepmip, verbose=verbose):
		if make_tar(fpath, compression=compression, verbose=verbose):
			return 1
