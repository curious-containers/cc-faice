import os
from uuid import uuid4
from argparse import ArgumentParser

from cc_faice.commons.engines import engine_validation

from cc_core.commons.files import load, read, load_and_read, dump, dump_print, file_extension
from cc_core.commons.exceptions import exception_format
from cc_core.commons.red import red_validation

from cc_faice.commons.red import parse_and_fill_template, jinja_validation
from cc_faice.commons.docker import DockerManager


DESCRIPTION = 'Run an experiment as described in a RED_FILE in a container with ccagent (cc_core.agent.cwl_io).'


def attach_args(parser):
    parser.add_argument(
        'red_file', action='store', type=str, metavar='RED_FILE',
        help='RED_FILE (json or yaml) containing an experiment description as local path or http url.'
    )
    parser.add_argument(
        '-j', '--jinja-file', action='store', type=str, metavar='JINJA_FILE',
        help='JINJA_FILE (json or yaml) containing values for jinja template variables in RED_FILE as local path '
             'or http url.'
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
        '--non-interactive', action='store_true',
        help='Do not ask for jinja template values interactively.'
    )
    parser.add_argument(
        '--dump-format', action='store', type=str, metavar='DUMP_FORMAT', choices=['json', 'yaml', 'yml'],
        default='yaml', help='Dump format for data written to files or stdout, default is "yaml".'
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

    return 0


def run(
        red_file,
        jinja_file,
        outdir,
        disable_pull,
        leave_container,
        non_interactive,
        dump_format,
        ignore_outputs
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
        'debugInfo': None
    }

    try:
        red_raw = load(red_file, 'RED_FILE')

        jinja_data = None
        if jinja_file:
            jinja_data = load_and_read(jinja_file, 'JINJA_FILE')
            jinja_validation(jinja_data)

        red_raw_filled = parse_and_fill_template(red_raw, jinja_data, non_interactive)
        red_data = read(red_raw_filled, 'RED_FILE')
        red_validation(red_data, ignore_outputs, container_requirement=True)
        engine_validation(red_data, 'container', ['docker'], 'faice agent red')

        ext = file_extension(dump_format)
        work_dir = 'work'

        mapped_work_dir = '/opt/cc/work'
        mapped_red_file = '/opt/cc/red.{}'.format(ext)

        container_name = str(uuid4())
        result['container']['name'] = container_name
        docker_manager = DockerManager()

        image = red_data['container']['settings']['image']['url']
        registry_auth = red_data['container']['settings']['image'].get('auth')
        if not disable_pull:
            docker_manager.pull(image, auth=registry_auth)

        command = 'ccagent red {} --dump-format={}'.format(
            mapped_red_file,
            dump_format
        )

        if outdir:
            command = '{} --outdir={}'.format(command, outdir)

        if ignore_outputs:
            command = '{} --ignore-outputs'.format(command)

        result['container']['command'] = command

        ro_mappings = [[os.path.abspath(red_file), mapped_red_file]]
        rw_mappings = [[os.path.abspath(work_dir), mapped_work_dir]]

        result['container']['volumes']['readOnly'] = ro_mappings
        result['container']['volumes']['readWrite'] = rw_mappings

        if not os.path.exists(work_dir):
            os.makedirs(work_dir)

        ccagent_data = docker_manager.run_container(
            container_name, image, command, ro_mappings, rw_mappings, mapped_work_dir, leave_container
        )
        result['container']['ccagent'] = ccagent_data
    except:
        result['debugInfo'] = exception_format()

    return result
