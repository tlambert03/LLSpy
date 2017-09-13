# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from codecs import open
from os import path
import sys

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    readme = f.read()

with open('LICENSE.txt') as f:
    license = f.read()

# get specific library by platform
if sys.platform.startswith('darwin'):
    PLATFORM = 'darwin'
    PACKAGE_DATA = [
            path.join('bin', 'cudaDeconv.app'),
            path.join('bin', 'otfviewer.app'),
            path.join('bin', 'radialft.app'),
            path.join('lib', 'libcudaDeconv.dylib'),
            path.join('lib', 'libradialft.dylib'),
    ]
elif sys.platform.startswith('win32'):
    PLATFORM = 'win32'
    PACKAGE_DATA = [
            path.join('bin', 'cudaDeconv.exe'),
            path.join('bin', 'otfviewer.exe'),
            path.join('bin', 'radialft.exe'),
            path.join('bin', 'libfftw3f-3.dll'),
            path.join('lib', 'libcudaDeconv.dll'),
            path.join('lib', 'libradialft.dll'),
    ]
else:
    PLATFORM = 'nix'
    PACKAGE_DATA = [
            path.join('bin', 'cudaDeconv'),
            path.join('bin', 'otfviewer'),
            path.join('bin', 'radialft'),
            path.join('lib', 'libcudaDeconv.so'),
            path.join('lib', 'libradialft.so'),
    ]


setup(
    name='llspy',
    version='0.1.0',
    description='Lattice Light Sheet Processing Tools',
    long_description=readme,
    author='Talley Lambert',
    author_email='talley.lambert@gmail.com',
    url='https://github.com/tlambert03/LLSpy2',
    license=license,
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
    ],
    entry_points={
            'console_scripts': [
                'lls=llspy.lls:cli',
                'lls-gui=llspy.gui.llspygui:main'
            ],
    },
)
