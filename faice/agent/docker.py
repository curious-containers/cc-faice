import os
import json
import docker
from uuid import uuid4

from cc_core.commons.cwl import location


def job_to_container_job(job_data, mapped_input_dir):
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


def input_volume_mappings(job_data, container_job_data, input_dir):
    volumes = []

    for key, val in job_data.items():
        if not isinstance(val, dict):
            continue

        file_path = location(key, val)

        if not os.path.isabs(file_path):
            file_path = os.path.join(os.path.expanduser(input_dir), file_path)

        container_file_path = container_job_data[key]['path']
        volumes.append((os.path.abspath(file_path), container_file_path))

    return volumes


class DockerManager:
    def __init__(self):
        self._client = docker.DockerClient(
            base_url='unix://var/run/docker.sock',
            version='auto'
        )
        self.container_name = str(uuid4())

    def pull(self, image):
        self._client.images.pull(image)

    def run_container(self, image, command, ro_mappings, rw_mappings, work_dir):
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
            name=self.container_name,
            user='1000:1000',
            working_dir=work_dir,
        )

        return json.loads(std_out.decode('utf-8'))
