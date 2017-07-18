from __future__ import division
import numpy as np


class dotdict(dict):
	"""dot.notation access to dictionary attributes"""
	__getattr__ = dict.get
	__setattr__ = dict.__setitem__
	__delattr__ = dict.__delitem__

	def __dir__(self):
		return self.keys()


class DimensionManager(object):
	# ('X',imageSize(2),pixelExtentInWorldX,pixelExtentInWorldX/2);

	def __init__(self, DimensionName='', NumberOfSamples=2, Delta=1, StartCoordinateInWorld=0.5):

		if DimensionName not in ['X', 'Y', 'Z']:
			raise ValueError('DimensionName must be X, Y, or Z')
		self.DimensionName = DimensionName
		self.Delta = Delta
		self.StartCoordinateInWorld = StartCoordinateInWorld
		self.NumberOfSamples = NumberOfSamples

	# PROPERTIES

	@property
	def WorldIncreasesWithIntrinsic(self):
		return self.Delta > 0

	@property
	def ExtentInWorld(self):
		return np.diff(self.WorldLimits)[0]

	@property
	def IntrinsicLimits(self):
		return 0.5 + np.array([0, self.NumberOfSamples])

	@property
	def WorldLimits(self):
		return np.sort(self.StartCoordinateInWorld + np.array([0, self.NumberOfSamples * self.Delta]))

	# SETTERS

	@WorldLimits.setter
	def WorldLimits(self, worldLimits):
		if not len(worldLimits) == 2:
			raise ValueError('worldLimits must be a vector of length 2')
		if worldLimits[1] <= worldLimits[0]:
			raise ValueError('worldLimits must be ascending in value')

		if self.WorldIncreasesWithIntrinsic:
			self.StartCoordinateInWorld = worldLimits[0]
			self.Delta = np.diff(worldLimits)[0] / self.NumberOfSamples
		else:
			self.StartCoordinateInWorld = worldLimits[1]
			self.Delta = -np.diff(worldLimits)[0] / self.NumberOfSamples

	def __setattr__(self, name, value):
		if name == 'NumberOfSamples':
			try:
				worldLimitsOld = self.WorldLimits
				self.Delta = np.diff(worldLimitsOld)[0] / value
			except Exception:
				# inelegent way to avoid error on __init__
				pass
		super(DimensionManager, self).__setattr__(name, value)

	# METHODS

	def contains(self, worldCoordinate):
		if isinstance(worldCoordinate, list):
			worldCoordinate = np.array(worldCoordinate)
		bounds = self.WorldLimits
		return (worldCoordinate >= bounds[0]) * (worldCoordinate <= bounds[1])

	def intrinsicToWorld(self, intrinsicCoordinate):
		if isinstance(intrinsicCoordinate, list):
			intrinsicCoordinate = np.array(intrinsicCoordinate)
		return (self.StartCoordinateInWorld +
			(intrinsicCoordinate - 0.5) * self.Delta)

	def worldToIntrinsic(self, worldCoordinate):
		if isinstance(worldCoordinate, list):
			worldCoordinate = np.array(worldCoordinate)
		return 0.5 + (worldCoordinate - self.StartCoordinateInWorld) * self.Delta

	def worldToSubscript(self, worldCoordinate):
		if np.isscalar(worldCoordinate):
			worldCoordinate = np.array([worldCoordinate])
		else:
			worldCoordinate = np.array(worldCoordinate)
		containedSubscripts = self.contains(worldCoordinate)
		subscript = np.empty(len(worldCoordinate))
		subscript[:] = np.NAN
		# Use round to map the intrinsic coordinate to the nearest
		# integral value. The outer min computation ensures that the
		# edge of the last pixel maps to a valid location, since round
		# maps 0.5 to 1.0.
		subscript[containedSubscripts] = np.minimum(
			np.round(self.worldToIntrinsic(worldCoordinate[containedSubscripts])),
			self.NumberOfSamples)
		return subscript


