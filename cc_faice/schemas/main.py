import sys
from collections import OrderedDict
from argparse import ArgumentParser

from cc_faice.schemas.list.main import main as list_main
from cc_faice.schemas.show.main import main as show_main

from cc_faice.schemas.list.main import DESCRIPTION as LIST_DESCRIPTION
from cc_faice.schemas.show.main import DESCRIPTION as SHOW_DESCRIPTION


SCRIPT_NAME = 'faice schemas'

DESCRIPTION = 'List or export jsonschemas defined in cc-core.'

MODES = OrderedDict([
    ('list', {'main': list_main, 'description': LIST_DESCRIPTION}),
    ('show', {'main': show_main, 'description': SHOW_DESCRIPTION})
])


def main():
    sys.argv[0] = SCRIPT_NAME

    parser = ArgumentParser(description=DESCRIPTION)
    subparsers = parser.add_subparsers(title='modes')

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