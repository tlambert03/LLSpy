# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from codecs import open
import os
from os import path
import sys

with open('llspy/version.py') as f:
    exec(f.read())

INCLUDELIBS = False
HERE = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(HERE, 'README.rst'), encoding='utf-8') as f:
    README = f.read()

with open('LICENSE.txt') as f:
    LICENSE = f.read()

if sys.platform.startswith('win32'):
    DATA_FILES = [
        ('Library\\bin', ['llspy\\bin\\libfftw3f-3.dll'])
    ]
elif sys.platform.startswith('darwin'):
    DATA_FILES = [
        ('lib', [os.path.join('llspy', 'lib', f) for f in
                 os.listdir('llspy/lib') if f.endswith('dylib')])
    ]
else:
    DATA_FILES = []

PACKAGE_DATA = [path.join('gui', 'guiDefaults.ini'),
                path.join('gui', 'img_window.ui')]

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
    license='',
    packages=find_packages(exclude=('tests', 'docs', 'pyinstaller')),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',

        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],

    python_requires='>=3.5',
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
        'matplotlib'
        'spimagine',
        'gputools'
    ],
    entry_points={
            'console_scripts': [
                'lls = llspy.lls:cli',
                'lls-gui = llspy.gui.llspygui:main'
            ],
    },
)
