#! /usr/bin/env python
from __future__ import print_function

import sys
import os
import shutil
from builtins import input

sys.path.append(os.path.join(os.path.dirname(sys.argv[0]), '..'))
from llspy import config
from llspy.llsdir import LLSdir, LLSpyError

default_otfdir = config.__OTFPATH__


def main(argv=None):
	"""Command line usage main function."""
	if float(sys.version[0:3]) < 2.6:
		print("This script requires Python version 2.6 or better.")
		print("This is Python version %s" % sys.version)
		return 0
	if argv is None:
		argv = sys.argv

	import argparse

	parser = argparse.ArgumentParser(
		description='Helper program for processing Lattice Light Sheet data')
	arg = parser.add_argument
	arg('path', help='folder or folders to process')
	arg('-i', '--iters', type=int, default=8,
		help='number of RL-deconvolution iterations (default=8)')
	arg('-b', '--background', type=int, default=None,
		help="Specify image background (default is to autodetect)")
	arg('-w', '--width', type=int, default=None,
		help="width of image after deskewing.  \
		Default is to autocrop. 0 = full frame")
	arg('-R', '--rotate', action='store_true', default=False,
		help="rotate image to coverslip coordinates after deconvolution")
	arg('-M', '--MIP', type=int, nargs=3, default=(0, 0, 1),
		help="Save max-intensity projection after deconvolution \
		along x, y, or z axis; takes 3 binary numbers separated by space: 0 0 1")
	arg('-m', '--rMIP', type=int, nargs=3, default=(0, 0, 0),
		help="Save max-intensity projection after deskewing \
		along x, y, or z axis; takes 3 binary numbers separated by space: 0 0 1")
	arg('-s', '--sepmips', dest='mipmerge', action='store_false', default=True,
		help="don't combine MIP files into single hyperstack")
	arg('-u', '--uint16', action='store_true', help="save deconvolved as 16 bit",
		default=False)
	arg('-p', '--bleachCorrection', action='store_true',
		help="perform bleach correction on timelapse data", default=False),
	arg('--otfdir', help="specify directory with otfs.\n\
		OTFs should be named (e.g.): 488_otf.tif", default=None)
	arg('-c', '--correct', action='store_true', default=False,
		help="Correct Flash pixels before processing")
	arg('-C', '--withMedian', dest='median', action='store_true', default=False,
		help="additionally correct with Phillip Keller median filter method")
	arg('-z', '--compress', action='store_true', default=False,
		help="Compress raw files after processing")
	arg('--batch', action='store_true', default=False,
		help="batch process folder: \
				look for all subfolders with a Settings.txt file")
	arg('-r', '--reprocess', action='store_true', default=False,
		help="Process even if the folder already has a processingLog JSON file, \
		(otherwise skip)")
	arg('-v', '--verbose', action='store_true', default=False)
	arg('-q', '--quiet', action='store_true', default=False)

	options = parser.parse_args()
	if options.median:
			options.correct = True
	path = os.path.abspath(options.path)

	# fix path errors
	if not path:
		path = input(
			"\nPlease type in the path to your file and press 'Enter': ")
		if not path:
			parser.error("No file specified")
		if not os.path.isdir(path):
			parser.error("Path must be an existing directory")

	E = LLSdir(path)

	# batch processing
	if not options.batch and not E.has_settings:
		parser.error('not a LLS data folder, use --batch for batch processing')

	# autodetect width by default
	if options.width is None:
			options.width = 'auto'

	# allow for provided OTF directory
	if not default_otfdir and options.otfdir is None:
		print('Could not find OTF directory at {}'.format(default_otfdir))
		sys.exit('Please specify where the OTFs are with --otfdir')
	elif options.otfdir is None:
		options.otfdir = default_otfdir

	# if not doing decon, but MIPs requested, do raw mips instead
	if (options.iters == 0 and
		any(list(options.deconMIP)) and
		not any(list(options.rawMIP))):
			options.rawMIP = options.deconMIP
			options.deconMIP = (0, 0, 0)

	def procfolder(E, options):
		# check whether folder has already been processed by the presence of a
		# ProcessingLog.txt file
		if E.has_been_processed() and not options.reprocess:
			print("Folder already appears to be processed: {}".format(E.path))
			print("Skipping ... use the '--reprocess' flag to force reprocessing")
			return 0

		if options.reprocess and E.raw_is_compressed():
			# uncompress the raw files first...
			E.decompress(verbose=options.verbose)
			# if reprocessing, look for a top level MIPs folder and remove it
			if E.path.joinpath('MIPs').exists():
				shutil.rmtree(E.path.joinpath('MIPs'))

		print("\n")
		print("#" * (int(len(str(E.path))) + 24))
		print("##    processing: %s    ##" % str(E.path))
		print("#" * (int(len(str(E.path))) + 24))
		print("\n")

		if options.correct:
			docorrection = True
			if E.is_corrected():
				import select
				print("Corrected folder already exists!  Use it?"
						"(y/n 8 seconds to answer)")
				i, o, e = select.select([sys.stdin], [], [], 8)
				if (i):
					if sys.stdin.readline().strip()[0].lower() == 'y':
						print("Using already corrected files...")
						docorrection = False
					else:
						print("recreating corrected files...")
						docorrection = True
				else:
					print("timed out... recreating corrected Files...")

			if docorrection:
				try:
					E.correct_flash(target='parallel', median=options.median)
				except Exception:
					raise RuntimeError(
						"ERROR: problem with correcting dataset: {}".format(E.path))

		try:
			S = E.autoprocess(**vars(options))
			logdict = None
		except LLSpyError as e:
			print(e)


	if options.batch:
		try:
			print("Looking for data folders in %s... " % path)
			subfolders = get_subfolders_containing_filepattern(
				path, filepattern='*Settings.txt')
			print("found the following LLS data folders:")
			for folder in subfolders:
					print(folder.split(path)[1])
			for folder in subfolders:
					procfolder(folder)
			sys.exit('\n\nDone batch processing!')
		except:
			raise
	else:
		try:
			procfolder(E, options)
			sys.exit('Done!')
		except:
			raise
	sys.exit(0)


if __name__ == "__main__":
	sys.exit(main())