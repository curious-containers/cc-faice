import sys
import json
from argparse import ArgumentParser

from cc_core.commons.schema_list import schemas


DESCRIPTION = 'Write a certain jsonschema to stdout.'


def attach_args(parser):
    parser.add_argument(
        'schema', action='store', type=str, metavar='SCHEMA',
        help='SCHEMA as shown by schema-list.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    return run(**args.__dict__)


def run(schema):
    for name, s in schemas:
        if name == schema:
            print(json.dumps(s, indent=4))
            return 0

    print('Schema "{}" not found. Use schema-list for available schemas.'.format(schema), file=sys.stderr)
    return 1
