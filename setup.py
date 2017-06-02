import setuptools


params = dict(
    name='khartoum',
    use_scm_version=True,
    author='YouGov, Plc.',
    author_email='open-source@yougov.com',
    packages=setuptools.find_packages(),
    install_requires=[
        'PyYAML>=3.10',
        'gevent>=1.1b6,<2',
        'pymongo>=2.4,<3dev',
        'appsettings==0.3.2',
    ],
    setup_requires=[
        'setuptools_scm>=1.15.0',
    ],
    entry_points = {
        'console_scripts': [
            'khartoum = khartoum.server:main',
        ],
    },
    description=(
        "A simple app for http serving of static files from MongoDB's GridFS "
        "filesystem."
    ),
    long_description=open('README.rst').read(),
    url='https://github.com/yougov/khartoum',
)

__name__ == '__main__' and setuptools.setup(**params)
