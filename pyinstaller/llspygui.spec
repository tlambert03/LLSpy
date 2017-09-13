# -*- mode: python -*-
# this requires the lib directory to be on the library path when freezing
# export DYLD_LIBRARY_PATH="./lib/"
# also requires dev version of pyinstaller and python 3.5 (not 3.6)
# pip install git+https://github.com/pyinstaller/pyinstaller.git

import sys
import logging

###############

block_cipher = None
APP_NAME = 'LLSpy'
APP_PATH = '/Users/talley/DropboxHMS/Python/llspy2'
DEBUG = False
ONEFILE = False
WINDOWED = False
UPX = False

#####################

# get specific library by platform
if sys.platform.startswith('darwin'):
	logging.info('COMPILING FOR MAC')
	binpaths = [('bin/darwin/cudaDeconv', '.')]
# ('lib/libcudaDeconv.dylib', '.'),
# ('lib/libradialft.dylib', '.')
elif sys.platform.startswith('win32'):
	logging.info('COMPILING FOR WINDOWS')
	binpaths = [('bin/win32/cudaDeconv.exe', '.'),
				('bin/win32/libfftw3f-3.dll', '.'),
				('lib/win32/libcudaDeconv.dll', '.'),
				('lib/win32/libradialft.dll', '.')]
else:
	logging.info('COMPILING FOR UNIX')
	binpaths = [('bin/nix/cudaDeconv', '.'),
				('lib/nix/libcudaDeconv.so', '.'),
				('lib/nix/libradialft.so', '.'),
				('/opt/anaconda3/lib/libstdc++.so.6', '.')]

datafiles = [('llspy/gui/guiDefaults.ini', 'gui'),
			('llspy/FlashParams.tif', '.')]

a = Analysis(['llspy/gui/llspygui.py'],
			pathex=[APP_PATH],
			binaries=binpaths,
			datas=datafiles,
			hiddenimports=['pywt._extensions._cwt'],
			hookspath=[],
			runtime_hooks=[],
			excludes=[],
			win_no_prefer_redirects=False,
			win_private_assemblies=False,
			cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
	a.scripts,
	# Static link the Visual C++ Redistributable DLLs if on Windows
	a.binaries + [('msvcp100.dll', 'C:\\Windows\\System32\\msvcp100.dll', 'bin'),
				('msvcr100.dll', 'C:\\Windows\\System32\\msvcr100.dll', 'bin'),
				('cufft64_80.dll', 'C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v8.0\\bin\\cufft64_80.dll', 'bin')]
				if sys.platform == 'win32' else a.binaries,
	a.zipfiles,
	a.datas,
	name=APP_NAME,
	debug=DEBUG,
	strip=False,
	upx=UPX,
	version=None,  # optional windows version file
	# runtime_tmpdir=None,  #  used for --onefile
	console=(not WINDOWED),
	icon='_assets/llspy1.ico')

if not ONEFILE:
	coll = COLLECT(exe,   # only without --onefile
				a.binaries,
				a.zipfiles,
				a.datas,
				strip=False,
				upx=UPX,
				name=APP_NAME)

if sys.platform == 'darwin' and WINDOWED:
	app = BUNDLE(exe,
				name=APP_NAME+'.app',
				icon='_assets/llspy1.icns',
				bundle_identifier='com.llspy.llspygui',
				info_plist={
					'NSHighResolutionCapable': 'True'
				})
