import json
from argparse import ArgumentParser

from cc_core.commons.files import load, read, load_and_read, dump_print
from cc_core.commons.exceptions import exception_format

from cc_faice.commons.compatibility import version_validation
from cc_faice.commons.red import parse_and_fill_template, red_validation, jinja_validation


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


def run(red_file, jinja_file, outdir, disable_pull, leave_container, non_interactive):
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
    except:
        result['debugInfo'] = exception_format()

    return result
