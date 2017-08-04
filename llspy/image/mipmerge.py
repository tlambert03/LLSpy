from llspy import plib
import tifffile as tf
import numpy as np


def mergemips(folder):
	"""combine folder of MIPs into a single multi-channel time stack.
	return dict with keys= axes(x,y,z) and values = numpy array
	"""
	folder = plib.Path(folder)
	if not folder.is_dir():
		raise IOError('MIP folder does not exist: {}'.format(str(folder)))

	try:
		out = {}
		for axis in ['z', 'x', 'y']:
			tiffs = []
			imcounts = []
			c = 0
			while True:
				filelist = sorted(folder.glob('*ch{}_stack*MIP_{}.tif'.format(c, axis)))
				if not len(filelist):
					break
				for file in filelist:
					tiffs.append(tf.imread(str(file)))
				imcounts.append(len(filelist))
				c += 1
			if c > 0:
				nt = np.max(imcounts)

				if (len(set(imcounts)) > 1):
					raise ValueError('Cannot merge MIPS with different number of '
						'timepoints per channel')
				if len(tiffs) != c * nt:
					raise ValueError('Number of images does not equal nC * nT')

				stack = np.stack(tiffs)
				stack = stack.reshape((c, 1, nt,
							stack.shape[-2], stack.shape[-1]))  # TZCYX
				stack = np.transpose(stack, (2, 1, 0, 3, 4))
				out[axis] = stack
		return out

	except ValueError:
		print("ERROR: failed to merge MIPs from {}".format(str(folder)))
		print("skipping...\n")
