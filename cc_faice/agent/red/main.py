import os
import stat
from uuid import uuid4
from argparse import ArgumentParser

from cc_core.commons.files import load_and_read, dump, dump_print, file_extension
from cc_core.commons.exceptions import exception_format, RedValidationError
from cc_core.commons.red import red_validation
from cc_core.commons.templates import fill_validation, fill_template, inspect_templates_and_secrets
from cc_core.commons.engines import engine_validation, engine_to_runtime

from cc_faice.commons.docker import DockerManager, docker_result_check, env_vars
from cc_core.commons.gpu_info import get_gpu_requirements, match_gpus, get_devices


DESCRIPTION = 'Run an experiment as described in a RED_FILE in a container with ccagent (cc_core.agent.cwl_io).'


def attach_args(parser):
    parser.add_argument(
        'red_file', action='store', type=str, metavar='RED_FILE',
        help='RED_FILE (json or yaml) containing an experiment description as local path or http url.'
    )
    parser.add_argument(
        '--fill-file', action='store', type=str, metavar='FILL_FILE',
        help='FILL_FILE (json or yaml) containing key-value pairs for template variables in RED_FILE as '
             'local path or http url.'
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
        '--preserve-environment', action='append', type=str, metavar='ENVVAR',
        help='Preserve specific environment variables when running container. May be provided multiple times.'
    )
    parser.add_argument(
        '--non-interactive', action='store_true',
        help='Do not ask for jinja template values interactively.'
    )
    parser.add_argument(
        '--dump-format', action='store', type=str, metavar='DUMP_FORMAT', choices=['json', 'yaml', 'yml'],
        default='yaml', help='Dump format for data written to files or stdout, choices are "json" or "yaml", default '
                             'is "yaml".'
    )
    parser.add_argument(
        '--dump-prefix', action='store', type=str, metavar='DUMP_PREFIX', default='dumped_',
        help='Name prefix for files dumped to storage, default is "dumped_".'
    )
    parser.add_argument(
        '--ignore-outputs', action='store_true',
        help='Ignore RED connectors specified in RED_FILE outputs section.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()

    result = run(**args.__dict__)
    dump_print(result, args.dump_format)

    if result['state'] == 'succeeded':
        return 0

    return 1


def get_runtime(red_data):
    """
    Extracts the docker runtime string.

    :param red_data: The yaml data of the job file as python dictionary
    :return: A String specifing the docker runtime (one of: 'docker', 'nvidia-docker')
    """

    return engine_to_runtime(red_data['container']['engine'])


def run(
        red_file,
        fill_file,
        outdir,
        disable_pull,
        leave_container,
        preserve_environment,
        non_interactive,
        dump_format,
        dump_prefix,
        ignore_outputs
):
    result = {
        'containers': [],
        'debugInfo': None,
        'state': 'succeeded'
    }

    secret_values = None
    ext = file_extension(dump_format)
    dumped_fill_file = '{}fill.{}'.format(dump_prefix, ext)

    try:
        red_data = load_and_read(red_file, 'RED_FILE')
        red_validation(red_data, ignore_outputs, container_requirement=True)
        engine_validation(red_data, 'container', ['docker', 'nvidia-docker'], 'faice agent red')

        fill_data = None
        if fill_file:
            fill_data = load_and_read(fill_file, 'FILL_FILE')
            fill_validation(fill_data)

        template_keys_and_values, secret_values = inspect_templates_and_secrets(red_data, fill_data, non_interactive)

        if template_keys_and_values:
            dump(template_keys_and_values, dump_format, dumped_fill_file)

        docker_manager = DockerManager()

        runtime = get_runtime(red_data)

        gpu_requirements = get_gpu_requirements(red_data['container']['settings'].get('gpus'))
        gpu_devices = get_devices(red_data['container']['engine'])
        gpus = match_gpus(gpu_devices, gpu_requirements)

        ram = red_data['container']['settings'].get('ram')
        image = red_data['container']['settings']['image']['url']
        registry_auth = red_data['container']['settings']['image'].get('auth')
        registry_auth = fill_template(registry_auth, template_keys_and_values, True, True)

        if not disable_pull:
            docker_manager.pull(image, auth=registry_auth)

    except RedValidationError:
        result['debugInfo'] = exception_format(secret_values=secret_values)
        result['state'] = 'failed'
        return result
    except:
        result['debugInfo'] = exception_format()
        result['state'] = 'failed'
        return result

    batches = [None]
    if 'batches' in red_data:
        batches = list(range(len(red_data['batches'])))

    for batch in batches:
        container_result = {
            'command': None,
            'name': None,
            'volumes': {
                'readOnly': None,
                'readWrite': None
            },
            'ccagent': None,
            'debugInfo': None,
            'state': 'succeeded'
        }
        result['containers'].append(container_result)
        try:
            if batch is None:
                work_dir = 'work'
            else:
                work_dir = 'work_{}'.format(batch)

            mapped_work_dir = '/opt/cc/work'
            mapped_red_file = '/opt/cc/red.{}'.format(ext)
            mapped_fill_file = '/opt/cc/fill.{}'.format(ext)

            container_name = str(uuid4())
            container_result['name'] = container_name

            command = [
                'ccagent',
                'red',
                mapped_red_file,
                '--dump-format={}'.format(dump_format)
            ]

            if batch is not None:
                command.append('--batch={}'.format(batch))

            if outdir:
                command.append('--outdir={}'.format(outdir))

            if ignore_outputs:
                command.append('--ignore-outputs')

            if template_keys_and_values:
                command.append('--fill-file={}'.format(mapped_fill_file))

            command = ' '.join([str(c) for c in command])

            container_result['command'] = command

            ro_mappings = [[os.path.abspath(red_file), mapped_red_file]]
            rw_mappings = [[os.path.abspath(work_dir), mapped_work_dir]]

            if template_keys_and_values:
                rw_mappings.append([os.path.abspath(dumped_fill_file), mapped_fill_file])

            container_result['volumes']['readOnly'] = ro_mappings
            container_result['volumes']['readWrite'] = rw_mappings

            old_work_dir_permissions = None
            if not os.path.exists(work_dir):
                os.makedirs(work_dir)
            if os.getuid() != 1000:
                old_work_dir_permissions = os.stat(work_dir).st_mode
                os.chmod(work_dir, old_work_dir_permissions | stat.S_IWOTH)

            environment = env_vars(preserve_environment)

            ccagent_data = docker_manager.run_container(
                name=container_name,
                image=image,
                command=command,
                ro_mappings=ro_mappings,
                rw_mappings=rw_mappings,
                work_dir=mapped_work_dir,
                leave_container=leave_container,
                ram=ram,
                runtime=runtime,
                gpus=gpus,
                environment=environment
            )
            if old_work_dir_permissions is not None:
                os.chmod(work_dir, old_work_dir_permissions)
            container_result['ccagent'] = ccagent_data
            docker_result_check(ccagent_data)
        except:
            container_result['debugInfo'] = exception_format()
            container_result['state'] = 'failed'
            result['state'] = 'failed'
            break

    if os.path.exists(dumped_fill_file):
        os.remove(dumped_fill_file)

    return result
