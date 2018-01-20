import os
import json
from argparse import ArgumentParser

from cc_core.commons.files import load_and_read
from cc_core.commons.cwl import cwl_to_command, cwl_validation
from cc_core.commons.cwl import cwl_input_files, cwl_output_files, cwl_input_file_check, cwl_output_file_check
from cc_core.commons.shell import execute
from cc_core.commons.exceptions import exception_format


DESCRIPTION = 'Run a CommandLineTool as described in a CWL_FILE and its corresponding JOB_FILE in a container.'


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
        help='Output directory in container, default directory is current working directory.'
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


def run(cwl_file, job_file, outdir):
    result = {
        'command': None,
        'input_files': None,
        'process_data': None,
        'output_files': None,
        'debug_info': None
    }

    try:
        cwl_data = load_and_read(cwl_file, 'CWL_FILE')
        job_data = load_and_read(job_file, 'JOB_FILE')

        cwl_validation(cwl_data, job_data)

        input_dir = os.path.split(os.path.expanduser(job_file))[0]
        container_input_dir = '/cwl/inputs'
        container_output_dir = '/cwl/workdir'

        command = cwl_to_command(cwl_data, job_data, input_dir=input_dir, check_base_command=False)
        result['command'] = command

        input_files = cwl_input_files(cwl_data, job_data, input_dir=input_dir)
        result['input_files'] = input_files

        cwl_input_file_check(input_files)

        process_data = execute(command)
        result['process_data'] = process_data

        output_files = cwl_output_files(cwl_data, output_dir=outdir)
        result['output_files'] = output_files

        cwl_output_file_check(output_files)
    except:
        result['debug_info'] = exception_format()

    return result