class imref2d(object):
	"""docstring for imref2d"""

	def __init__(self, *args):
		self.Dimension = dotdict()
		if len(args) == 0:
			self.Dimension.X = DimensionManager('X')
			self.Dimension.Y = DimensionManager('Y')
		elif len(args) == 1:
			self.Dimension.X = DimensionManager('X', args[0][1])
			self.Dimension.Y = DimensionManager('Y', args[0][0])
		elif len(args) == 3:
			if all([isinstance(x, (list, np.ndarray)) for x in args[1:3]]):
				# world limits provided
				self.Dimension.X = DimensionManager('X', args[0][1])
				self.Dimension.Y = DimensionManager('Y', args[0][0])
				self.XWorldLimits = args[1]
				self.YWorldLimits = args[2]
			elif all([np.isscalar(x) for x in args[1:3]]):
				# imref2d(imageSize,pixelExtentInWorldX,pixelExtentInWorldY)
				self.Dimension.X = DimensionManager('X', args[0][1], args[1], args[1] / 2)
				self.Dimension.Y = DimensionManager('Y', args[0][0], args[2], args[2] / 2)
			else:
				raise ValueError('2nd & 3rd arguments must all be either scalar or array')
		else:
			raise ValueError('imref2d expects either 0, 1, or 3 arguments')

	@property
	def ImageExtentInWorldX(self):
		return self.Dimension.X.ExtentInWorld

	@property
	def ImageExtentInWorldY(self):
		return self.Dimension.Y.ExtentInWorld

	@property
	def XWorldLimits(self):
		return self.Dimension.X.WorldLimits

	@property
	def YWorldLimits(self):
		return self.Dimension.Y.WorldLimits

	@property
	def PixelExtentInWorldX(self):
		return np.abs(self.Dimension.X.Delta)

	@property
	def PixelExtentInWorldY(self):
		return np.abs(self.Dimension.Y.Delta)

	@property
	def FirstCornerX(self):
		return self.Dimension.X.StartCoordinateInWorld

	@property
	def FirstCornerY(self):
		return self.Dimension.Y.StartCoordinateInWorld

	@property
	def XIntrinsicLimits(self):
		return self.Dimension.X.IntrinsicLimits

	@property
	def YIntrinsicLimits(self):
		return self.Dimension.Y.IntrinsicLimits

	@property
	def ImageSize(self):
		return np.array([self.Dimension.Y.NumberOfSamples,
			self.Dimension.X.NumberOfSamples])

	@XWorldLimits.setter
	def XWorldLimits(self, xLimWorld):
		self.Dimension.X.WorldLimits = xLimWorld

	@YWorldLimits.setter
	def YWorldLimits(self, yLimWorld):
		self.Dimension.Y.WorldLimits = yLimWorld

	@ImageSize.setter
	def ImageSize(self, imSize):
		# TODO: validate image size here
		self.Dimension.X.NumberOfSamples = imSize[1]
		self.Dimension.Y.NumberOfSamples = imSize[0]

	def contains(self, xWorld, yWorld):
		return self.Dimension.X.contains(xWorld) * self.Dimension.Y.contains(yWorld)

	def intrinsicToWorld(self, xIntrinsic, yIntrinsic):
		xw = self.Dimension.X.intrinsicToWorld(xIntrinsic)
		yw = self.Dimension.Y.intrinsicToWorld(yIntrinsic)
		return xw, yw

	def worldToIntrinsic(self, xWorld, yWorld):
		xi = self.Dimension.X.worldToIntrinsic(xWorld)
		yi = self.Dimension.Y.worldToIntrinsic(yWorld)
		return xi, yi

	def worldToSubscript(self, xWorld, yWorld):
		if len({type(n) for n in (xWorld, yWorld)}) > 1:
			raise ValueError('All inputs to worldToSubscript must have same type')
		if not any([np.isscalar(n) for n in (xWorld, yWorld)]):
			if len({len(n) for n in (xWorld, yWorld)}) > 1:
				raise ValueError('All inputs to worldToSubscript must have same size')
		# TODO: check order of CRP output index
		c = self.Dimension.X.worldToSubscript(xWorld)
		r = self.Dimension.Y.worldToSubscript(yWorld)

		nan_c = np.isnan(c)
		nan_r = np.isnan(r)

		c[nan_r] = np.NAN
		r[nan_c] = np.NAN

		return c, r

	def __repr__(self):
		from pprint import pformat
		repdict = {}
		for n in dir(self):
			if isinstance(self.__getattribute__(n), np.ndarray):
				val = self.__getattribute__(n)
				if len(val) == 1:
					repdict[n] = "{:.4f}".format(val[0])
				else:
					if np.issubdtype(val.dtype, np.int):
						repdict[n] = list(val)
					else:
						repdict[n] = list(["{:.4f}".format(i) for i in val])
			elif isinstance(self.__getattribute__(n), (np.float, float)):
				repdict[n] = "{:.4f}".format(self.__getattribute__(n))
			elif isinstance(self.__getattribute__(n), (np.int, np.int64, int)):
				repdict[n] = int(self.__getattribute__(n))
		return pformat(repdict)


