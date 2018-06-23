from argparse import ArgumentParser

from cc_core.commons.files import load_and_read, file_extension, wrapped_print, dump
from cc_core.commons.red import red_validation, convert_batch_experiment


DESCRIPTION = 'Convert batches from a single RED_FILE into separate files containing only one batch each.'


def attach_args(parser):
    parser.add_argument(
        'red_file', action='store', type=str, metavar='RED_FILE',
        help='RED_FILE (json or yaml) containing an experiment description as local path or http url.'
    )
    parser.add_argument(
        '--dump-format', action='store', type=str, metavar='DUMP_FORMAT', choices=['json', 'yaml', 'yml'],
        default='yaml', help='Dump format for data written to files or stdout, choices are "json" or "yaml", default '
                             'is "yaml".'
    )
    parser.add_argument(
        '--dump-prefix', action='store', type=str, metavar='DUMP_PREFIX', default='dumped_',
        help='Name prefix for files dumped to storage, default is "dumped_".'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    return run(**args.__dict__)


def run(red_file, dump_format, dump_prefix):
    ext = file_extension(dump_format)

    red_data = load_and_read(red_file, 'RED_FILE')
    red_validation(red_data, False)

    if 'batches' not in red_data:
        wrapped_print([
            'ERROR: RED_FILE does not contain batches.'
        ], error=True)
        return 1

    for batch in range(len(red_data['batches'])):
        batch_data = convert_batch_experiment(red_data, batch)
        dumped_batch_file = '{}batch_{}.{}'.format(dump_prefix, batch, ext)
        dump(batch_data, dump_format, dumped_batch_file)

    return 0
