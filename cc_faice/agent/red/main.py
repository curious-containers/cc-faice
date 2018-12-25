import os
import stat
from uuid import uuid4
from argparse import ArgumentParser

from cc_core.commons.files import load_and_read, dump, dump_print, file_extension
from cc_core.commons.exceptions import exception_format, RedValidationError, print_exception
from cc_core.commons.red import red_validation
from cc_core.commons.templates import fill_validation, fill_template, inspect_templates_and_secrets
from cc_core.commons.engines import engine_validation, engine_to_runtime

from cc_faice.commons.docker import DockerManager, docker_result_check, env_vars
from cc_core.commons.gpu_info import get_gpu_requirements, match_gpus, get_devices

DESCRIPTION = 'Run an experiment as described in a RED_FILE in a container with ccagent red.'


def attach_args(parser):
    parser.add_argument(
        'red_file', action='store', type=str, metavar='RED_FILE',
        help='RED FILE (json or yaml) containing an experiment description as local PATH or http URL.'
    )
    parser.add_argument(
        '-v', '--variables', action='store', type=str, metavar='VARIABLES_FILE',
        help='VARIABLES_FILE (json or yaml) containing key-value pairs for variables in RED_FILE as '
             'local PATH or http URL.'
    )
    parser.add_argument(
        '-o', '--outputs', action='store_true',
        help='Enable connectors specified in the RED FILE outputs section.'
    )
    parser.add_argument(
        '-m', '--meta', action='store_true',
        help='Write meta data, including detailed exceptions, to stdout.'
    )
    parser.add_argument(
        '--format', action='store', type=str, metavar='FORMAT', choices=['json', 'yaml', 'yml'], default='yaml',
        help='Specify meta data FORMAT as one of [json, yaml, yml]. Default is yaml.'
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
        help='Do not ask for RED variables interactively.'
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
    meta = args.__dict__['meta']
    if meta:
        dump_print(result, format)

    if result['state'] == 'succeeded':
        return 0

    return 1


def run(red_file,
        variables_file,
        outputs,
        format,
        disable_pull,
        leave_container,
        preserve_environment,
        non_interactive,
        prefix,
        **_
        ):
    result = {
        'containers': [],
        'debugInfo': None,
        'state': 'succeeded'
    }

    secret_values = None
    ext = file_extension(format)
    dumped_variables_file = '{}variables.{}'.format(prefix, ext)

    try:
        red_data = load_and_read(red_file, 'RED_FILE')
        ignore_outputs = not outputs
        red_validation(red_data, ignore_outputs, container_requirement=True)
        engine_validation(red_data, 'container', ['docker', 'nvidia-docker'], 'faice agent red')

        variables_data = None
        if variables_file:
            variables_data = load_and_read(variables_file, 'VARIABLES_FILE')
            fill_validation(variables_data)

        template_keys_and_values, secret_values = inspect_templates_and_secrets(red_data, variables_data, non_interactive)

        if template_keys_and_values:
            dump(template_keys_and_values, format, dumped_variables_file)

        docker_manager = DockerManager()

        runtime = engine_to_runtime(red_data['container']['engine'])

        gpu_requirements = get_gpu_requirements(red_data['container']['settings'].get('gpus'))
        gpu_devices = get_devices(red_data['container']['engine'])
        gpus = match_gpus(gpu_devices, gpu_requirements)

        ram = red_data['container']['settings'].get('ram')
        image = red_data['container']['settings']['image']['url']
        registry_auth = red_data['container']['settings']['image'].get('auth')
        registry_auth = fill_template(registry_auth, template_keys_and_values, True, True)

        if not disable_pull:
            docker_manager.pull(image, auth=registry_auth)

    except RedValidationError as e:
        result['debugInfo'] = exception_format(secret_values=secret_values)
        result['state'] = 'failed'
        print_exception(e)
        return result
    except Exception as e:
        result['debugInfo'] = exception_format()
        result['state'] = 'failed'
        print_exception(e)
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
                outputs_dir = 'outputs'
            else:
                outputs_dir = 'outputs_{}'.format(batch)

            mapped_outputs_dir = '/opt/cc/outputs'
            mapped_red_file = '/opt/cc/red.{}'.format(ext)
            mapped_variables_file = '/opt/cc/variables.{}'.format(ext)

            container_name = str(uuid4())
            container_result['name'] = container_name

            command = [
                'ccagent',
                'red',
                mapped_red_file,
                '--meta',
                '--format=json',
                '--leave-directories'
            ]

            if batch is not None:
                command.append('--batch={}'.format(batch))

            if outputs:
                command.append('--outputs')

            if template_keys_and_values:
                command.append('--variables={}'.format(mapped_variables_file))

            command = ' '.join([str(c) for c in command])

            container_result['command'] = command

            ro_mappings = [[os.path.abspath(red_file), mapped_red_file]]
            rw_mappings = []

            work_dir = None
            old_outputs_dir_permissions = None

            if not outputs:
                rw_mappings.append([os.path.abspath(outputs_dir), mapped_outputs_dir])
                work_dir = mapped_outputs_dir

                if not os.path.exists(outputs_dir):
                    os.makedirs(outputs_dir)
                if os.getuid() != 1000:
                    old_outputs_dir_permissions = os.stat(outputs_dir).st_mode
                    os.chmod(outputs_dir, old_outputs_dir_permissions | stat.S_IWOTH)

            if template_keys_and_values:
                rw_mappings.append([os.path.abspath(dumped_variables_file), mapped_variables_file])

            container_result['volumes']['readOnly'] = ro_mappings
            container_result['volumes']['readWrite'] = rw_mappings

            environment = env_vars(preserve_environment)

            ccagent_data = docker_manager.run_container(
                name=container_name,
                image=image,
                command=command,
                ro_mappings=ro_mappings,
                rw_mappings=rw_mappings,
                work_dir=work_dir,
                leave_container=leave_container,
                ram=ram,
                runtime=runtime,
                gpus=gpus,
                environment=environment
            )
            if old_outputs_dir_permissions is not None:
                os.chmod(outputs_dir, old_outputs_dir_permissions)
            container_result['ccagent'] = ccagent_data[0]
            docker_result_check(ccagent_data)
        except Exception as e:
            container_result['debugInfo'] = exception_format()
            container_result['state'] = 'failed'
            result['state'] = 'failed'
            print_exception(e)
            break

    if os.path.exists(dumped_variables_file):
        os.remove(dumped_variables_file)

    return result
