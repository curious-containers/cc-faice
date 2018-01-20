import os
import json
from argparse import ArgumentParser

from cc_core.commons.files import load_and_read
from cc_core.commons.cwl import cwl_to_command, cwl_validation
from cc_core.commons.cwl import cwl_input_files, cwl_output_files, cwl_input_file_check, cwl_output_file_check
from cc_core.commons.shell import execute
from cc_core.commons.exceptions import exception_format

from faice.agent.docker import job_to_container_job, input_volume_mappings, DockerManager


DESCRIPTION = 'Run a CommandLineTool as described in a CWL_FILE and its corresponding JOB_FILE in a container with ' \
              'cc-core.'


def attach_args(parser):
    parser.add_argument(
        'cwl_file', action='store', type=str, metavar='CWL_FILE',
        help='CWL_FILE containing a CLI description (json/yaml) as local path or http url.'
    )
    parser.add_argument(
        'job_file', action='store', type=str, metavar='JOB_FILE',
        help='JOB_FILE in the CWL job format (json/yaml) as local path or http url.'
    )
    parser.add_argument(
        '--no-pull', action='store_true',
        help='Do not explicitely pull Docker image.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()

    result = run(**args.__dict__)
    print(json.dumps(result, indent=4))

    if result['debug_info']:
        return 1

    return 0


def run(cwl_file, job_file, no_pull):
    result = {
        'container_data': None,
        'debug_info': None
    }

    try:
        cwl_data = load_and_read(cwl_file, 'CWL_FILE')
        job_data = load_and_read(job_file, 'JOB_FILE')

        cwl_validation(cwl_data, job_data, docker_requirement=True)

        input_dir = os.path.split(os.path.expanduser(job_file))[0]
        work_dir = os.path.join(os.getcwd(), 'work')
        container_job_file = os.path.join(os.getcwd(), 'container-job.yml')
        cwl_file_name = os.path.split(cwl_file)[1]

        mapped_input_dir = '/opt/cc/inputs'
        mapped_work_dir = '/opt/cc/work'
        mapped_cwl_file = os.path.join('/opt/cc', cwl_file_name)
        mapped_container_job_file = '/opt/cc/container-job.yml'

        container_job_data = job_to_container_job(job_data, mapped_input_dir)

        ro_mappings = input_volume_mappings(job_data, container_job_data, input_dir)
        ro_mappings.append((os.path.abspath(cwl_file), mapped_cwl_file))
        ro_mappings.append((os.path.abspath(container_job_file), mapped_container_job_file))

        rw_mappings = [(work_dir, mapped_work_dir)]

        docker_manager = DockerManager()

        if not os.path.exists(work_dir):
            os.makedirs(work_dir)

        with open(container_job_file, 'w') as f:
            json.dump(container_job_data, f)

        image = cwl_data['requirements']['DockerRequirement']['dockerPull']
        if not no_pull:
            docker_manager.pull(image)

        command = 'ccagent cwl {} {}'.format(mapped_cwl_file, mapped_container_job_file)

        container_data = docker_manager.run_container(image, command, ro_mappings, rw_mappings, mapped_work_dir)
        result['container_data'] = container_data
    except:
        result['debug_info'] = exception_format()

    return result
