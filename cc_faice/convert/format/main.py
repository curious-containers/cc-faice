from argparse import ArgumentParser

from cc_core.commons.exceptions import print_exception, AgentError
from cc_core.commons.files import dump_print, load_and_read


DESCRIPTION = 'Read an arbitrary JSON or YAML file and convert it into the specified format.'


def attach_args(parser):
    parser.add_argument(
        'file', action='store', type=str, metavar='FILE',
        help='FILE (json or yaml) to be converted into specified FORMAT as local path or http url.'
    )
    parser.add_argument(
        '--format', action='store', type=str, metavar='FORMAT', choices=['json', 'yaml', 'yml'], default='yaml',
        help='Specify FORMAT for generated data as one of [json, yaml, yml]. Default is yaml.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    return run(**args.__dict__, fmt=args.format)


def run(file, fmt, **_):
    try:
        data = load_and_read(file, 'FILE')
    except AgentError as e:
        print_exception(e)
        return 1

    dump_print(data, fmt)
    return 0
