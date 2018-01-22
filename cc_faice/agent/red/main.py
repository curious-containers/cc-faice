import json
from argparse import ArgumentParser

from cc_core.commons.files import load, read, load_and_read
from cc_core.commons.exceptions import exception_format

from cc_faice.commons.compatibility import version_validation
from cc_faice.commons.red import parse_and_fill_template
from cc_faice.commons.red import red_validation


DESCRIPTION = 'Run an experiment as described in a RED_FILE in a container with ccagent (cc_core.agent.cwl_io).'


def attach_args(parser):
    parser.add_argument(
        '-r', '--red-file', action='store', type=str, metavar='RED_FILE', required=True,
        help='RED_FILE (json or yaml) containing an experiment description as local path or http url.'
    )
    parser.add_argument(
        '-t', '--template_values_file', action='store', type=str, metavar='TEMPLATE_VALUES_FILE',
        help='TEMPLATE_VALUES_FILE (json or yaml) containing values for RED_FILE template variables as local path '
             'or http url.'
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
    version_validation()
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()

    result = run(**args.__dict__)
    print(json.dumps(result, indent=4))

    return 0


def run(red_file, template_values_file, outdir, disable_pull, leave_container):
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

        template_values_data = {}
        if template_values_file:
            template_values_data = load_and_read(template_values_file, 'TEMPLATE_VALUES_FILE')

        red_raw_filled = parse_and_fill_template(red_raw, template_values_data, False)
        red_data = read(red_raw_filled, 'RED_FILE')

        red_validation(red_data)
    except:
        result['debugInfo'] = exception_format()

    return result