#!/usr/bin/python
from setuptools import setup, find_packages

setup(
    name='khartoum',
    version='0.3.3',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    packages=find_packages(),
    install_requires=[
        'PyYAML>=3.10',
        'gevent>=1.1b6,<2',
        'pymongo>=2.1.1,<3dev',
        'appsettings==0.3.2',
    ],
    entry_points = {
        'console_scripts': [
            'khartoum = khartoum.server:main',
        ],
    },
    description=(
        "A simple app for http serving of static files from MongoDB's GridFS "
        "filesystem."),
    long_description=open('README.rst').read(),
    url='https://bitbucket.org/btubbs/khartoum',
)
