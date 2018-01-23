import os
from uuid import uuid4
from argparse import ArgumentParser

from cc_core.commons.files import load, read, load_and_read, dump, dump_print, file_extension
from cc_core.commons.exceptions import exception_format

from cc_faice.commons.compatibility import version_validation
from cc_faice.commons.red import parse_and_fill_template, red_validation, jinja_validation
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
        '--dump-format', action='store', type=str, metavar='DUMP_FORMAT', choices=['json', 'yaml'], default='json',
        help='Dump format for data generated or aggregated by the agent.'
    )


def main():
    version_validation()
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()

    result = run(**args.__dict__)
    dump_print(result, args.dump_format)

    return 0


def run(red_file, jinja_file, outdir, disable_pull, leave_container, non_interactive, dump_format):
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
        red_validation(red_data)

        ext = file_extension(dump_format)
        work_dir = os.path.join(os.getcwd(), 'work')
        cwl_export_file = os.path.join(os.getcwd(), 'cwl-export.{}'.format(ext))
        red_inputs_export_file = os.path.join(os.getcwd(), 'red-inputs-export.{}'.format(ext))
        red_outputs_export_file = os.path.join(os.getcwd(), 'red-outputs-export.{}'.format(ext))

        mapped_work_dir = '/opt/cc/work'
        mapped_cwl_export_file = os.path.join('/opt/cc/cwl-export.{}'.format(ext))
        mapped_red_inputs_export_file = os.path.join('/opt/cc/red-inputs-export.{}'.format(ext))
        mapped_red_outputs_export_file = os.path.join('/opt/cc/red-outputs-export.{}'.format(ext))

        ro_mappings = [
            [cwl_export_file, mapped_cwl_export_file],
            [red_inputs_export_file, mapped_red_inputs_export_file],
            [red_outputs_export_file, mapped_red_outputs_export_file]
        ]
        rw_mappings = [[work_dir, mapped_work_dir]]

        result['container']['volumes']['readOnly'] = ro_mappings
        result['container']['volumes']['readWrite'] = rw_mappings

        container_name = str(uuid4())
        result['container']['name'] = container_name
        docker_manager = DockerManager()

        image = red_data['container']['settings']['image']['url']
        registry_auth = red_data['container']['settings']['image'].get('auth')
        if not disable_pull:
            docker_manager.pull(image, auth=registry_auth)

        command = 'ccagent red {} {} -o {} --dump-format={}'.format(
            mapped_cwl_export_file,
            mapped_red_inputs_export_file,
            mapped_red_outputs_export_file,
            dump_format
        )
        if outdir:
            command = '{} --outdir={}'.format(command, outdir)
        result['container']['command'] = command

        if not os.path.exists(work_dir):
            os.makedirs(work_dir)

        dump(red_data['cli'], dump_format, cwl_export_file)
        dump(red_data['inputs'], dump_format, red_inputs_export_file)
        dump(red_data['outputs'], dump_format, red_outputs_export_file)

        ccagent_data = docker_manager.run_container(
            container_name, image, command, ro_mappings, rw_mappings, mapped_work_dir, leave_container
        )
        result['container']['ccagent'] = ccagent_data
    except:
        result['debugInfo'] = exception_format()

    return result