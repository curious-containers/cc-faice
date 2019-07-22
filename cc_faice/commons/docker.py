import io
import os
import tarfile

import docker
from docker.errors import DockerException
from docker.models.containers import Container

from cc_core.commons.files import read
from cc_core.commons.exceptions import AgentError
from cc_core.commons.engines import DEFAULT_DOCKER_RUNTIME, NVIDIA_DOCKER_RUNTIME
from cc_core.commons.gpu_info import set_nvidia_environment_variables

DOCKER_SOCKET = 'unix://var/run/docker.sock'


def env_vars(preserve_environment):
    if preserve_environment is None:
        return {}

    environment = {}

    for var in preserve_environment:
        if var in os.environ:
            environment[var] = os.environ[var]

    return environment


class DockerManager:
    def __init__(self):
        try:
            self._client = docker.DockerClient(
                base_url=DOCKER_SOCKET,
                version='auto'
            )
        except DockerException:
            raise DockerException('Could not connect to docker daemon at "{}". Is the docker daemon running?'
                                  .format(DOCKER_SOCKET))

    def pull(self, image, auth=None):
        self._client.images.pull(image, auth_config=auth)

    def run_container(
            self,
            name,
            image,
            command,
            work_dir,
            leave_container,
            ram,
            runtime=DEFAULT_DOCKER_RUNTIME,
            gpus=None,
            environment=None,
            enable_fuse=False,
            archive=None,
            output_directory=None
    ):
        """
        Executes a docker container with the given arguments.

        :param name: The name of the container
        :param image: The image to use for this container
        :param command: The command to execute inside the container
        :param work_dir: The initial working directory inside the container
        :param leave_container: If True, the container will not be removed after execution
        :param ram: The ram limit for this container
        :param runtime: A runtime string for the container (like nvidia)
        :param gpus: A specification of gpus to enable in this docker container
        :param environment: A dictionary containing environment variables, which should be set inside the container
        :param enable_fuse: If True, SYS_ADMIN capabilities are granted for this container and /dev/fuse is mounted
        :param archive: An optional archive, that can be copied into the container before starting it
        :param output_directory: A path to a directory inside the docker container that will be loaded to the host system
                              when the container has finished and returned as third argument.

        :return: A tuple (stdout, stderr, get_archive)
                 stdout: a dictionary containing the stdout of the container execution parsed as json object
                 stderr: A string containing the stderr of the container execution
                 get_archive: A TarFile that contains the files which were found under output_directory
        :rtype: Tuple[dict, str, TarFile or None]
        """
        if environment is None:
            environment = {}

        if gpus is None:
            gpus = []

        mem_limit = None

        if ram is not None:
            mem_limit = '{}m'.format(ram)

        if runtime == NVIDIA_DOCKER_RUNTIME:
            set_nvidia_environment_variables(environment, map(lambda gpu: gpu.device_id, gpus))

        devices = []
        capabilities = []
        if enable_fuse:
            devices.append('/dev/fuse')
            capabilities.append('SYS_ADMIN')

        c = self._client.containers.create(
            image,
            command,
            name=name,
            user='1000:1000',
            working_dir=work_dir,
            mem_limit=mem_limit,
            memswap_limit=mem_limit,
            runtime=runtime,
            environment=environment,
            devices=devices,
            cap_add=capabilities
        )  # type: Container

        if archive:
            c.put_archive('/', archive)

        c.start()
        c.wait()

        std_out = c.logs(stdout=True, stderr=False)
        std_err = c.logs(stdout=False, stderr=True)

        # handle output directory
        output_tar_file = None
        if output_directory:
            try:
                bits, _ = c.get_archive(output_directory)

                output_archive_bytes = io.BytesIO()
                for chunk in bits:
                    output_archive_bytes.write(chunk)

                output_archive_bytes.seek(0)
                output_tar_file = tarfile.TarFile(fileobj=output_archive_bytes)
            except DockerException as e:
                print('failed to get output archive.\n{}'.format(str(e)))  # TODO: handle right

        if not leave_container:
            c.remove()

        std_out = std_out.decode('utf-8')
        std_err = std_err.decode('utf-8')

        try:
            std_out = read(std_out, 'CCAGENT_OUTPUT')
        except Exception:
            raise AgentError('Could not parse stdout of agent.\nAgent stdout:\n{}\nAgent stderr:\n{}'
                             .format(std_out, std_err))

        return std_out, std_err, output_tar_file
