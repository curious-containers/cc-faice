import sys
import jsonschema
from argparse import ArgumentParser

from cc_core.commons.schema_map import schemas
from cc_core.commons.files import load_and_read


DESCRIPTION = 'Validate data against schema. Returns code 0 if data is valid.'


def attach_args(parser):
    parser.add_argument(
        'schema', action='store', type=str, metavar='SCHEMA',
        help='SCHEMA as in "faice schemas list".'
    )
    parser.add_argument(
        'file', action='store', type=str, metavar='FILE',
        help='FILE (json or yaml) to be validated as local path or http url.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    return run(**args.__dict__)


def run(schema, file):
    if schema not in schemas:
        print('Schema "{}" not found. Use "faice schema list" for available schemas.'.format(schema), file=sys.stderr)
        return 1

    data = load_and_read(file, 'FILE')
    jsonschema.validate(data, schemas[schema])

    return 0
