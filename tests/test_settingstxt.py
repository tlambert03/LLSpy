import unittest
import datetime
import sys
import os
sys.path.append('..')

from llspy.settingstxt import LLSsettings

TESTSDIR = os.path.dirname(os.path.abspath(__file__))

class SettingsTests(unittest.TestCase):

	def setUp(self):
		self.settings_dict = {
		'acq_mode': 'Z stack',
		'basename': 'example_Settings.txt',
		'camera': {'cycle': '0.00330',
				'cycleHz': '302.72 Hz',
				'exp': '0.00202',
				'model': 'C11440-22C',
				'name': '"Orca4.0"',
				'pixel': 6.5,
				'roi': [913, 901, 1232, 1156],
				'serial': '100740',
				'trigger_mode': '"SLM -> Cam"'},
		'channel': {0: {'S PZT': {'interval': '0.3', 'numpix': '88', 'offset': '55'},
					'X Galvo': {'interval': '0.1', 'numpix': '51', 'offset': '0'},
					'Z PZT': {'interval': '0', 'numpix': '88', 'offset': '12'},
					'exfilter': 'N/A',
					'exposure': '2',
					'laser': '488',
					'numstacks_requested': '3',
					'power': '3'},
				1: {'S PZT': {'interval': '0.3', 'numpix': '88', 'offset': '55'},
					'X Galvo': {'interval': '0.1', 'numpix': '51', 'offset': '0'},
					'Z PZT': {'interval': '0', 'numpix': '88', 'offset': '12'},
					'exfilter': 'N/A',
					'exposure': '2',
					'laser': '560',
					'numstacks_requested': '3',
					'power': '3'}},
		'cycle_lasers': 'per Z',
		'date': datetime.datetime(2016, 10, 7, 17, 50, 37),
		'mag': 63.8,
		'mask': {'innerNA': 0.42, 'outerNA': 0.5},
		'pixel_size': 0.1019,
		'sheet_angle': 31.5,
		'software_version': '4.02893.0012',
		'z_motion': 'Sample piezo'
		}
		self.example_file_path = os.path.join(TESTSDIR, 'testdata', 'example_Settings.txt')
		self.setobj = LLSsettings(self.example_file_path)

	def tearDown(self):
		# code to do tear down
		pass

	def test_parse_settings(self):
		for k in self.setobj.__dict__:
			if not k in ['path', 'raw_text', 'SPIMproject']:
				self.assertEqual(self.setobj.__dict__[k], self.settings_dict[k])

