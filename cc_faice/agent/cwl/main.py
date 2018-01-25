import os
from uuid import uuid4
from argparse import ArgumentParser

from cc_core.commons.files import load_and_read, dump, dump_print, file_extension
from cc_core.commons.cwl import cwl_validation
from cc_core.commons.exceptions import exception_format

from cc_faice.commons.docker import dump_job, input_volume_mappings, DockerManager


DESCRIPTION = 'Run a CommandLineTool as described in a CWL_FILE and its corresponding JOB_FILE in a container with ' \
              'ccagent (cc_core.agent.cwl).'


def attach_args(parser):
    parser.add_argument(
        'cwl_file', action='store', type=str, metavar='CWL_FILE',
        help='CWL_FILE (json or yaml) containing a CLI description as local path or http url.'
    )
    parser.add_argument(
        'job_file', action='store', type=str, metavar='JOB_FILE',
        help='JOB_FILE (json or yaml) in the CWL job format as local path or http url.'
    )
    parser.add_argument(
        '--outdir', action='store', type=str, metavar='OUTPUT_DIR',
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
    parser.add_argument(
        '--dump-format', action='store', type=str, metavar='DUMP_FORMAT', choices=['json', 'yaml', 'yml'],
        default='yaml', help='Dump format for data written to files or stdout, default is "yaml".'
    )
    parser.add_argument(
        '--dump-prefix', action='store', type=str, metavar='DUMP_PREFIX', default='dumped_',
        help='Name prefix for files dumped to storage, default is "_dumped".'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()

    result = run(**args.__dict__)
    dump_print(result, args.dump_format)

    return 0


def run(cwl_file, job_file, outdir, disable_pull, leave_container, dump_format, dump_prefix):
    result = {
        'container': {
            'command': None,
            'name': None,
            'volumes': {
                'readOnly': None,
                'readWrite': None
            },
            'ccagent': None
        },
        'debugInfo': None
    }

    try:
        cwl_data = load_and_read(cwl_file, 'CWL_FILE')
        job_data = load_and_read(job_file, 'JOB_FILE')

        cwl_validation(cwl_data, job_data, docker_requirement=True)

        ext = file_extension(dump_format)
        input_dir = os.path.split(os.path.expanduser(job_file))[0]
        work_dir = 'work'
        dumped_job_file = '{}job.{}'.format(dump_prefix, ext)

        mapped_input_dir = '/opt/cc/inputs'
        mapped_work_dir = '/opt/cc/work'
        mapped_cwl_file = '/opt/cc/cli.cwl'
        mapped_job_file = '/opt/cc/job.{}'.format(ext)

        dumped_job_data = dump_job(job_data, mapped_input_dir)

        ro_mappings = input_volume_mappings(job_data, dumped_job_data, input_dir)
        ro_mappings += [
            [os.path.abspath(cwl_file), mapped_cwl_file],
            [os.path.abspath(dumped_job_file), mapped_job_file]
        ]
        rw_mappings = [[os.path.abspath(work_dir), mapped_work_dir]]

        result['container']['volumes']['readOnly'] = ro_mappings
        result['container']['volumes']['readWrite'] = rw_mappings

        container_name = str(uuid4())
        result['container']['name'] = container_name
        docker_manager = DockerManager()

        image = cwl_data['requirements']['DockerRequirement']['dockerPull']
        if not disable_pull:
            docker_manager.pull(image)

        command = 'ccagent cwl {} {} --dump-format={}'.format(mapped_cwl_file, mapped_job_file, dump_format)
        if outdir:
            command = '{} --outdir={}'.format(command, outdir)
        result['container']['command'] = command

        if not os.path.exists(work_dir):
            os.makedirs(work_dir)

        dump(dumped_job_data, dump_format, dumped_job_file)

        ccagent_data = docker_manager.run_container(
            container_name, image, command, ro_mappings, rw_mappings, mapped_work_dir, leave_container
        )
        result['container']['ccagent'] = ccagent_data
    except:
        result['debugInfo'] = exception_format()

    return result
