import os
import re
import subprocess
import warnings
from llspy.config import config

default_cudaBinary = config.__CUDADECON__


# TODO: this would probable be better implemented as a voluptuous schema
# FIXME: passing of the binary is messed up... is it a string?  is it None?
def assemble_args(binary, indir, filepattern, otf, **options):
	if not isinstance(binary, CUDAbin):
		if isinstance(binary, str):
			try:
				binary = CUDAbin(binPath=binary)
			except Exception:
				CUDAbinException("Not a valid cudaDeconv binary: {}".format(binary))
		else:
			binary = CUDAbin()

	arglist = [indir, filepattern, otf]
	for o in options:
		if binary.has_option_longname(o):
			if 'MIP' in o:
				if options[o] is not None and len(options[o]) == 3:
					arglist.extend(['--' + o, str(options[o][0]),
						str(options[o][1]), str(options[o][2])])
			elif isinstance(options[o], bool):
				if options[o]:
					arglist.extend(['--' + o])
			else:
				arglist.extend(['--' + o, str(options[o])])
		else:
			warnings.warn('Warning: option not recognized, ignoring: {}'.format(o))
	return arglist


class CUDAbin(object):
	"""
	Wrapper class for Lin Shao's cudaDeconv binary
	"""
	def __init__(self, binPath=default_cudaBinary):
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
			self._run_command((binPath + " -h").split())
			return True
		else:
			raise CUDAbinException(
				'cudaDeconv could not be located or is not executable.')

	def process(self, indir, filepattern, otf, **options):
		cmd = [self.path]
		cmd.extend(assemble_args(self, indir, filepattern, otf, **options))
		self._run_command(cmd)

	def _run_command(self, cmd):
		"""
		Execute an cudaDeconv command via the subprocess module.
		If the process exits with a exit status of zero, the output is
		encapsulated into a CUDAbinResult and returned.
		Otherwise, an CUDAProcessError is thrown.
		"""
		try:
			output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
			return CUDAbinResult(0, output)
		except subprocess.CalledProcessError as e:
				raise CUDAProcessError(e.cmd, e.returncode, e.output)

	def _get_options(self):
		"""
		query the binary help output and output a list of possible flags
		and descriptions
		"""
		cmd = self.path + " -h "
		h = self._run_command(cmd.split())
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