import os
from uuid import uuid4
from argparse import ArgumentParser

from cc_core.commons.files import load_and_read, dump, dump_print, file_extension, is_local
from cc_core.commons.cwl import cwl_validation
from cc_core.commons.exceptions import exception_format, print_exception
from cc_core.commons.mnt_core import module_dependencies, interpreter_dependencies
from cc_core.commons.mnt_core import module_destinations, interpreter_destinations, interpreter_command

from cc_faice.commons.docker import dump_job, input_volume_mappings, DockerManager, docker_result_check, env_vars

DESCRIPTION = 'Run a CommandLineTool as described in a CWL_FILE and its corresponding JOB_FILE with ccagent cwl in a ' \
              'container.'


def attach_args(parser):
    parser.add_argument(
        'cwl_file', action='store', type=str, metavar='CWLFILE',
        help='CWLFILE containing a CLI description (json/yaml) as local PATH or http URL.'
    )
    parser.add_argument(
        'job_file', action='store', type=str, metavar='JOBFILE',
        help='JOBFILE in the CWL job format (json/yaml) as local PATH or http URL.'
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
        '--prefix', action='store', type=str, metavar='PREFIX', default='faice_',
        help='PREFIX for files dumped to storage, default is "faice_".'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()

    result = run(**args.__dict__)

    format = args.__dict__['format']
    debug = args.__dict__['debug']
    if debug:
        dump_print(result, format)

    if result['state'] == 'succeeded':
        return 0

    return 1


def run(cwl_file,
        job_file,
        format,
        disable_pull,
        leave_container,
        preserve_environment,
        prefix,
        **_
        ):
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
        'debugInfo': None,
        'state': 'succeeded'
    }

    try:
        import cc_core.agent.cwl.__main__

        source_paths, c_source_paths = module_dependencies([cc_core.agent.cwl.__main__])
        module_mounts = module_destinations(source_paths)
        interpreter_deps = interpreter_dependencies(c_source_paths)
        interpreter_mounts = interpreter_destinations(interpreter_deps)

        cwl_data = load_and_read(cwl_file, 'CWLFILE')
        job_data = load_and_read(job_file, 'JOBFILE')

        cwl_validation(cwl_data, job_data, docker_requirement=True)

        ext = file_extension(format)
        input_dir = os.path.split(os.path.expanduser(job_file))[0]
        outputs_dir = 'outputs'
        dumped_job_file = '{}job.{}'.format(prefix, ext)
        dumped_cwl_file = '{}.cwl'.format(prefix)

        if not is_local(cwl_file):
            dump(cwl_data, format, dumped_cwl_file)
            cwl_file = dumped_cwl_file

        mapped_input_dir = '/cwl/inputs'
        mapped_outputs_dir = '/cwl/outputs'
        mapped_cwl_file = '/cwl/cli.cwl'
        mapped_job_file = '/cwl/job.{}'.format(ext)

        dumped_job_data = dump_job(job_data, mapped_input_dir)

        ro_mappings = input_volume_mappings(job_data, dumped_job_data, input_dir)
        ro_mappings += [
            [os.path.abspath(cwl_file), mapped_cwl_file],
            [os.path.abspath(dumped_job_file), mapped_job_file]
        ]
        ro_mappings += module_mounts
        ro_mappings += interpreter_mounts
        rw_mappings = [[os.path.abspath(outputs_dir), mapped_outputs_dir]]

        result['container']['volumes']['readOnly'] = ro_mappings
        result['container']['volumes']['readWrite'] = rw_mappings

        container_name = str(uuid4())
        result['container']['name'] = container_name
        docker_manager = DockerManager()

        image = cwl_data['requirements']['DockerRequirement']['dockerPull']
        if not disable_pull:
            docker_manager.pull(image)

        command = interpreter_command()
        command += [
            '-m',
            'cc_core.agent.cwl',
            mapped_cwl_file,
            mapped_job_file,
            '--debug',
            '--format=json',
            '--leave-directories'
        ]

        command = ' '.join([str(c) for c in command])
        command = "/bin/sh -c '{}'".format(command)

        result['container']['command'] = command

        if not os.path.exists(outputs_dir):
            os.makedirs(outputs_dir)

        dump(dumped_job_data, format, dumped_job_file)

        environment = env_vars(preserve_environment)

        ccagent_data = docker_manager.run_container(
            container_name,
            image,
            command,
            ro_mappings,
            rw_mappings,
            mapped_outputs_dir,
            leave_container,
            None,
            environment
        )
        result['container']['ccagent'] = ccagent_data[0]
        docker_result_check(ccagent_data)
    except Exception as e:
        result['debugInfo'] = exception_format()
        result['state'] = 'failed'
        print_exception(e)

    return result
