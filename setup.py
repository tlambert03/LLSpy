# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from codecs import open
from os import path
import sys

INCLUDELIBS = False
HERE = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(HERE, 'README.rst'), encoding='utf-8') as f:
    README = f.read()

with open('LICENSE.txt') as f:
    LICENSE = f.read()


PACKAGE_DATA = ['gui/guiDefaults.ini']


if sys.platform.startswith('win32'):
    PACKAGE_DATA += 'bin/libfftw3f-3.dll'


if INCLUDELIBS:
    # add specific library by platform
    if sys.platform.startswith('darwin'):
        PACKAGE_DATA += [
                'bin/*.app',
                'lib/*.dylib',
        ]
    elif sys.platform.startswith('win32'):
        PACKAGE_DATA += [
                'bin/*.exe',
                'lib/*.dll',
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
    version='0.1.0',
    description='Lattice Light Sheet Processing Tools',
    long_description=README,
    author='Talley Lambert',
    author_email='talley.lambert@gmail.com',
    url='https://github.com/tlambert03/LLSpy2',
    license=LICENSE,
    packages=find_packages(exclude=('tests', 'docs')),
    python_requires='>=3.5',
    package_data={
        'llspy': PACKAGE_DATA,
    },
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
    ],
    entry_points={
            'console_scripts': [
                'lls=llspy.lls:cli',
                'lls-gui=llspy.gui.llspygui:main'
            ],
    },
)
