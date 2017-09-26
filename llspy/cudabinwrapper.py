import os
import sys
import re
import subprocess
import logging
from . import util

from voluptuous import (All, Any, Coerce, Length, Range, Exclusive, Schema,
    Required, REMOVE_EXTRA)
from voluptuous.humanize import validate_with_humanized_errors

PLAT = sys.platform
if PLAT == 'linux2':
    PLAT = 'linux'
elif PLAT == 'cygwin':
    PLAT = 'win32'

intbool = Schema(lambda x: int(bool(x)))


def dirpath(v):
    if not os.path.isdir(str(v)):
        raise ValueError('Not a valid directory')
    return v


def filepath(v):
    if not os.path.isfile(str(v)):
        raise ValueError('Not a valid directory')
    return v


def nGPU(binary):
    try:
        output = subprocess.check_output([binary, '-Q'])
        return int(re.match(b'Detected\s(?P<numGPU>\d+)\sCUDA', output).groups()[0])
    except Exception:
        return 0


def is_cudaDeconv(path):
    try:
        h = subprocess.check_output([path, '--help'])
        return all(a in str(h) for a in ('dzdata', 'deskew', 'input-dir', 'otf-file'))
    except Exception:
        return False


def get_bundled_binary(name='cudaDeconv'):
    """returns path to bundled, platform-specific cudaDeconv.
    This function is aware of whether program is running in frozen (pyinstaller)
    state,
    """

    if getattr(sys, 'frozen', False):
        binPath = sys._MEIPASS
    else:
        thisDirectory = os.path.dirname(__file__)
        binPath = os.path.join(thisDirectory, os.pardir, os.pardir, 'llspylibs', PLAT, 'bin')
        binPath = os.path.abspath(binPath)
        if not os.path.isdir(binPath):
            if os.environ.get('CONDA_PREFIX', False):
                base = os.environ['CONDA_PREFIX']
                if PLAT == 'win32':
                    binPath = os.path.join(base, 'Library', 'bin')
                else:
                    binPath = os.path.join(base, 'bin')
            else:
                binPath = ''

    # get specific binary by platform
    binary = os.path.join(binPath, name)
    binary += '.exe' if sys.platform.startswith('win32') else ''

    if not util.which(binary):
        raise CUDAbinException('{} could not be located or is not executable: {}'.format(name, binary))

    logging.debug("Found {} Binary: {}".format(name, os.path.abspath(binary)))
    return binary


cudaDeconSchema = Schema({
    Required('input-dir'): dirpath,
    Required('otf-file'): filepath,
    Required('filename-pattern'): str,
    'drdata': All(Coerce(float), Range(0.01, 0.5),
        msg='Data pixel size (drdata) must be float between 0.01 - 0.5'),
    'dzdata': All(Coerce(float), Range(0, 50),
        msg='Data Z step size (dzdata) must be float between 0 - 50'),
    'drpsf': All(Coerce(float), Range(0.01, 0.5),
        msg='PSF pixel size (drpsf) must be float between 0.01 - 0.5'),
    'dzpsf': All(Coerce(float), Range(0, 50),
        msg='PSF Z step size (dzpsf) must be float between 0 - 50'),
    'wavelength': All(Coerce(float), Range(.3, 1),
        msg='wavelength must be float between .3 - 1'),
    'wiener': Any(-1, All(Coerce(float), Range(0, 50))),
    'background': All(Coerce(int), Range(0, 65535),
        msg='background must be int between 0 - 65,535'),
    'napodize': All(Coerce(int), Range(0, 400),
        msg='napodize must be int between 0 - 400'),
    'nzblend': All(Coerce(int), Range(0, 100),
        msg='nzblend must be int between 0 - 100'),
    'NA': All(Coerce(float), Range(0.2, 1.33),
        msg='NA must be float between 0.2 - 1.33'),
    Exclusive('RL', 'iterations'): All(Coerce(int), Range(0, 30),
        msg='RL (nIters) must be int between 0 - 30'),
    Exclusive('nIters', 'iterations'): All(Coerce(int), Range(0, 30),
        msg='RL (nIters) must be int between 0 - 30'),
    'deskew': All(Coerce(float), Range(-180, 180),
        msg='deskew angle must be float between -180 and 180'),
    'width': All(Coerce(int), Range(0, 2000),
        msg='width must be int between 0 - 2000'),
    'shift': All(Coerce(int), Range(-1000, 1000),
        msg='shift must be int between -1000 - 1000'),
    'rotate': All(Coerce(float), Range(-180, 180),
        msg='rotate angle must be float between -180 and 180'),
    'saveDeskewedRaw': Coerce(bool),
    'crop': All((All(Coerce(int), Range(0, 2000)),), Length(min=6, max=6)),
    'MIP': All((intbool,), Length(min=3, max=3)),
    'rMIP': All((intbool,), Length(min=3, max=3)),
    'uint16': Coerce(bool),
    'bleachCorrection': Coerce(bool),
    'DoNotAdjustResForFFT': Coerce(bool),
}, extra=REMOVE_EXTRA)


