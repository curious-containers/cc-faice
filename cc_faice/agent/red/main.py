"""
                Host            Container
blue_file       <tempfile>      /tmp/red_exec/blue_file.yml
blue_agent      <import...>     /tmp/red_exec/blue_agent.py
outputs         ./outputs       /outputs/
inputs          -               /tmp/red/inputs/
working dir     -               -
"""
import io
import os
import tarfile

import tempfile
import json
import stat

from argparse import ArgumentParser
from enum import Enum
from uuid import uuid4

from cc_core.commons.engines import engine_to_runtime, engine_validation
from cc_core.commons.exceptions import print_exception, exception_format, AgentError
from cc_core.commons.files import load_and_read, dump_print
from cc_core.commons.gpu_info import get_gpu_requirements, get_devices, match_gpus
from cc_core.commons.red import red_validation
from cc_core.commons.red_to_blue import convert_red_to_blue
from cc_core.commons.templates import get_secret_values, normalize_keys

from cc_faice.commons.templates import complete_red_templates
from cc_faice.commons.docker import env_vars, DockerManager

DESCRIPTION = 'Run an experiment as described in a REDFILE with ccagent red in a container.'

PYTHON_INTERPRETER = 'python3'
BLUE_FILE_CONTAINER_NAME = 'blue_file.json'
BLUE_AGENT_CONTAINER_NAME = 'blue_agent.py'
BLUE_AGENT_CONTAINER_DIR = '/cc'
CONTAINER_OUTPUT_DIRECTORY = '/outputs'
CONTAINER_WORK_DIRECTORY = None


