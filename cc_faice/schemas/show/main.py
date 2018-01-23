import sys
import json
from argparse import ArgumentParser

from cc_core.commons.schema_map import schemas
from cc_core.commons.files import dump_print


DESCRIPTION = 'Write a jsonschema to stdout.'


def attach_args(parser):
    parser.add_argument(
        'schema', action='store', type=str, metavar='SCHEMA',
        help='SCHEMA as in "faice schema list".'
    )
    parser.add_argument(
        '--dump-format', action='store', type=str, metavar='DUMP_FORMAT', choices=['json', 'yaml'], default='json',
        help='Dump format for data generated or aggregated by the agent.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    return run(**args.__dict__)


def run(schema, dump_format):
    if schema not in schemas:
        print('Schema "{}" not found. Use "faice schema list" for available schemas.'.format(schema), file=sys.stderr)
        return 1

    dump_print(schemas[schema], dump_format)
    return 0
