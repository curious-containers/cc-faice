"""
                Host            Container
blue_file       <tempfile>      /tmp/red/exec/blue_file.yml
blue_agent      <import...>     /tmp/red/exec/blue_agent.py
working dir     -               /tmp/red/work/
outputs         ./outputs       /tmp/red/outputs/
inputs          -               /tmp/red/inputs/
"""
import tempfile
import json

from argparse import ArgumentParser
from enum import Enum
from uuid import uuid4

from cc_core.commons.exceptions import print_exception, exception_format
from cc_core.commons.files import load_and_read
from cc_core.commons.red import red_validation
from cc_core.commons.red_to_blue import convert_red_to_blue

DESCRIPTION = 'Run an experiment as described in a REDFILE with ccagent red in a container.'

PYTHON_INTERPRETER = 'python3'
BLUE_FILE_CONTAINER_PATH = '/tmp/red/exec/blue_file.json'
BLUE_AGENT_CONTAINER_PATH = '/tmp/red/exec/blue_agent.py'
CONTAINER_OUTPUT_DIRECTORY = '/tmp/red/outputs/'


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


class OutputMode(Enum):
    Connectors = 0
    Directory = 1


def main():
    args = _get_commandline_args()
    run(**args.__dict__,
        output_mode=OutputMode.Connectors if args.outputs else OutputMode.Directory)


def run(red_file,
        # variables,
        # format,
        # disable_pull,
        leave_container,
        # preserve_environment,
        # non_interactive,
        # prefix,
        # insecure,
        output_mode,
        **_
        ):
    """
    Executes a RED Experiment
    :param red_file: The path or URL to the RED File to execute
    # :param variables: A path or URL to an variables file
    # :param disable_pull:
    :param leave_container:
    # :param preserve_environment:
    # :param non_interactive:
    # :param prefix:
    # :param insecure:
    :param output_mode: Either Connectors or Directory. If Directory Connectors, the blue agent will try to execute
    the output connectors, if Directory faice will mount an outputs directory and the blue agent will move the output
    files into this directory.
    """

    result = {
        'containers': [],
        'debugInfo': None,
        'state': 'succeeded'
    }

    try:
        red_data = load_and_read(red_file, 'REDFILE')
        red_validation(red_data, output_mode == OutputMode.Directory, container_requirement=True)

        blue_batches = convert_red_to_blue(red_data)

        blue_agent_host_path = get_blue_agent_host_path()

        # docker settings
        docker_image = red_data['container']['settings']['image']['url']

        host_outputs_dir = None  # TODO
        if len(blue_batches) == 1:
            host_outputs_dir = 'outputs'
        else:
            host_outputs_dir = 'outputs_{batch_index}'

        for batch_index, blue_batch in enumerate(blue_batches):
            run_blue_batch(blue_batch,
                           docker_image,
                           blue_agent_host_path,
                           host_outputs_dir,
                           output_mode,
                           leave_container,
                           batch_index)
    except Exception as e:
        print_exception(e)
        result['debugInfo'] = exception_format()
        result['state'] = 'failed'


def run_blue_batch(blue_batch,
                   image,
                   blue_agent_host_path,
                   host_outputs_dir,
                   output_mode,
                   leave_container,
                   batch_index,
                   ram):
    """
    Executes an blue agent inside a docker container that takes the given blue batch as argument.
    :param blue_batch: The blue batch to execute
    :param image: The docker image url to use. This docker image should be already present on the host machine
    :param blue_agent_host_path: The path to the blue agent to execute
    :param host_outputs_dir: The outputs directory of the host.
    :param output_mode: If output mode == Connectors the blue agent will be started with '--outputs' flag
    Otherwise this function will mount the CONTAINER_OUTPUT_DIRECTORY
    :param leave_container: If True, the started container will not be stopped after execution.
    :param batch_index: The index of the current batch
    :param ram: TODO
    :return: A container result as dictionary
    """
    container_name = str(uuid4())
    command = _create_blue_agent_command()

    blue_file = _create_json_file(blue_batch)

    ro_mappings = [[blue_file.name, BLUE_FILE_CONTAINER_PATH],
                   [blue_agent_host_path, BLUE_AGENT_CONTAINER_PATH]]

    rw_mappings = []
    if output_mode == OutputMode.Directory:
        rw_mappings.append([host_outputs_dir.format(batch_index=batch_index), CONTAINER_OUTPUT_DIRECTORY])

    working_directory = blue_batch['workDir']

    # EXECUTE

    blue_file.close()


def _create_json_file(data):
    """
    Creates a temporary file that contains the given data in json format.
    :param data: The data to write to the temporary file
    :return: A NamedTemporaryFile
    """
    f = tempfile.NamedTemporaryFile()
    json.dump(data, f)
    f.seek(0)
    f.flush()
    return f


def _create_blue_agent_command():
    """
    Defines the command to execute inside the docker container to execute the blue agent.
    :return: A list of strings to execute inside the docker container.
    """
    return [PYTHON_INTERPRETER, BLUE_AGENT_CONTAINER_PATH, BLUE_FILE_CONTAINER_PATH]


def get_blue_agent_host_path():
    """
    Returns the path of the blue agent in the host machine to mount into the docker container.
    :return: The path to the blue agent
    """
    import cc_core.agent.blue.main as blue_main
    return blue_main.__file__
