import io
import json
import os
import tarfile
from typing import List

import docker
from docker.errors import DockerException
from docker.models.containers import Container

from cc_core.commons.exceptions import AgentError
from cc_core.commons.engines import DEFAULT_DOCKER_RUNTIME, NVIDIA_DOCKER_RUNTIME
from cc_core.commons.gpu_info import set_nvidia_environment_variables, GPUDevice


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
            self._client = docker.from_env()
        except DockerException:
            raise DockerException('Could not connect to docker daemon. Is the docker daemon running?')

        self._container = None  # type: Container or None

    def pull(self, image, auth=None):
        self._client.images.pull(image, auth_config=auth)

    def create_container(
            self,
            name,
            image,
            command,
            ram,
            runtime=DEFAULT_DOCKER_RUNTIME,
            gpus=None,
            environment=None,
            enable_fuse=False,
    ):
        """
        Creates a docker container with the given arguments. All following calls to this docker manager refer to this
        docker container.

        :param name: The name of the container
        :type name: str
        :param image: The image to use for this container
        :type image: str
        :param command: The command to execute inside the container
        :type command: List[str]
        :param ram: The ram limit for this container in megabytes
        :type ram: int
        :param runtime: A runtime string for the container (like nvidia)
        :type runtime: str
        :param gpus: A specification of gpus to enable in this docker container
        :type gpus: List[GPUDevice]
        :param environment: A dictionary containing environment variables, which should be set inside the container
        :type environment: Dict[str, Any]
        :param enable_fuse: If True, SYS_ADMIN capabilities are granted for this container and /dev/fuse is mounted
        :type enable_fuse: bool
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

        self._container = self._client.containers.create(
            image,
            command,
            name=name,
            user='1000:1000',
            mem_limit=mem_limit,
            memswap_limit=mem_limit,
            runtime=runtime,
            environment=environment,
            cap_add=capabilities
        )

    def put_archive(self, archive):
        """
        Inserts the given tar archive into the container.

        :param archive: The archive, that is copied into the container
        :type archive: tarfile.TarFile
        """
        self._container.put_archive('/', archive)

    def run_container(self):
        """
        Runs the container and waits for the execution to end.

        :return: A tuple (stdout, stderr)
                 stdout: a dictionary containing the stdout of the container execution parsed as json object
                 stderr: A string containing the stderr of the container execution
        :rtype: Tuple[dict, str]

        :raise AgentError: If the stdout of the agent is not valid json
        """
        self._container.start()
        self._container.wait()

        std_out = self._container.logs(stdout=True, stderr=False).decode('utf-8')
        std_err = self._container.logs(stdout=False, stderr=True).decode('utf-8')

        try:
            parsed_std_out = json.loads(std_out)
        except json.JSONDecodeError:
            raise AgentError(
                'Could not parse stdout of agent.\nAgent stdout:\n{}\nAgent stderr:\n{}'.format(std_out, std_err)
            )

        return parsed_std_out, std_err

    def get_file_archive(self, file_path):
        """
        Retrieves the given file path as tar-archive from the internal docker container.

        :param file_path: A file path inside the docker container
        :type file_path: str

        :return: A tar archive, which corresponds to the given file path
        :rtype: tarfile.TarFile

        :raise AgentError: If the given file could not be fetched
        """
        try:
            bits, _ = self._container.get_archive(file_path)

            output_archive_bytes = io.BytesIO()
            for chunk in bits:
                output_archive_bytes.write(chunk)

            output_archive_bytes.seek(0)
        except DockerException as e:
            raise AgentError(str(e))

        return tarfile.TarFile(fileobj=output_archive_bytes)

    def remove_container(self):
        """
        Removes the internal container.
        """
        self._container.remove()
        self._container = None
