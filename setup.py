#!/usr/bin/env python3

from distutils.core import setup

description = 'FAICE (Fair Collaboration and Experiments) is part of the Curious Containers project and enables' \
              'researchers to perform and distribute reproducible data-driven experiments.'

setup(
    name='faice',
    version='2.0.0',
    summary=description,
    description=description,
    author='Christoph Jansen',
    author_email='Christoph.Jansen@htw-berlin.de',
    url='https://github.com/curious-containers/cc-faice',
    packages=[
        'faice',
        'faice.agent',
        'faice.schema_list',
        'faice.schema_export'
    ],
    entry_points={
        'console_scripts': ['faice=faice.main:main']
    },
    license='AGPL-3.0',
    platforms=['any'],
    install_requires=[
        'cc-core'
    ]
)
