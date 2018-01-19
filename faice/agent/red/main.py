from argparse import ArgumentParser


DESCRIPTION = 'Run an experiment as described in a RED_FILE. This tool is similar to agents implemented in ' \
              'cc-core, but uses container technologies. Refer to the RED documentation for more ' \
              'details.'


def attach_args(parser):
    parser.add_argument(
        'red_file', action='store', type=str, metavar='RED_FILE',
        help='RED_FILE containing an experiment description (json/yaml) as local path or http url.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    return run(**args.__dict__)


def run(red_file):
    print(red_file)
    return 0