class imref3d(imref2d):
	"""docstring for imref3d"""

	def __init__(self, *args):
		self.Dimension = dotdict()
		if len(args) == 0:
			self.Dimension.X = DimensionManager('X')
			self.Dimension.Y = DimensionManager('Y')
			self.Dimension.Z = DimensionManager('Z')
		elif len(args) == 1:
			self.Dimension.X = DimensionManager('X', args[0][2])
			self.Dimension.Y = DimensionManager('Y', args[0][1])
			self.Dimension.Z = DimensionManager('Z', args[0][0])
		elif len(args) == 4:
			if all([isinstance(x, (list, np.ndarray)) for x in args[1:4]]):
				# imref3d(imageSize,pixelExtentInWorldX,pixelExtentInWorldY,pixelExtentInWorldZ)
				self.Dimension.X = DimensionManager('X', args[0][2])
				self.Dimension.Y = DimensionManager('Y', args[0][1])
				self.Dimension.Z = DimensionManager('Z', args[0][0])
				self.XWorldLimits = args[1]
				self.YWorldLimits = args[2]
				self.ZWorldLimits = args[3]
			elif all([np.isscalar(x) for x in args[1:4]]):
				# imref3d(imageSize,xWorldLimits,yWorldLimits,zWorldLimits)
				self.Dimension.X = DimensionManager('X', args[0][2], args[1], args[1] / 2)
				self.Dimension.Y = DimensionManager('Y', args[0][1], args[2], args[2] / 2)
				self.Dimension.Z = DimensionManager('Z', args[0][0], args[3], args[3] / 2)
			else:
				raise ValueError('2nd - 4th arguments must all be either scalar or array')
		else:
			raise ValueError('imref3d expects either 0, 1, or 4 arguments')

	@property
	def ImageExtentInWorldZ(self):
		return self.Dimension.Z.ExtentInWorld

	@property
	def ZWorldLimits(self):
		return self.Dimension.Z.WorldLimits

	@property
	def PixelExtentInWorldZ(self):
		return np.abs(self.Dimension.Z.Delta)

	@property
	def FirstCornerZ(self):
		return self.Dimension.Z.StartCoordinateInWorld

	@property
	def ZIntrinsicLimits(self):
		return self.Dimension.Z.IntrinsicLimits

	@ZWorldLimits.setter
	def ZWorldLimits(self, zLimWorld):
		self.Dimension.Z.WorldLimits = zLimWorld

	@property
	def ImageSize(self):
		return np.array([self.Dimension.Z.NumberOfSamples,
			self.Dimension.Y.NumberOfSamples,
			self.Dimension.X.NumberOfSamples])

	@ImageSize.setter
	def ImageSize(self, imSize):
		# TODO: validate image size here
		self.Dimension.X.NumberOfSamples = imSize[2]
		self.Dimension.Y.NumberOfSamples = imSize[1]
		self.Dimension.Z.NumberOfSamples = imSize[0]

	def contains(self, xWorld, yWorld, zWorld):
		return (self.Dimension.X.contains(xWorld) *
			self.Dimension.Y.contains(yWorld) *
			self.Dimension.Z.contains(zWorld))

	def intrinsicToWorld(self, xIntrinsic, yIntrinsic, zIntrinsic):
		xw = self.Dimension.X.intrinsicToWorld(xIntrinsic)
		yw = self.Dimension.Y.intrinsicToWorld(yIntrinsic)
		zw = self.Dimension.Z.intrinsicToWorld(zIntrinsic)
		return xw, yw, zw

	def worldToIntrinsic(self, xWorld, yWorld, zWorld):
		xi = self.Dimension.X.worldToIntrinsic(xWorld)
		yi = self.Dimension.Y.worldToIntrinsic(yWorld)
		zi = self.Dimension.Z.worldToIntrinsic(zWorld)
		return xi, yi, zi

	def worldToSubscript(self, xWorld, yWorld, zWorld):
		if len({type(n) for n in (xWorld, yWorld, zWorld)}) > 1:
			raise ValueError('All inputs to worldToSubscript must have same type')
		if not any([np.isscalar(n) for n in (xWorld, yWorld, zWorld)]):
			if len({len(n) for n in (xWorld, yWorld, zWorld)}) > 1:
				raise ValueError('All inputs to worldToSubscript must have same size')
		# TODO: check order of CRP output index
		c = self.Dimension.X.worldToSubscript(xWorld)
		r = self.Dimension.Y.worldToSubscript(yWorld)
		p = self.Dimension.Z.worldToSubscript(zWorld)

		nan_c = np.isnan(c)
		nan_r = np.isnan(r)
		nan_p = np.isnan(p)

		c[nan_r | nan_p] = np.NAN
		r[nan_c | nan_p] = np.NAN
		p[nan_r | nan_c] = np.NAN

		return c, r, p

	def sizesMatch(self, I):
		raise NotImplementedError()
		# imageSize = I.shape
		# if ~isequal(size(self.ImageSize), size(imageSize))
		#     error(message('images:imref:sizeMismatch','ImageSize','imref3d'));
		# end
		# TF = isequal(imageSize(1),self.Dimension.Y.NumberOfSamples)...
		#   and isequal(imageSize(2),self.Dimension.X.NumberOfSamples)...
		#   and isequal(imageSize(3),self.Dimension.Z.NumberOfSamples);
