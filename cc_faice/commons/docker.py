import os
import docker
from docker.errors import DockerException

from cc_core.commons.files import read
from cc_core.commons.exceptions import AgentError
from cc_core.commons.engines import DEFAULT_DOCKER_RUNTIME, NVIDIA_DOCKER_RUNTIME
from cc_core.commons.gpu_info import set_nvidia_environment_variables


NOFILE_LIMIT = 4096


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
                version='auto'
            )
        except DockerException:
            raise DockerException('Could not connect to docker daemon. Is the docker daemon running?')

    def pull(self, image, auth=None):
        self._client.images.pull(image, auth_config=auth)

    def run_container(self,
                      name,
                      image,
                      command,
                      ro_mappings,
                      rw_mappings,
                      work_dir,
                      leave_container,
                      ram,
                      runtime=DEFAULT_DOCKER_RUNTIME,
                      gpus=None,
                      environment=None,
                      enable_fuse=False
                      ):
        if environment is None:
            environment = {}

        if gpus is None:
            gpus = []

        binds = {}

        for host_vol, container_vol in ro_mappings:
            binds[host_vol] = {
                'bind': container_vol,
                'mode': 'ro'
            }

        for host_vol, container_vol in rw_mappings:
            binds[host_vol] = {
                'bind': container_vol,
                'mode': 'z'
            }

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
            volumes=binds,
            name=name,
            user='1000:1000',
            working_dir=work_dir,
            mem_limit=mem_limit,
            memswap_limit=mem_limit,
            runtime=runtime,
            environment=environment,
            devices=devices,
            cap_add=capabilities,
            ulimits=[docker.types.Ulimit(name='nofile', soft=NOFILE_LIMIT, hard=NOFILE_LIMIT)]
        )

        c.start()
        c.wait()

        std_out = c.logs(stdout=True, stderr=False)
        std_err = c.logs(stdout=False, stderr=True)

        if not leave_container:
            c.remove()

        std_out = std_out.decode('utf-8')
        std_err = std_err.decode('utf-8')

        try:
            std_out = read(std_out, 'CCAGENT_OUTPUT')
        except Exception:
            raise AgentError('Could not parse stdout of agent.\nAgent stdout:\n{}\nAgent stderr:\n{}'
                             .format(std_out, std_err))

        return std_out, std_err
