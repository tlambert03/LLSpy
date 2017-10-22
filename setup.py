# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from codecs import open
from os import path
import sys

with open('llspy/version.py') as f:
    exec(f.read())

INCLUDELIBS = False
HERE = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(HERE, 'README.rst'), encoding='utf-8') as f:
    README = f.read()

with open('LICENSE') as f:
    LICENSE = f.read()

if sys.platform.startswith('win32'):
    DATA_FILES = []
elif sys.platform.startswith('darwin'):
    DATA_FILES = []
else:
    DATA_FILES = []

PACKAGE_DATA = [path.join('gui', 'guiDefaults.ini'),
                path.join('gui', 'img_window.ui'),
                path.join('gui', 'before_after.png'),
                path.join('gui', 'logo_dark.png'),
                path.join('gui', 'logo_light.png')]

if INCLUDELIBS:
    # add specific library by platform
    if sys.platform.startswith('darwin'):
        PACKAGE_DATA += [
                'bin/*.app',
                'lib/*.dylib',
        ]
    elif sys.platform.startswith('win32'):
        PACKAGE_DATA += [
                path.join('bin', '*.exe'),
                path.join('lib', '*.dll'),
        ]
    else:
        PACKAGE_DATA += [
                'bin/cudaDeconv',
                'bin/otfviewer',
                'bin/radialft',
                'lib/*.so',
        ]


setup(
    name='llspy',
    version=__version__,
    description='Lattice Light Sheet Processing Tools',
    long_description=README,
    author='Talley Lambert',
    author_email='talley.lambert@gmail.com',
    url='https://github.com/tlambert03/LLSpy2',
    license='BSD 3-clause',
    packages=find_packages(exclude=('tests', 'docs', 'pyinstaller')),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Visualization'

    ],
    python_requires='>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,!=3.4.*',
    package_data={
        'llspy': PACKAGE_DATA,
    },
    data_files=DATA_FILES,
    install_requires=[
        'numpy',
        'scipy',
        'tifffile',
        'numba',
        'voluptuous',
        'click',
        'watchdog',
        'pyqt5',
        'matplotlib',
        'spimagine',
        'gputools',
        'raven',
    ],
    entry_points={
            'console_scripts': [
                'lls = llspy.bin.llspy_cli:cli',
                'lls-gui = llspy.bin.llspy_gui:main'
            ],
    },
)
