class dotdict(dict):
	"""dot.notation access to dictionary attributes"""
	__getattr__ = dict.get
	__setattr__ = dict.__setitem__
	__delattr__ = dict.__delitem__
	def __dir__(self):
		return self.keys()

def format_size(size):
	"""Return file size as string from byte size."""
	for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'):
		if size < 2048:
			return "%.f %s" % (size, unit)
		size /= 1024.0