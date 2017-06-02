import io

import setuptools

with io.open('README.rst', encoding='utf-8') as readme:
    long_description = readme.read()

name = 'khartoum'
description = (
    "A simple app for http serving of static files from MongoDB's GridFS "
    "filesystem."
)


params = dict(
    name=name,
    use_scm_version=True,
    author='YouGov, Plc.',
    author_email='open-source@yougov.com',
    description=description or name,
    long_description=long_description,
    url='https://github.com/yougov/' + name,
    packages=setuptools.find_packages(),
    install_requires=[
        'PyYAML>=3.10',
        'gevent>=1.1b6,<2',
        'pymongo>=2.4,<3dev',
        'appsettings==0.3.2',
        'six',
    ],
    extras_require={
        'testing': [
            'pytest >= 2.8',
        ],
    },
    setup_requires=[
        'setuptools_scm>=1.15.0',
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
    ],
    entry_points = {
    },
)

__name__ == '__main__' and setuptools.setup(**params)
