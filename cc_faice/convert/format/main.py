from argparse import ArgumentParser

from cc_core.commons.files import dump_print, load_and_read


DESCRIPTION = 'Read an arbitrary JSON or YAML file and convert it into the specified format.'


def attach_args(parser):
    parser.add_argument(
        'file', action='store', type=str, metavar='FILE',
        help='FILE (json or yaml) to be converted into specified DUMP_FORMAT as local path or http url.'
    )
    parser.add_argument(
        '--dump-format', action='store', type=str, metavar='DUMP_FORMAT', choices=['json', 'yaml', 'yml'],
        default='yaml', help='Dump format for data written to files or stdout, choices are "json" or "yaml", default '
                             'is "yaml".'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    run(**args.__dict__)
    return 0


def run(file, dump_format):
    data = load_and_read(file, 'FILE')
    dump_print(data, dump_format)
