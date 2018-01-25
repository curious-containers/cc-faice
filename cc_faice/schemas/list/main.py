from argparse import ArgumentParser

from cc_core.commons.schema_map import schemas
from cc_core.commons.files import dump_print


DESCRIPTION = 'List of all available jsonschemas defined in cc-core.'


def attach_args(parser):
    parser.add_argument(
        '--dump-format', action='store', type=str, metavar='DUMP_FORMAT', choices=['json', 'yaml', 'yml'],
        default='yaml', help='Dump format for data written to files or stdout, default is "yaml".'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    run(**args.__dict__)
    return 0


def run(dump_format):
    dump_print({'schemas': list(schemas.keys())}, dump_format)
