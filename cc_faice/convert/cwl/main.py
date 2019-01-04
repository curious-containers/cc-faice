from argparse import ArgumentParser

from jsonschema import validate
from jsonschema.exceptions import ValidationError

from cc_core.commons.files import dump_print, load_and_read, wrapped_print
from cc_core.commons.schemas.cwl import cwl_schema


DESCRIPTION = 'Read cli section of a REDFILE and write it to stdout in the specified format.'


def attach_args(parser):
    parser.add_argument(
        'red_file', action='store', type=str, metavar='REDFILE',
        help='REDFILE (json or yaml) containing an experiment description as local PATH or http URL.'
    )
    parser.add_argument(
        '--format', action='store', type=str, metavar='FORMAT', choices=['json', 'yaml', 'yml'], default='yaml',
        help='Specify FORMAT for generated data as one of [json, yaml, yml]. Default is yaml.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    return run(**args.__dict__)


def run(red_file, format):
    red_data = load_and_read(red_file, 'REDFILE')

    if 'cli' not in red_data:
        wrapped_print([
            'ERROR: REDFILE does not contain cli section.'
        ], error=True)
        return 1

    cli = red_data['cli']

    try:
        validate(cli, cwl_schema)
    except ValidationError as e:
        wrapped_print([
            'ERROR: REDFILE does not comply with jsonschema.',
            e.context
        ], error=True)
        return 1

    dump_print(cli, format)
