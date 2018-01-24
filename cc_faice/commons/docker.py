import os
import docker

from cc_core.commons.cwl import location
from cc_core.commons.files import read


def dump_job(job_data, mapped_input_dir):
    job = {}

    for key, val in job_data.items():
        if not isinstance(val, dict):
            job[key] = val
            continue

        path = os.path.join(mapped_input_dir, key)
        job[key] = {
            'class': 'File',
            'path': path
        }

    return job


def input_volume_mappings(job_data, dumped_job_data, input_dir):
    volumes = []

    for key, val in job_data.items():
        if not isinstance(val, dict):
            continue

        file_path = location(key, val)

        if not os.path.isabs(file_path):
            file_path = os.path.join(os.path.expanduser(input_dir), file_path)

        container_file_path = dumped_job_data[key]['path']
        volumes.append([os.path.abspath(file_path), container_file_path])

    return volumes


class DockerManager:
    def __init__(self):
        self._client = docker.DockerClient(
            base_url='unix://var/run/docker.sock',
            version='auto'
        )

    def pull(self, image, auth=None):
        self._client.images.pull(image, auth_config=auth)

    def run_container(self, name, image, command, ro_mappings, rw_mappings, work_dir, leave_container):
        binds = {}

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

        std_out = self._client.containers.run(
            image,
            command,
            volumes=binds,
            name=name,
            user='1000:1000',
            working_dir=work_dir,
            remove=not leave_container
        )

        return read(std_out.decode('utf-8'), 'CCAGENT_OUTPUT')
