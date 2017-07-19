import ctypes
import numpy as np
import os

dylib = 'libcudaDeconv.so'
curdir = os.path.dirname(__file__)
cudaLib = ctypes.cdll.LoadLibrary(os.path.join(curdir, '..', '..', 'lib', dylib))

# Deskew is used when no decon is desired
# https://stackoverflow.com/questions/5862915/passing-numpy-arrays-to-a-c-function-for-input-and-output
Deskew_interface = cudaLib.Deskew_interface
Deskew_interface.restype = ctypes.c_int
Deskew_interface.argtypes = [np.ctypeslib.ndpointer(ctypes.c_ushort, flags="C_CONTIGUOUS"),
				ctypes.c_int,
				ctypes.c_int,
				ctypes.c_int,
				ctypes.c_float,
				ctypes.c_float,
				ctypes.c_float,
				np.ctypeslib.ndpointer(ctypes.c_float, flags="C_CONTIGUOUS"),
				ctypes.c_int,
				ctypes.c_int]

# RL_interface_init must be used before using RL_interface
RL_interface_init = cudaLib.RL_interface_init
RL_interface_init.restype = ctypes.c_int
RL_interface_init.argtypes = [ctypes.c_int,		# nx
					ctypes.c_int,				# ny
					ctypes.c_int,				# nz
					ctypes.c_float,				# drdata
					ctypes.c_float,				# dzdata
					ctypes.c_float,				# drpsf
					ctypes.c_float,				# dzpsf
					ctypes.c_float,				# angle
					ctypes.c_float,				# rotate
					ctypes.c_int,				# outputwidth
					ctypes.c_char_p]			# otfpath.encode()

# used between init and RL_interface to retrieve the post-deskewed image dimensions
get_output_nx = cudaLib.get_output_nx
get_output_ny = cudaLib.get_output_ny
get_output_nz = cudaLib.get_output_nz


# The actual decon
RL_interface = cudaLib.RL_interface
RL_interface.restype = ctypes.c_int
RL_interface.argtypes = [np.ctypeslib.ndpointer(ctypes.c_ushort, flags="C_CONTIGUOUS"),	 # im
				ctypes.c_int,													# nx
				ctypes.c_int,													# ny
				ctypes.c_int,													# nz
				np.ctypeslib.ndpointer(ctypes.c_float, flags="C_CONTIGUOUS"),   # result
				ctypes.c_float,													# background
				ctypes.c_int,													# iters
				ctypes.c_int]													# shift

# call after
cleanup = cudaLib.RL_cleanup


def RL_init(rawdata_shape, otfpath, drdata=0.104, dzdata=0.5, drpsf=0.104, dzpsf=0.1,
	angle=31.5, rotate=0, outputwidth=0):
	nz, ny, nx = rawdata_shape
	RL_interface_init(nx, ny, nz, drdata, dzdata, drpsf, dzpsf, angle, rotate,
		outputwidth, otfpath.encode())


def deskewGPU(im, dz=0.5, dr=0.102, angle=31.5, width=0, shift=0):
	nz, ny, nx = im.shape

	# have to calculate this here to know the size of the return array
	if width == 0:
		deskewedNx = np.int(nx + np.floor(nz * dz * abs(np.cos(angle * np.pi / 180)) / dr))
	else:
		deskewedNx = width

	result = np.empty((nz, ny, deskewedNx), dtype=np.float32)
	Deskew_interface(im, nx, ny, nz, dz, dr, angle, result, deskewedNx, shift)
	return result


def RL_decon(im, background=80, iters=10, shift=0):
	nz, ny, nx = im.shape
	result = np.empty((get_output_nz(), get_output_ny(), get_output_nx()), dtype=np.float32)
	RL_interface(im, nx, ny, nz, result, background, iters, shift)
	return result


if __name__ == "__main__":
	import sys
	import os
	import tifffile as tf
	import matplotlib.pyplot as plt
	if len(sys.argv) == 2:
		p = os.path.abspath(sys.argv[1]).replace('\\', '')
		if os.path.isfile(p):
			tf.imshow(deskewGPU(tf.imread(p), 0.5))
			plt.show()
	elif len(sys.argv) > 2:
		zstep = sys.argv[1]
		for i in sys.argv[2:]:
			p = p = os.path.abspath(i).replace('\\', '')
			if os.path.isfile(p):
				tf.imshow(deskewGPU(tf.imread(p), float(zstep)))
				plt.show()
	else:
		im = tf.imread('/Users/talley/Dropbox (HMS)/CBMF/lattice_sample_data/lls_basic_samp/cell5_ch0_stack0000_488nm_0000000msec_0020931273msecAbs.tif')
		tf.imshow(deskewGPU(im, 0.3))
		plt.show()
