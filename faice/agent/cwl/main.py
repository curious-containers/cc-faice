import os
import json
from uuid import uuid4
from argparse import ArgumentParser

from cc_core.commons.files import load_and_read
from cc_core.commons.cwl import cwl_validation
from cc_core.commons.exceptions import exception_format

from faice.agent.docker import job_to_container_job, input_volume_mappings, DockerManager


DESCRIPTION = 'Run a CommandLineTool as described in a CWL_FILE and its corresponding JOB_FILE in a container with ' \
              'ccagent (cc_core.agent.cwl).'


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
        '-d', '--outdir', action='store', type=str, metavar='OUTPUT_DIR',
        help='Output directory, default current directory. Will be passed to ccagent in the container.'
    )
    parser.add_argument(
        '--disable-pull', action='store_true',
        help='Do not try to pull Docker images.'
    )
    parser.add_argument(
        '--leave-container', action='store_true',
        help='Do not delete Docker container used by jobs after they exit.'
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


def run(cwl_file, job_file, outdir, disable_pull, leave_container):
    result = {
        'container': {
            'command': None,
            'name': None,
            'volumes': {
                'read_only': None,
                'read_write': None
            },
            'ccagent': None
        },
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

        result['container']['volumes']['read_only'] = ro_mappings
        result['container']['volumes']['read_write'] = rw_mappings

        container_name = str(uuid4())
        result['container']['name'] = container_name
        docker_manager = DockerManager(container_name)

        image = cwl_data['requirements']['DockerRequirement']['dockerPull']
        if not disable_pull:
            docker_manager.pull(image)

        command = 'ccagent cwl {} {}'.format(mapped_cwl_file, mapped_container_job_file)
        if outdir:
            command = '{} --outdir={}'.format(command, outdir)
        result['container']['command'] = command

        if not os.path.exists(work_dir):
            os.makedirs(work_dir)

        with open(container_job_file, 'w') as f:
            json.dump(container_job_data, f)

        ccagent_data = docker_manager.run_container(
            image, command, ro_mappings, rw_mappings, mapped_work_dir, leave_container
        )
        result['container']['ccagent'] = ccagent_data
    except:
        result['debug_info'] = exception_format()

    return result
