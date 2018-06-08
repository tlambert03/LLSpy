import logging
import numpy as np
from datetime import datetime
from pprint import pformat
from collections import MutableMapping
from tifffolder import TiffFolder
from .settingstxt import parse_settings
from .util import mode1
try:
    from pathlib import Path
    Path().expanduser()
except (ImportError, AttributeError):
    from pathlib2 import Path

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class LLSParams(MutableMapping):
    """ A dictionary like container for LLS acquisition parameters.

    Intended to be the single source of truth

    Attributes:
        dz: the actual z step size used (regardless of stage scanning or not)
        dzFinal (calculated): effective final dz, (takes deskewing into account)
        dx: pixel size
        voxel (calculated): 3tuple of (dzFinal, dx, dx)
        angle: actual angle extracted from the settings file
        samplescan: whether samplescan mode was used
        deskew (calculated): deskew angle required (angle if samplescan else 0)
        decimated: False if there is a different nt for each channel

    Attributes likely acquired from settings:
        nt, nc, nz, ny, nx: shape of the dataset originally detected from
            settings.txt, but updated with actual data
        time (dict): contains time info:
            abs: list of absolute timestamps
            rel: list of relative timestamps
            t: list of timepoints in filenames (e.g. stack0003 -> 3)
            interval: mode interval of timepoints
        channels (dict): information from each channel
        wavelengths (list): list of wavelengths for each channel

    """

    __slots__ = ('_store', )

    def __init__(self, *args, **kwargs):
        self._store = {
            'dz': None,
            'dx': None,
            'angle': None,
            'samplescan': None,
            'decimated': False,
        }
        self.update(dict(*args, **kwargs))

    def __dir__(self):
        return set(self._store.keys()).union({'deskew', 'dzFinal', 'voxel'})

    def __getattr__(self, attr):
        return self.__getitem__(attr)

    def __getitem__(self, key):
        # computed params
        if key == 'dzFinal':
            v = self['dz']
            if self['samplescan'] and self['angle']:
                v *= np.sin(self['angle'] * np.pi / 180)
            return round(v, 4)
        if key == 'voxel':
            return self['dzFinal'], self['dx'], self['dx']
        if key == 'deskew':
            return self['angle'] if self['samplescan'] else 0

        return self._store[key]

    def __setitem__(self, key, value):
        self._store[key] = value
        if key == 'angle' and value is not None:
            self._store['samplescan'] = True if value > 0 else False
        # if key == 'samplescan' and not value:
        #     self._store['angle'] = 0

    def __delitem__(self, key):
        del self._store[key]

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)

    def __repr__(self):
        return pformat(self._store)


class LLSFolder(TiffFolder):
    """ Example class for handling lattice light sheet data """
    patterns = [
        ('rel', '_{d7}msec'),
        ('abs', '_{d10}msecAbs'),
        ('w', '_{d3}nm'),
        ('t', '_stack{d4}'),
        ('c', '_ch{d1}'),
        ('cam', 'Cam{D1}')
    ]

    def _parse(self):
        super(LLSFolder, self)._parse()
        for chan, cdict in self.channelinfo.items():
            for k, v in cdict.items():
                if k in ('cam', 'w'):
                    # assume the same value across all timepoints
                    cdict[k] = v[0]

        self.timeinfo = {}
        if self._shapedict.get('t') > 1 and self._symmetrical:
            cdict = next(iter(self.channelinfo.values()))
            if 'abs' in cdict and len(cdict['abs']) > 1:
                self.timeinfo = {
                    'interval': mode1(np.subtract(cdict['abs'][1:],
                                      cdict['abs'][:-1])),
                    'rel': cdict.get('rel'),
                    'abs': cdict.get('abs'),
                    't': cdict.get('t'),
                }


class LLSdir(object):

    def __init__(self, path, patterns=None):
        self.path = Path(path)
        if not self.path.is_dir():
            raise ValueError('Path provided is not a directory: %s' % path)

        try:
            self.data = LLSFolder(path, patterns)
        except LLSFolder.EmptyError:
            raise self.NoDataError('No data found in .../%s' % str(self.path.name))
        self.settings = parse_settings(path)
        self.params = LLSParams(self.settings.get('params', {}))
        # remove defaultdict class for better __repr__
        self.params['channels'] = {k: dict(v) for
                                   k, v in self.data.channelinfo.items()}
        self.params['decimated'] = self.data._symmetrical
        self.params['time'] = self.data.timeinfo

        self.date = self.settings.get('date') or datetime.now()

        self.params.update({'n' + a: v for a, v in
                            zip(self.data.axes, self.data.shape)})

        # if no settings were found, there is probably no dz/dx/angle info
        # check here and then look for a previously processed proclog.txt

    @property
    def is_ready(self):
        """Returns true if the path has data and enough params to process"""
        return bool(len(self.data) and self.params['dz'] and self.params['dx'])

    @property
    def age(self):
        """Returns the age of the dataset in age"""
        return (datetime.now() - self.date).days

    class NoDataError(Exception):
        """ Exception raised when the provided folder has no data to process """
        pass