class CUDAbin(object):
    """
    Wrapper class for Lin Shao's cudaDeconv binary
    """

    def __init__(self, binPath=None):
        """
        Init the class by optionally giving it a path to an cudaDeconv executable.
        Otherwise, the class assumes cudaDeconv is the environment PATH variable
        and retrieves the full path to the executable.
        The _self_test function is called to verify cudaDeconv.

        binPath -- Path to cudaDeconv executable

        Throws CUDAbinException:
            If cudaDeconv is not found in PATH or on the file system
            If cudaDeconv does not have execute permission

        Throws CUDAProcessError
            If the _self_test() does not pass
        """
        if binPath is None:
            binPath = get_bundled_binary()

        tmpPath = binPath
        if not os.path.isabs(binPath):
            for path in os.environ["PATH"].split(os.pathsep):
                fullbinPath = os.path.join(path, binPath)
                if os.path.isfile(fullbinPath):
                    tmpPath = fullbinPath
                    break
            else:
                raise CUDAbinException("{} not found in PATH".format(binPath))

        if self._self_test(tmpPath):
            self.path = tmpPath
            self.options = self._get_options()

    @property
    def opts_longform(self):
        return [next(x.strip('--') for x in key if x.startswith('--'))
                for key in self.options.keys()]

    @property
    def opts_shortform(self):
        return [next(x.strip('-') for x in key if x.startswith('-'))
                for key in self.options.keys()]

    def set_path(self, path):
        """
        Set path to the binary.
        """
        if self._self_test(path):
            self.path = path

    def _self_test(self, binPath):
        """
        test to check if the executable exists and run the '-h' command
        for verification.

        binPath -- Absolute path to binary

        Throws CUDAbinException:
        If binary file does not exist or does not have execute permissions
        Throws CUDAProcessError:
        If the 'cudaDeconv -h' command failed
        """
        if os.path.isfile(binPath) and os.access(binPath, os.X_OK):
            self._run_command([binPath, '-h'])
            return True
        else:
            raise CUDAbinException(
                'cudaDeconv could not be located or is not executable.')

    def process(self, indir, filepattern, otf, **options):
        cmd = [self.path]
        options['input-dir'] = indir
        options['otf-file'] = otf
        options['filename-pattern'] = filepattern
        cmd.extend(self.assemble_args(**options))
        print("\n"+" ".join(cmd))
        return self._run_command(cmd, mode='call')

    def _run_command(self, cmd, mode='check'):
        """
        Execute an cudaDeconv command via the subprocess module.
        If the process exits with a exit status of zero, the output is
        encapsulated into a CUDAbinResult and returned.
        Otherwise, an CUDAProcessError is thrown.
        """
        try:
            if mode == 'call':
                subprocess.call(cmd, stderr=subprocess.STDOUT)
            else:
                output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
                return CUDAbinResult(0, output)
        except subprocess.CalledProcessError as e:
                raise CUDAProcessError(e.cmd, e.returncode, e.output)

    def _get_options(self):
        """
        query the binary help output and output a list of possible flags
        and descriptions
        """
        h = self._run_command([self.path, '-h'])
        self.helpstring = h.output.decode('utf-8')
        H = self.helpstring.splitlines()
        options = [re.findall('[^A-Za-z1-9]-[1-9a-zA-Z-]+', i) for i in H]
        hasarg = [1 if z else 0 for z in options]
        options = [tuple(z.strip(' ') for z in i) for i in options if i]
        d = [i.split('   ')[-1].strip()
            if len(i.split('   ')) > 1 else '' for i in H]

        descr = []
        buf = ''
        for n in list(zip(hasarg, d)):
            if n[0]:
                descr.append(buf.strip())
                buf = ''
            buf += ' ' + n[1]
        descr.append(buf.strip())
        descr = descr[1:]
        return {options[i]: descr[i] for i in range(len(descr))}

    def has_option(self, flag):
        """check the existence of a given flag in the binary help string."""
        return any([flag in key for key in self.options.keys()])

    def has_option_longname(self, name):
        """check the existence of a given flag in the binary help string."""
        return name in self.opts_longform

    def _validate_flag_list(self, flaglist):
        """validate a list of options flags... before sending command string"""
        q = [self.has_option(i) for i in flaglist]
        if all(q):
            return True
        else:
            badflags = [i for i, x in enumerate(q) if not x]
            msg = ''
            for f in badflags:
                msg += "Unrecognized option: '{}'\n".format(flaglist[f])
            raise CUDAbinException(msg)

    def describe_option(self, flag):
        """
        print the description provided in the binary help string for a given flag
        """
        if self.has_option(flag):
            return self.options[[key for key in self.options.keys() if flag in key][0]]
        else:
            print('The flag "{}" is not listed in the help string.'.format(flag))

    def assemble_args(self, **options):

        options = validate_with_humanized_errors(options, cudaDeconSchema)

        arglist = []
        for o in options:
            # convert LLSpy variable naming conventions to cudaDeconv names
            # TODO: consider uniying everything to cudaDeconv?
            optname = o
            convert_name = {
                'nIters': 'RL',
            }
            if optname in convert_name:
                optname = convert_name[optname]

            # assemble the argument list
            if self.has_option_longname(optname):
                # expand listed items like --MIP 0 0 0
                if optname in ('MIP', 'rMIP', 'crop'):
                        arglist.append('--' + optname)
                        [arglist.append(str(i)) for i in options[o]]
                # booleans only get a single flag
                elif isinstance(options[o], bool):
                    if options[o]:
                        arglist.extend(['--' + optname])
                # otherwise just add the argument
                else:
                    arglist.extend(['--' + optname, str(options[o])])
            else:
                logging.warn('Warning: option not recognized, ignoring: {}'.format(o))

        return arglist

    def help(self):
        """print the help string provided by cudaDeconv"""
        print(self.helpstring)


class CUDAbinException(Exception):
    """
    Generic exception indicating anything relating to the execution
    of cudaDeconDeskew. A string containing an error message should be supplied
    when raising this exception.
    """
    pass


class CUDAProcessError(CUDAbinException):
    """
    Exception to describe an cudaDeconv execution error.
    """

    def __init__(self, cmd, rtnCode, output):
        """
        cmd -- The string or byte array of the cudaDeconv command ran
        rtnCode -- The process return code
        output -- Any output from the failed process
        """
        self.cmd = cmd
        self.rtnCode = rtnCode
        self.output = output
        self.message = "cudaDeconv returned a non-zero exit code"


class CUDAbinResult():
    """
    Holds the result of running an cudaDeconv command.
    """

    def __init__(self, rtnCode, output):
        """
        rtnCode -- The exit code
        output -- Any output from the process
        """
        self.rtnCode = rtnCode
        self.output = output
