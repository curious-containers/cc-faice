from argparse import ArgumentParser


DESCRIPTION = 'Run a CommandLineTool as described in a FAICE_FILE. This tool is similar to agents implemented in ' \
              'cc-core, but uses container technologies. Refer to the FAICE documentation for more ' \
              'details.'


def attach_args(parser):
    parser.add_argument(
        'faice_file', action='store', type=str, metavar='FAICE_FILE',
        help='FAICE_FILE containing an experiment description (json/yaml) as local path or http url.'
    )
    parser.add_argument(
        '--no-container', action='store_true',
        help='Do not execute jop in a container, even when specified by the experiment.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    return run(**args.__dict__)


def run(faice_file, no_container):
    print(faice_file)
    print(no_container)
    return 0
