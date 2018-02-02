#!/usr/bin/env python3

from distutils.core import setup

description = 'FAICE (Fair Collaboration and Experiments) is part of the Curious Containers project and enables' \
              'researchers to perform and distribute reproducible data-driven experiments.'

setup(
    name='cc-faice',
    version='2.0.1',
    summary=description,
    description=description,
    author='Christoph Jansen',
    author_email='Christoph.Jansen@htw-berlin.de',
    url='https://github.com/curious-containers/cc-faice',
    packages=[
        'cc_faice',
        'cc_faice.agent',
        'cc_faice.agent.cwl',
        'cc_faice.agent.red',
        'cc_faice.commons',
        'cc_faice.export',
        'cc_faice.file_server',
        'cc_faice.schemas',
        'cc_faice.schemas.list',
        'cc_faice.schemas.show',
        'cc_faice.schemas.validate'
    ],
    entry_points={
        'console_scripts': ['faice=cc_faice.main:main']
    },
    license='AGPL-3.0',
    platforms=['any'],
    install_requires=[
        'cc-core >= 2.0, < 2.1',
        'flask',
        'werkzeug',
        'docker',
        'Jinja2',
        'jsonschema'
    ]
)