def attach_args(parser):
    parser.add_argument(
        'red_file', action='store', type=str, metavar='REDFILE',
        help='REDFILE (json or yaml) containing an experiment description as local PATH or http URL.'
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
        '--keyring-service', action='store', type=str, metavar='KEYRING_SERVICE', default='red',
        help='Keyring service to resolve template values, default is "red".'
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
    if args.outputs:
        output_mode = OutputMode.Connectors
    else:
        output_mode = OutputMode.Directory
    result = run(**args.__dict__,
                 output_mode=output_mode)

    if args.debug:
        dump_print(result, args.format)

    if result['state'] != 'succeeded':
        return 1

    return 0


def run(red_file,
        disable_pull,
        leave_container,
        preserve_environment,
        non_interactive,
        insecure,
        output_mode,
        keyring_service,
        **_
        ):
    """
    Executes a RED Experiment
    :param red_file: The path or URL to the RED File to execute
    :param disable_pull: If True the docker image is not pulled from an registry
    :param leave_container:
    :param preserve_environment: List of environment variables to preserve inside the docker container.
    :param non_interactive: If True, unresolved template values are not asked interactively
    :param insecure: Allow insecure capabilities
    :param output_mode: Either Connectors or Directory. If Directory Connectors, the blue agent will try to execute
    :param keyring_service: The keyring service name to use for template substitution the output connectors, if
    Directory faice will mount an outputs directory and the blue agent will move the output files into this directory.
    """

    result = {
        'containers': [],
        'debugInfo': None,
        'state': 'succeeded'
    }

    secret_values = None

    try:
        red_data = load_and_read(red_file, 'REDFILE')

        # validation
        red_validation(red_data, output_mode == OutputMode.Directory, container_requirement=True)
        engine_validation(red_data, 'container', ['docker', 'nvidia-docker'], optional=False)

        # templates and secrets
        complete_red_templates(red_data, keyring_service, non_interactive)
        secret_values = get_secret_values(red_data)
        normalize_keys(red_data)

        # process red data
        blue_batches = convert_red_to_blue(red_data)

        # docker settings
        docker_image = red_data['container']['settings']['image']['url']
        ram = red_data['container']['settings'].get('ram')
        runtime = engine_to_runtime(red_data['container']['engine'])
        environment = env_vars(preserve_environment)

        # gpus
        gpu_requirements = get_gpu_requirements(red_data['container']['settings'].get('gpus'))
        gpu_devices = get_devices(red_data['container']['engine'])
        gpus = match_gpus(gpu_devices, gpu_requirements)

        # create docker manager
        docker_manager = DockerManager()

        if not disable_pull:
            registry_auth = red_data['container']['settings']['image'].get('auth')
            docker_manager.pull(docker_image, auth=registry_auth)

        if len(blue_batches) == 1:
            host_outdir = 'outputs'
        else:
            host_outdir = 'outputs_{batch_index}'

        for batch_index, blue_batch in enumerate(blue_batches):
            container_execution_result = run_blue_batch(
                blue_batch=blue_batch,
                docker_manager=docker_manager,
                docker_image=docker_image,
                host_outdir=host_outdir,
                output_mode=output_mode,
                leave_container=leave_container,
                batch_index=batch_index,
                ram=ram,
                gpus=gpus,
                environment=environment,
                runtime=runtime,
                insecure=insecure
            )

            # handle execution result
            result['containers'].append(container_execution_result.to_dict())
            container_execution_result.raise_for_state()
    except Exception as e:
        print_exception(e, secret_values)
        result['debugInfo'] = exception_format(secret_values)
        result['state'] = 'failed'

    return result


def _get_blue_batch_mount_keys(blue_batch):
    """
    Returns a list of input/output keys, that use mounting connectors
    :param blue_batch: The blue batch to analyse
    Output connectors are evaluated only, if output_mode == Connectors
    :return: A list of input/outputs keys as strings
    """
    mount_connectors = []

    # check input keys
    for input_key, input_value in blue_batch['inputs'].items():
        if not isinstance(input_value, list):
            input_value = [input_value]

        if not isinstance(input_value[0], dict):
            continue

        for input_value_element in input_value:
            connector = input_value_element.get('connector')
            if connector and connector.get('mount', False):
                mount_connectors.append(input_key)

    return mount_connectors


class ExecutionResultType(Enum):
    Succeeded = 0
    Failed = 1

    def __str__(self):
        return self.name.lower()


class ContainerExecutionResult:
    def __init__(self, state, command, container_name, agent_execution_result, agent_std_err):
        """
        Creates a new Container Execution Result

        :param state: The state of the agent execution ('failed', 'successful')
        :param command: The command, that executes the blue agent inside the docker container
        :param container_name: The name of the docker container
        :param agent_execution_result: The parsed json output of the blue agent
        :param agent_std_err: The std err as list of string of the blue agent
        """
        self.state = state
        self.command = command
        self.container_name = container_name
        self.agent_execution_result = agent_execution_result
        self.agent_std_err = agent_std_err

    def successful(self):
        return self.state == ExecutionResultType.Succeeded

    def to_dict(self):
        """
        Transforms self into a dictionary representation.
        :return: self as dictionary
        """
        return {
            'state': str(self.state),
            'command': self.command,
            'containerName': self.container_name,
            'agentStdOut': self.agent_execution_result,
            'agentStdErr': self.agent_std_err
        }

    def raise_for_state(self):
        """
        Raises an AgentError, if state is not successful.
        :raise AgentError: If state is not successful
        """
        if not self.successful():
            raise AgentError(self.agent_std_err)


def run_blue_batch(blue_batch,
                   docker_manager,
                   docker_image,
                   host_outdir,
                   output_mode,
                   leave_container,
                   batch_index,
                   ram,
                   gpus,
                   environment,
                   runtime,
                   insecure):
    """
    Executes an blue agent inside a docker container that takes the given blue batch as argument.

    :param blue_batch: The blue batch to execute
    :param docker_manager: The docker manager to use for executing the batch
    :param docker_image: The docker image url to use. This docker image should be already present on the host machine
    :param host_outdir: The outputs directory of the host. This is mounted as outdir inside the docker container
                        mounted into the docker container, where host_outputs_dir is the host directory.
    :param output_mode: If output mode == Connectors the blue agent will be started with '--outputs' flag
                        Otherwise this function will mount the CONTAINER_OUTPUT_DIRECTORY
    :param leave_container: If True, the started container will not be stopped after execution.
    :param batch_index: The index of the current batch
    :param ram: The RAM limit for the docker container, given in MB
    :param gpus: The gpus to use for this batch execution
    :param environment: The environment to use for the docker container
    :param runtime: The docker runtime to use
    :param insecure: Allow insecure capabilities
    :return: A container result
    :rtype: ContainerExecutionResult
    """

    container_name = str(uuid4())

    command = _create_blue_agent_command()

    container_outdir = None
    if output_mode == OutputMode.Directory:
        container_outdir = blue_batch['outdir']
    elif output_mode == OutputMode.Connectors:
        command.append('--outputs')

    is_mounting = define_is_mounting(blue_batch, insecure)

    with _create_batch_archive(blue_batch, BLUE_AGENT_CONTAINER_DIR) as blue_archive:
        ccagent_data = docker_manager.run_container(
            name=container_name,
            image=docker_image,
            command=command,
            work_dir=None,
            leave_container=leave_container,
            ram=ram,
            runtime=runtime,
            gpus=gpus,
            environment=environment,
            enable_fuse=is_mounting,
            archive=blue_archive,
            output_directory=container_outdir
        )

    if ccagent_data[0]['state'] == 'succeeded':
        state = ExecutionResultType.Succeeded

        # create outputs directory
        if output_mode == OutputMode.Directory:
            # create host output directory
            abs_host_outdir = os.path.abspath(host_outdir.format(batch_index=batch_index))
            os.makedirs(abs_host_outdir, exist_ok=True)

            output_tar_file = ccagent_data[2]
            output_tar_file.extractall()
            output_tar_file.close()
    else:
        state = ExecutionResultType.Failed

    container_result = ContainerExecutionResult(
        state,
        command,
        container_name,
        ccagent_data[0],
        ccagent_data[1]
    )

    return container_result


def _create_batch_archive(blue_data, directory):
    """
    Creates a tar archive. This archive contains the blue agent and a blue file. The blue file is filled with the
    given blue data. The blue agent and the blue file are stored inside the given directory. The tar archive and all
    files contained in this archive are in memory and are never stored in the local filesystem.

    :param blue_data: The data to put into the blue file of the returned archive
    :type blue_data: dict
    :param directory: Inside the archive the blue agent and the blue batch is located under the given directory
    :type directory: str
    :return: A tar archive containing the blue agent and the given blue batch
    :rtype: io.BytesIO or bytes
    """
    data_file = io.BytesIO()
    tar_file = tarfile.open(mode='w', fileobj=data_file)

    # add blue agent
    agent_archive_name = os.path.join(directory, BLUE_AGENT_CONTAINER_NAME)
    tar_file.add(get_blue_agent_host_path(), arcname=agent_archive_name, recursive=False)

    # add blue file
    blue_batch_name = os.path.join(directory, BLUE_FILE_CONTAINER_NAME)
    blue_batch_content = json.dumps(blue_data).encode('utf-8')

    # see https://bugs.python.org/issue22208 for more information
    blue_batch_tarinfo = tarfile.TarInfo(blue_batch_name)
    blue_batch_tarinfo.size = len(blue_batch_content)

    tar_file.addfile(blue_batch_tarinfo, io.BytesIO(blue_batch_content))

    # close file
    tar_file.close()
    data_file.seek(0)

    return data_file


def define_is_mounting(blue_batch, insecure):
    mount_connectors = _get_blue_batch_mount_keys(blue_batch)
    if mount_connectors:
        if not insecure:
            raise Exception('The following keys are mounting directories {}.\nTo enable mounting inside '
                            'a docker container run faice with --insecure (see --help).\n'
                            'Be aware that this will enable SYS_ADMIN capabilities in order to enable FUSE mounts.'
                            .format(mount_connectors))
        return True
    return False


def _create_json_file(data):
    """
    Creates a temporary file that contains the given data in json format.
    :param data: The data to write to the temporary file
    :return: A NamedTemporaryFile
    """
    f = tempfile.NamedTemporaryFile(mode='w')
    json.dump(data, f)
    f.seek(0)
    f.flush()
    if os.getuid() != 1000:
        os.chmod(f.name, stat.S_IROTH)
    return f


def _create_blue_agent_command():
    """
    Defines the command to execute inside the docker container to execute the blue agent.
    The resulting command looks similar to "python3 /cc/blue_agent.py /cc/blue_file.json --debug"

    :return: A list of strings to execute inside the docker container.
    :rtype: List[str]
    """
    blue_agent_container_path = os.path.join(BLUE_AGENT_CONTAINER_DIR, BLUE_AGENT_CONTAINER_NAME)
    blue_file_container_path = os.path.join(BLUE_AGENT_CONTAINER_DIR, BLUE_FILE_CONTAINER_NAME)
    return [PYTHON_INTERPRETER, blue_agent_container_path, blue_file_container_path, '--debug']


def get_blue_agent_host_path():
    """
    Returns the path of the blue agent in the host machine to mount into the docker container.
    :return: The path to the blue agent
    """
    import cc_core.agent.blue.__main__ as blue_main
    return blue_main.__file__
