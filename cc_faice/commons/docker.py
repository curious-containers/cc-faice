import os
import docker
from docker.errors import DockerException

from cc_core.commons.cwl import location
from cc_core.commons.files import read
from cc_core.commons.exceptions import AgentError
from cc_core.commons.engines import DEFAULT_DOCKER_RUNTIME, NVIDIA_DOCKER_RUNTIME
from cc_core.commons.gpu_info import set_nvidia_environment_variables

DOCKER_SOCKET = 'unix://var/run/docker.sock'


def docker_result_check(ccagent_data):
    if ccagent_data[0]['state'] != 'succeeded':
        raise AgentError('ccagent did not succeed\n\nError of Agent:\n{}'.format(ccagent_data[1]))


def dump_job(job_data, mapped_input_dir):
    job = {}

    for key, arg in job_data.items():
        val = arg
        if isinstance(arg, list):
            val = []
            for index, i in enumerate(arg):
                if isinstance(i, dict):
                    if (i.get('class') == 'File') or (i.get('class') == 'Directory'):
                        path = os.path.join(mapped_input_dir, '{}_{}'.format(key, index))
                        elem = {
                            'class': i['class'],
                            'path': path
                        }
                        listing = i.get('listing')
                        if listing:
                            elem['listing'] = listing
                        val.append(elem)
                else:
                    val.append(i)
        elif isinstance(arg, dict):
            if (arg.get('class') == 'File') or (arg.get('class') == 'Directory'):
                path = os.path.join(mapped_input_dir, key)
                val = {
                    'class': arg['class'],
                    'path': path
                }
                listing = arg.get('listing')
                if listing:
                    val['listing'] = listing

        job[key] = val

    return job


def input_volume_mappings(job_data, dumped_job_data, input_dir):
    volumes = []

    for key, val in job_data.items():
        if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
            for i, e in enumerate(val):
                file_path = location(key, e)

                if not os.path.isabs(file_path):
                    file_path = os.path.join(os.path.expanduser(input_dir), file_path)

                container_file_path = dumped_job_data[key][i]['path']
                volumes.append([os.path.abspath(file_path), container_file_path])

        if isinstance(val, dict):
            file_path = location(key, val)

            if not os.path.isabs(file_path):
                file_path = os.path.join(os.path.expanduser(input_dir), file_path)

            container_file_path = dumped_job_data[key]['path']
            volumes.append([os.path.abspath(file_path), container_file_path])

    return volumes


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
        except DockerException as e:
            raise DockerException('Could not connect to docker daemon at "{}". Is the docker daemon running?'
                                  .format(DOCKER_SOCKET))

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
        binds = {}

        if environment is None:
            environment = {}

        if gpus is None:
            gpus = []

        for host_vol, container_vol in ro_mappings:
            binds[host_vol] = {
                'bind': container_vol,
                'mode': 'ro'
            }

        for host_vol, container_vol in rw_mappings:
            binds[host_vol] = {
                'bind': container_vol,
                'mode': 'rw'
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
            cap_add=capabilities
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
            raise AgentError(std_err)

        return std_out, std_err
