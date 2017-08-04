def readHDF5(filename):
    import h5py
    f = h5py.File(filename, 'r')
    return f['data'].value

def readHDF5Frame(filename, frame):
    import h5py
    f = h5py.File(filename, 'r')
    return f['data'][frame]

def writeHDF5(filename, data):
    import h5py
    f = h5py.File(filename, 'w')
    f['data'] = data
    f.flush()
    f.close()