from argparse import ArgumentParser

from cc_core.commons.files import load_and_read
from cc_core.commons.red import red_validation
from cc_core.commons.red_to_blue import convert_red_to_blue

DESCRIPTION = 'Run an experiment as described in a REDFILE with ccagent red in a container.'


def attach_args(parser):
    parser.add_argument(
        'red_file', action='store', type=str, metavar='REDFILE',
        help='REDFILE (json or yaml) containing an experiment description as local PATH or http URL.'
    )
    parser.add_argument(
        '-v', '--variables', action='store', type=str, metavar='VARFILE',
        help='VARFILE (json or yaml) containing key-value pairs for variables in REDFILE as '
             'local PATH or http URL.'
    )
    parser.add_argument(
        '-o', '--outputs', action='store_true',
        help='Enable connectors specified in the RED FILE outputs section.'
    )
    parser.add_argument(
        '-d', '--debug', action='store_true',
        help='Write debug info, including detailed exceptions, to stdout.'
    )
    parser.add_argument(
        '--format', action='store', type=str, metavar='FORMAT', choices=['json', 'yaml', 'yml'], default='yaml',
        help='Specify FORMAT for generated data as one of [json, yaml, yml]. Default is yaml.'
    )
    parser.add_argument(
        '--disable-pull', action='store_true',
        help='Do not try to pull Docker images.'
    )
    parser.add_argument(
        '--leave-container', action='store_true',
        help='Do not delete Docker container used by jobs after they exit.'
    )
    parser.add_argument(
        '--preserve-environment', action='append', type=str, metavar='ENVVAR',
        help='Preserve specific environment variables when running container. May be provided multiple times.'
    )
    parser.add_argument(
        '--non-interactive', action='store_true',
        help='Do not ask for RED variables interactively.'
    )
    parser.add_argument(
        '--insecure', action='store_true',
        help='Enable SYS_ADMIN capabilities in container, if REDFILE contains connectors performing FUSE mounts.'
    )
    parser.add_argument(
        '--prefix', action='store', type=str, metavar='PREFIX', default='faice_',
        help='PREFIX for files dumped to storage, default is "faice_".'
    )


def _get_commandline_args():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    return parser.parse_args()


def main():
    args = _get_commandline_args()
    run(**args.__dict__,
        ignore_outputs=not args.outputs)


def run(red_file,
        # variables,
        # format,
        # disable_pull,
        # leave_container,
        # preserve_environment,
        # non_interactive,
        # prefix,
        # insecure,
        ignore_outputs,
        **_
        ):
    """
    Executes a RED Experiment
    :param red_file: The path or URL to the RED File to execute
    # :param variables: A path or URL to an variables file
    # :param disable_pull:
    # :param leave_container:
    # :param preserve_environment:
    # :param non_interactive:
    # :param prefix:
    # :param insecure:
    :param ignore_outputs:
    """

    result = {
        'containers': [],
        'debugInfo': None,
        'state': 'succeeded'
    }

    red_data = load_and_read(red_file, 'REDFILE')
    red_validation(red_data, ignore_outputs, container_requirement=True)

    blue_data = convert_red_to_blue(red_data)
    print(blue_data)
