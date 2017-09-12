# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from codecs import open
from os import path
import sys

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.txt'), encoding='utf-8') as f:
    readme = f.read()

with open('LICENSE.txt') as f:
    license = f.read()

# get specific library by platform
if sys.platform.startswith('darwin'):
    PLATFORM = 'darwin'
elif sys.platform.startswith('win32'):
    PLATFORM = 'win32'
else:
    PLATFORM = 'nix'


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
    package_data={'llspy': [path.join('bin', PLATFORM, '*'), 'lib/*']},
    install_requires=[
        'numpy',
        'scipy',
        'tifffile',
        'numba',
        'scikit-image',
        'voluptuous',
        'click',
        'watchdog',
        'pyqt5',
    ],
    entry_points={
            'console_scripts': [
                'lls=llspy.lls:cli',
            ],
        },

)
