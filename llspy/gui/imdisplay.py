from __future__ import division

import numpy as np


def slices3D(data, levels=None):
	try:
		import pyqtgraph as pg
		import pyqtgraph.opengl as gl
	except ImportError:
		"ERROR: could not import pyopengl"
		return
	w = gl.GLViewWidget()
	w.opts['distance'] = 200
	w.show()
	w.setWindowTitle('Image Preview')

	# create volume data set to slice three images from
	shape = data.shape

	# slice out three planes, convert to RGBA for OpenGL texture
	if levels is None:
		levels = (data.min(), data.max())

	tex1 = pg.makeRGBA(data[shape[0]//2], levels=levels)[0]       # yz plane
	tex2 = pg.makeRGBA(data[:, shape[1]//2], levels=levels)[0]     # xz plane
	tex3 = pg.makeRGBA(data[:, :, shape[2]//2], levels=levels)[0]   # xy plane
	# ex1[:,:,3] = 128
	# ex2[:,:,3] = 128
	# ex3[:,:,3] = 128

	# Create three image items from textures, add to view
	v1 = gl.GLImageItem(tex1)
	v1.translate(-shape[1]/2, -shape[2]/2, 0)
	v1.rotate(90, 0, 0, 1)
	v1.rotate(-90, 0, 1, 0)
	w.addItem(v1)
	v2 = gl.GLImageItem(tex2)
	v2.translate(-shape[0]/2, -shape[2]/2, 0)
	v2.rotate(-90, 1, 0, 0)
	w.addItem(v2)
	v3 = gl.GLImageItem(tex3)
	v3.translate(-shape[0]/2, -shape[1]/2, 0)
	w.addItem(v3)

	ax = gl.GLAxisItem()
	w.addItem(ax)


# modified from tifffile to allow for contrast and MIPs and changing cmap
def imshow3D(data, title=None, vmin=0, vmax=None, cmap=None,
		bitspersample=None, photometric='minisblack', interpolation=None,
		dpi=96, figure=None, subplot=111, maxdim=8192, figsize=8, **kwargs):
	"""Plot n-dimensional images using matplotlib.pyplot.

	Return figure, subplot and plot axis.
	Requires pyplot already imported `from matplotlib import pyplot`.

	Parameters
	----------
	bitspersample : int or None
		Number of bits per channel in integer RGB images.
	photometric : {'miniswhite', 'minisblack', 'rgb', or 'palette'}
		The color space of the image data.
	title : str
		Window and subplot title.
	figure : matplotlib.figure.Figure (optional).
		Matplotlib to use for plotting.
	subplot : int
		A matplotlib.pyplot.subplot axis.
	maxdim : int
		maximum image width and length.
	kwargs : optional
		Arguments for matplotlib.pyplot.imshow.

	"""
	import sys

	isrgb = photometric in ('rgb', 'palette')

	def reshape_nd(image, ndim):
		if image.ndim >= ndim:
			return image
		image = image.reshape((1,) * (ndim - image.ndim) + image.shape)
		return image

	data = data.squeeze()
	if photometric in ('miniswhite', 'minisblack'):
		data = reshape_nd(data, 2)
	else:
		data = reshape_nd(data, 3)

	dims = data.ndim
	if dims < 2:
		raise ValueError("not an image")
	elif dims == 2:
		dims = 0
		isrgb = False
	else:
		if isrgb and data.shape[-3] in (3, 4):
			data = np.swapaxes(data, -3, -2)
			data = np.swapaxes(data, -2, -1)
		elif not isrgb and (data.shape[-1] < data.shape[-2] // 8 and
							data.shape[-1] < data.shape[-3] // 8 and
							data.shape[-1] < 5):
			data = np.swapaxes(data, -3, -1)
			data = np.swapaxes(data, -2, -1)
		isrgb = isrgb and data.shape[-1] in (3, 4)
		dims -= 3 if isrgb else 2

	if isrgb:
		data = data[..., :maxdim, :maxdim, :maxdim]
	else:
		data = data[..., :maxdim, :maxdim]

	if photometric == 'palette' and isrgb:
		datamax = data.max()
		if datamax > 255:
			data >>= 8  # possible precision loss
		data = data.astype('B')
	elif data.dtype.kind in 'ui':
		if not (isrgb and data.dtype.itemsize <= 1) or bitspersample is None:
			try:
				bitspersample = int(np.ceil(np.log(data.max(), 2)))
			except Exception:
				bitspersample = data.dtype.itemsize * 8
		elif not isinstance(bitspersample, int):
			# bitspersample can be tuple, e.g. (5, 6, 5)
			bitspersample = data.dtype.itemsize * 8
		# datamax = 2**bitspersample # don't like this for 16 bit images
		datamax = data.max()
		if isrgb:
			if bitspersample < 8:
				data <<= 8 - bitspersample
			elif bitspersample > 8:
				data >>= bitspersample - 8  # precision loss
			data = data.astype('B')
	elif data.dtype.kind == 'f':
		datamax = data.max()
		if isrgb and datamax > 1.0:
			if data.dtype.char == 'd':
				data = data.astype('f')
			data /= datamax
	elif data.dtype.kind == 'b':
		datamax = 1
	elif data.dtype.kind == 'c':
		# TODO: handle complex types
		raise NotImplementedError("complex type")

	if not isrgb:
		if vmax is None:
			vmax = datamax
		if vmin is None:
			if data.dtype.kind == 'i':
				dtmin = np.iinfo(data.dtype).min
				vmin = np.min(data)
				if vmin == dtmin:
					vmin = np.min(data > dtmin)
			if data.dtype.kind == 'f':
				dtmin = np.finfo(data.dtype).min
				vmin = np.min(data)
				if vmin == dtmin:
					vmin = np.min(data > dtmin)
			else:
				vmin = 0

	pyplot = sys.modules['matplotlib.pyplot']

	if figure is None:
		yxAspect = data.shape[-2]/data.shape[-1]
		fgsz = (figsize/yxAspect, figsize)
		pyplot.rc('font', family='sans-serif', weight='normal', size=8)
		figure = pyplot.figure(dpi=dpi, figsize=fgsz, frameon=True,
							facecolor='1.0', edgecolor='w')
		try:
			figure.canvas.manager.window.title(title)
		except Exception:
			pass
		pyplot.subplots_adjust(bottom=0.03*(dims+4)+0.01, top=0.9,
							left=0.1, right=0.95, hspace=0.05, wspace=0.0)
	subplot = pyplot.subplot(subplot)

	if title:
		# try:
		# 	title = unicode(title, 'Windows-1252')
		# except TypeError:
		# 	pass
		figure.suptitle(title, size=11)

	if cmap is None:
		if data.dtype.kind in 'ubf' or vmin == 0:
			cmap = 'cubehelix'
		else:
			cmap = 'coolwarm'
		if photometric == 'miniswhite':
			cmap += '_r'

	# FIXME: this overrides the input arguments
	dataRange = data.max()-data.min()
	vmin_init = data.min()-dataRange*0.02
	vmax_init = data.max()*0.6
	image = pyplot.imshow(data[(0,) * dims].squeeze(), vmin=vmin_init, vmax=vmax_init,
						cmap=cmap, interpolation=interpolation, **kwargs)

	cmaps = tuple({cmap, 'gray', 'afmhot', 'cubehelix', 'inferno'})

	if not isrgb:
		cbar = pyplot.colorbar()  # panchor=(0.55, 0.5), fraction=0.05
	else:
		cbar = None

	def format_coord(x, y):
		# callback function to format coordinate display in toolbar
		x = int(x + 0.5)
		y = int(y + 0.5)
		try:
			if dims:
				return "%s @ %s [%4i, %4i]" % (cur_ax_dat[1][y, x],
											current, x, y)
			else:
				return "%s @ [%4i, %4i]" % (data[y, x], x, y)
		except IndexError:
			return ""

	pyplot.gca().format_coord = format_coord

	if dims:
		current = list((0,) * dims)
		cur_ax_dat = [0, data[tuple(current)].squeeze()]
		global currentProjection
		currentProjection = None
		global currentCmap
		currentCmap = 0
		dnames = 'TCZYX'
		sliders = [pyplot.Slider(
			pyplot.axes([0.125, 0.03*(axis+1), 0.725, 0.025]),
			dnames[axis-dims-2], 0, data.shape[axis]-1, 0, facecolor='0.5',
			valfmt='%%.0f [%i]' % data.shape[axis]) for axis in range(dims)]
		sliders.append(pyplot.Slider(pyplot.axes([0.125, 0.03*(dims+1), 0.725, 0.025]),
					'min', data.min()-dataRange*0.1,
					data.min()+dataRange*0.1, vmin_init,
					valfmt='%%.0f [%i]' % data.min(), facecolor='0.5'))
		sliders.append(pyplot.Slider(pyplot.axes([0.125, 0.03*(dims+2), 0.725, 0.025]),
					'max', data.min(), data.max(), vmax_init,
					valfmt='%%.0f [%i]' % data.max(), facecolor='0.5'))
		for slider in sliders:
			slider.drawon = False

		prjlookup = {
			'm': lambda x: np.max(x, 0),
			'n': lambda x: np.min(x, 0),
			'b': lambda x: np.mean(x, 0),
			'v': lambda x: np.std(x, 0),
			',': lambda x: np.median(x, 0),
		}

		def set_image(current, sliders=sliders, data=data):
			# change image and redraw canvas
			if currentProjection and currentProjection in prjlookup.keys():
				IM = prjlookup[currentProjection](data[tuple(current[:dims-1])])
			else:
				IM = data[tuple(current)]
			image.set_data(IM.squeeze())
			for ctrl, index in zip(sliders[:dims], current):
				ctrl.eventson = False
				ctrl.set_val(index)
				ctrl.eventson = True
			figure.canvas.draw()

		def vmin_changed(val, sliders=sliders):
			image.set_clim(vmin=val)
			sliders[dims].eventson = False
			sliders[dims].set_val(val)
			sliders[dims].eventson = True
			figure.canvas.draw()

		def vmax_changed(val, sliders=sliders):
			image.set_clim(vmax=val)
			sliders[dims+1].eventson = False
			sliders[dims+1].set_val(val)
			sliders[dims+1].eventson = True
			figure.canvas.draw()

		def on_changed(index, axis, data=data, current=current):
			# callback function for slider change event
			index = int(round(index))
			cur_ax_dat[0] = axis
			if index == current[axis]:
				return
			if index >= data.shape[axis]:
				index = 0
			elif index < 0:
				index = data.shape[axis] - 1
			current[axis] = index
			set_image(current)

		def cycle_color(e):
			global currentCmap
			currentCmap += 1
			image.set_cmap(cmaps[currentCmap % len(cmaps)])
			figure.canvas.draw()

		def on_keypressed(event, data=data, current=current):
			# callback function for key press event
			key = event.key
			axis = cur_ax_dat[0]
			if str(key) in '0123456789':
				on_changed(int(key), axis)
			elif key == 'right':
				on_changed(current[axis] + 1, axis)
			elif key == 'left':
				on_changed(current[axis] - 1, axis)
			elif key == 'up':
				cur_ax_dat[0] = 0 if axis == len(data.shape)-3 else axis + 1
			elif key == 'down':
				cur_ax_dat[0] = len(data.shape)-3 if axis == 0 else axis - 1
			elif key == 'end':
				on_changed(data.shape[axis] - 1, axis)
			elif key == 'home':
				on_changed(0, axis)
			elif key == 'c':
				cycle_color(None)
			elif key in prjlookup.keys():
				global currentProjection
				if currentProjection and currentProjection == key:
					currentProjection = None,
				else:
					currentProjection = key
				set_image(current)

		def on_scroll(event):
			axis = cur_ax_dat[0]
			if event.button == 'up':
				on_changed(current[axis] - 1, dims-1)
			else:
				on_changed(current[axis] + 1, dims-1)

		figure.canvas.mpl_connect('scroll_event', on_scroll)

		figure.canvas.mpl_connect('key_press_event', on_keypressed)
		for axis, ctrl in enumerate(sliders[:dims]):
			ctrl.on_changed(lambda k, a=axis: on_changed(k, a))
		sliders[dims].on_changed(lambda k: vmin_changed(k))
		sliders[dims+1].on_changed(lambda k: vmax_changed(k))

		if cbar:
			cbar.ax.set_picker(5)
			figure.canvas.mpl_connect('pick_event', cycle_color)

	return figure, subplot, image

