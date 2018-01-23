from argparse import ArgumentParser


DESCRIPTION = 'Export RED_FILE to pure CWL with support for RED connectors (remote input and output files).'


def attach_args(parser):
    parser.add_argument(
        'red_file', action='store', type=str, metavar='RED_FILE',
        help='RED_FILE (json or yaml) containing an experiment description as local path or http url.'
    )
    parser.add_argument(
        '-j', '--jinja-file', action='store', type=str, metavar='JINJA_FILE',
        help='JINJA_FILE (json or yaml) containing values for jinja template variables in RED_FILE as local path '
             'or http url.'
    )
    parser.add_argument(
        '--outdir', action='store', type=str, metavar='OUTPUT_DIR',
        help='Output directory, default current directory. Will be passed to ccagent in the container.'
    )
    parser.add_argument(
        '--non-interactive', action='store_true',
        help='Do not ask for jinja template values interactively.'
    )
    parser.add_argument(
        '--dump-format', action='store', type=str, metavar='DUMP_FORMAT', choices=['json', 'yaml'], default='json',
        help='Dump format for data generated or aggregated by the agent.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    run(**args.__dict__)
    return 0


def run(red_file, jinja_file, outdir, non_interactive, dump_format):
    pass
