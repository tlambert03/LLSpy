import unittest
import sys
sys.path.append('..')

from llspy.core import parse


class FilenameTests(unittest.TestCase):

	def setUp(self):
		self.example_name = 'cell5_ch0_stack0006_488nm_'\
			'0005280msec_0020936553msecAbs.tif'
		self.dict = {'abstime': 20936553, 'basename': 'cell5',
			'channel': 0, 'reltime': 5280, 'stack': 6, 'wave': 488}

	def tearDown(self):
		# code to do tear down
		pass

	def test_parse_filename(self):
		p = parse.parse_filename(self.example_name)
		self.assertEqual(p, self.dict)

	def test_gen_filename(self):
		p = parse.gen_filename(self.dict)
		self.assertEqual(p, self.example_name)
