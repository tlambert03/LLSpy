import tarfile
import os
import subprocess
from . import util

EXTENTIONS = {
	'.bz2': 'lbzip2',
	'.gz': 'pigz',
}

archive_extension = {
	'lbzip2': '.bz2',
	'bzip2': '.bz2',
	'pbzip2': '.bz2',
	'pigz': '.gz',
	'gzip': '.gz',
}


def tartiffs(path, delete=True):
	tifflist = [f for f in os.listdir(path) if f.endswith('.tif')]
	# figure out what type of folder this is
	if not len(tifflist):
		print('No tiffs found in folder {}'.format(path))
		return None

	# generate output file name
	folder_type = 'RAW'
	if '_deskewed' in tifflist[0]:
		folder_type = 'DESKEWED'
	elif '_decon' in tifflist[0]:
		folder_type = 'DECON'
	basename = "_".join([tifflist[0].split('_ch')[0], folder_type])
	outtar = os.path.join(path, basename + '.tar')

	# create the tarfile
	with tarfile.open(outtar, 'w') as tar:
		[tar.add(os.path.join(path, i), arcname=i) for i in tifflist]

	if delete:
		[os.remove(os.path.join(path, i)) for i in tifflist]
	return outtar


def untar(tarball, delete=True):
	assert tarball.endswith('.tar'), 'File {} is not a tarball'.format(tarball)
	with tarfile.open(tarball) as tar:
		tar.extractall(path=os.path.dirname(tarball))
	if delete:
		os.remove(tarball)
	return os.path.dirname(tarball)


def zipit(fname, compression=None):
	if compression is None:
		compression = 'lbzip2'
	# check if it exists and is not already compressed
	assert os.path.exists(fname), 'File does not exist: {}'.format(fname)
	assert os.path.splitext(fname)[1] not in (archive_extension[compression],), 'File already compressed: ' + fname
	if compression == 'pigz':
		flags = '-v'  # the -z flag means complress to zlib format in pigz
	else:
		flags = '-zv'
	subprocess.call([compression, flags, fname])
	return fname + archive_extension[compression]


def unzipit(fname, compression=None):
	extension = os.path.splitext(fname)[1]
	if compression is None:
		compression = EXTENTIONS[extension]
	assert archive_extension[compression] == extension, "Format {} cannot be unzipped by program {}".format(extension, compression)
	# check if it exists and is compressed type
	assert os.path.exists(fname), 'File does not exist: {}'.format(fname)
	assert extension in (archive_extension[compression],), 'File not compressed: ' + fname
	subprocess.call([compression, '-dv', fname])
	return fname.strip(archive_extension[compression])


def compress(path, compression=None):
	tar = tartiffs(path)
	return zipit(tar, compression) if tar is not None and os.path.isfile(tar) else None


def decompress(file, compression=None):
	# if it's not a tar.bz2, assume it's a directory that contains one
	compressedtar = util.find_filepattern(file, '*.tar*') if os.path.isdir(file) else file
	if compressedtar is None or not compressedtar.endswith(archive_extension[compression]):
		print('No compressed files found in ' + file)
		return None
	tarball = unzipit(compressedtar, compression)
	return untar(tarball)
