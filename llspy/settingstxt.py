from __future__ import division

import re
import io
import logging
import dateutil.parser as dp
from collections import defaultdict
from configparser import ConfigParser
from .util import py23_unpack, numberdict, dotdict
from .camera import CameraROI
try:
    from pathlib import Path
    Path().expanduser()
except (ImportError, AttributeError):
    from pathlib2 import Path

logger = logging.getLogger(__name__)


# repating pattern definitions used for parsing settings file
numstk_regx = re.compile(r"""
    \#\sof\sstacks\s\((?P<channel>\d)\) # channel number inside parentheses
    \s:\s+(?P<numstacks_requested>\d+)  # number of stacks after the colon
    """, re.MULTILINE | re.VERBOSE)

wavfrm_regx = re.compile(r"""
    ^(?P<waveform>.*)\sOffset,  # Waveform type, newline followed by description
    .*\((?P<channel>\d+)\)\s    # get channel number inside of parentheses
    :\s*(?P<offset>[-\d]*\.?\d*)    # float offset value after colon
    \s*(?P<interval>[-\d]*\.?\d*)   # float interval value next
    \s*(?P<numpix>\d+)          # integer number of pixels last
    """, re.MULTILINE | re.VERBOSE)

exc_regx = re.compile(r"""
    Excitation\sFilter,\s+Laser,    # Waveform type, newline followed by description
    .*\((?P<channel>\d+)\)\s    # get channel number inside of parentheses
    :\s+(?P<exfilter>[^\s]*)        # excitation filter: anything but whitespace
    \s+(?P<laser>\d+)           # integer laser line
    \s+(?P<power>\d*\.?\d*)     # float laser power value next
    \s+(?P<exposure>\d*\.?\d*)  # float exposure time last
    """, re.MULTILINE | re.VERBOSE)

PIXEL_SIZE = {
    'C11440-22C': 6.5,
    'C11440': 6.5,
    'C13440': 6.5,
}


class SettingsParserError(Exception):
    pass


def parse_settings(path, pattern='*Settings.txt'):
    """ Parse LLS Settings.txt file and return dict of info """
    path = Path(path)
    if path.is_dir():
        sfiles = [s for s in path.glob(pattern)]
        if len(sfiles) == 0:
            return {}
        if len(sfiles) > 1:
            logger.warn('Multiple Settings.txt files detected. '
                        'Using first one.')
        path = sfiles[0]
    if not path.is_file():
        raise IOError('Could not read file: %s' % str(path))
    with io.open(str(path), 'r', encoding='utf-8') as f:
        text = f.read()

    sections = [t.strip()for t in
                re.split(r'(?:[\*\s]+)([^\*]+)', text)
                if t.strip()]
    if len(sections) % 2:
        raise SettingsParserError('Section headings not properly parsed')
    sections = dict(zip(sections[::2], sections[1::2]))
    for k in ('General', 'Waveform', 'Camera'):
        if k not in sections:
            raise SettingsParserError('Cannot parse settings file without '
                                      '"{}"" section'.format(k))

    def _search(regex, default=None, func=lambda x: x, section=text):
        match = re.search(regex, sections[section])
        if match and len(match.groups()):
            return func(match.group(1).strip())
        return default

    _D = dotdict(
        params=dotdict(),
        camera=dotdict(),
        mask=None,
        channels=defaultdict(lambda: defaultdict(dict))
    )

    # basic stuff from General section
    searches = [
        # Section     label    regex               default         formatter
        ('General', ('date', r'Date\s*:\s*(.*)\n', None, dp.parse),),
        ('General', ('acq_mode', r'Acq Mode\s*:\s*(.*)\n'),),
        ('General', ('software_version', r'Version\s*:\s*v ([\d*.?]+)'),),
        ('Waveform', ('cycle_lasers', r'Cycle lasers\s*:\s*(.*)(?:$|\n)'),),
        ('Waveform', ('z_motion', r'Z motion\s*:\s*(.*)(?:$|\n)'),),
    ]
    for section, item in searches:
        key, patrn = py23_unpack(*item)
        _D[key] = _search(*patrn, section=section)

    # channel-specific information
    for regx in (wavfrm_regx, exc_regx, numstk_regx):
        for item in regx.finditer(sections['Waveform']):
            i = item.groupdict()
            c = int(i.pop('channel'))
            w = i.pop('waveform', False)
            if w:
                _D['channels'][c][w].update(numberdict(i))
            else:
                _D['channels'][c].update(numberdict(i))

    # camera section
    cp = ConfigParser(strict=False)
    cp.read_string('[Section]\n' + sections['Camera'])
    cp = cp[cp.sections()[0]]
    for s in ('model', 'serial', 'exp(s)', 'cycle(s)', 'cycle(hz)', 'roi'):
        _D['camera'].update({re.sub(r'(\()(.+)(\))', r"_\2", s): cp.get(s)})
    if _D['camera'].get('roi'):
        _D['camera']['roi'] = CameraROI([int(q) for q in re.findall(r'\d+', cp.get('roi'))])
    try:
        _D['camera']['pixel'] = PIXEL_SIZE[_D['camera']['model'].split('-')[0]]
    except Exception:
        _D['camera']['pixel'] = None

    # general .ini File section

    # parse the ini part
    cp = ConfigParser(strict=False)
    cp.optionxform = str    # leave case in keys
    cp.read_string(sections['.ini File'])
    # not everyone will have added Annular mask to their settings ini
    for n in ['Mask', 'Annular Mask', 'Annulus']:
        if cp.has_section(n):
            _D['mask'] = {}
            for k, v in cp['Annular Mask'].items():
                _D['mask'][k] = float(v)
    _D['params']['angle'] = cp.getfloat('Sample stage',
                                        'Angle between stage and bessel beam (deg)')
    _D['mag'] = cp.getfloat('Detection optics', 'Magnification')
    _D['camera']['name'] = cp.get('General', 'Camera type')
    _D['camera']['trigger_mode'] = cp.get('General', 'Cam Trigger mode')
    _D['mag'] = cp.getfloat('Detection optics', 'Magnification')
    _D['camera']['twincam'] = cp.getboolean('General', 'Twin cam mode?')

    try:
        _D['camera']['cam2_name'] = cp.get('General', '2nd Camera type')
    except Exception:
        _D['camera']['cam2_name'] = 'Disabled'
    _D['ini'] = cp
    if _D['camera']['pixel'] and _D['mag']:
        _D['params']['dx'] = round(_D['camera']['pixel'] / _D['mag'], 4)
    else:
        _D['params']['dx'] = None
    _D['params']['nc'] = len(_D['channels'])
    if _D['channels'][0]['numstacks_requested']:
        _D['params']['nt'] = int(_D['channels'][0]['numstacks_requested'])
    else:
        _D['params']['nt'] = None
    _D['params']['nx'] = None  # .camera.roi.height
    _D['params']['ny'] = None  # .camera.roi.width
    _D['params']['wavelengths'] = [_D['channels'][v]['laser'] for v in
                                   sorted(_D['channels'].keys())]
    _D['params']['samplescan'] = _D['z_motion'] == 'Sample piezo'
    _D['params']['roi'] = _D['camera']['roi']

    k = 'S PZT' if _D['z_motion'] == 'Sample piezo' else 'Z PZT'
    try:
        _D['params']['nz'] = _D['channels'][0][k]['numpix']
        _D['params']['dz'] = abs(_D['channels'][0][k]['interval'])
    except Exception:
        _D['params']['dz'] = None

    _D['channels'] = {k: dict(v) for k, v in _D['channels'].items()}
    return _D
