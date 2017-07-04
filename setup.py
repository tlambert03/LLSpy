# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='LLSpy',
    version='0.1.0',
    description='Lattice Light Sheet Processing Tools',
    long_description=readme,
    author='Talley Lambert',
    author_email='talley.lambert@gmail.com',
    url='https://github.com/tlambert03/LLSpy',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)
