import sys
from collections import OrderedDict
from argparse import ArgumentParser

from faice.agent.main import main as agent_main
from faice.schemas.main import main as schemas_main

from faice.agent.main import DESCRIPTION as AGENT_DESCRIPTION
from faice.schemas.main import DESCRIPTION as SCHEMAS_DESCRIPTION


SCRIPT_NAME = 'faice'

VERSION = '2.0.0'

DESCRIPTION = 'FAICE Copyright (C) 2017  Christoph Jansen. This software is distributed under the Apache 2.0 ' \
              'LICENSE and is part of the Curious Containers project (https://www.curious-containers.cc).'

MODES = OrderedDict([
    ('agent', {'main': agent_main, 'description': AGENT_DESCRIPTION}),
    ('schemas', {'main': schemas_main, 'description': SCHEMAS_DESCRIPTION})
])


def main():
    sys.argv[0] = SCRIPT_NAME

    parser = ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        '-v', '--version', action='version', version=VERSION
    )
    subparsers = parser.add_subparsers(title='tools')

    sub_parser = None
    for key, val in MODES.items():
        sub_parser = subparsers.add_parser(key, help=val['description'], add_help=False)

    if len(sys.argv) < 2:
        parser.print_help()
        exit()

    _ = parser.parse_known_args()
    sub_args = sub_parser.parse_known_args()

    mode = MODES[sub_args[1][0]]['main']
    sys.argv[0] = '{} {}'.format(SCRIPT_NAME, sys.argv[1])
    del sys.argv[1]
    exit(mode())
