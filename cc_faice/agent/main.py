import sys
from collections import OrderedDict
from argparse import ArgumentParser

from cc_faice.agent.cwl.main import main as cwl_main
from cc_faice.agent.red.main import main as red_main

from cc_faice.agent.cwl.main import DESCRIPTION as CWL_DESCRIPTION
from cc_faice.agent.red.main import DESCRIPTION as RED_DESCRIPTION


SCRIPT_NAME = 'faice agent'

DESCRIPTION = 'Run a RED experiment or a CWL CommandLineTool.'

MODES = OrderedDict([
    ('cwl', {'main': cwl_main, 'description': CWL_DESCRIPTION}),
    ('red', {'main': red_main, 'description': RED_DESCRIPTION})
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
