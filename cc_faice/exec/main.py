from argparse import ArgumentParser

import requests

from cc_core.commons.files import load_and_read, wrapped_print, dump_print
from cc_core.commons.red import red_validation
from cc_core.commons.templates import inspect_templates_and_secrets, fill_template, fill_validation
from cc_core.commons.engines import engine_validation


DESCRIPTION = 'Execute experiment according to execution engine defined in RED_FILE.'


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
        '--non-interactive', action='store_true',
        help='Do not ask for jinja template values interactively.'
    )
    parser.add_argument(
        '--dump-format', action='store', type=str, metavar='DUMP_FORMAT', choices=['json', 'yaml', 'yml'],
        default='yaml', help='Dump format for data written to files or stdout, choices are "json" or "yaml", default '
                             'is "yaml".'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    return run(**args.__dict__)


def run(red_file, fill_file, non_interactive, dump_format):
    red_data = load_and_read(red_file, 'RED_FILE')
    red_validation(red_data, False)
    engine_validation(red_data, 'execution', ['ccagency'], 'faice exec')

    fill_data = None
    if fill_file:
        fill_data = load_and_read(fill_file, 'FILL_FILE')
        fill_validation(fill_data)

    template_keys_and_values, secret_values = inspect_templates_and_secrets(red_data, fill_data, non_interactive)
    red_data = fill_template(red_data, template_keys_and_values, False, False)
    red_data_removed_underscores = fill_template(red_data, template_keys_and_values, False, True)

    if 'access' not in red_data['execution']['settings']:
        wrapped_print([
            'ERROR: cannot send RED data to CC-Agency if access settings are not defined.'
        ], error=True)
        return 1

    if 'auth' not in red_data['execution']['settings']['access']:
        wrapped_print([
            'ERROR: cannot send RED data to CC-Agency if auth is not defined in access settings.'
        ], error=True)
        return 1

    access = red_data_removed_underscores['execution']['settings']['access']

    r = requests.post(
        '{}/red'.format(access['url'].strip('/')),
        auth=(
            access['auth']['username'],
            access['auth']['password']
        ),
        json=red_data
    )
    try:
        r.raise_for_status()
    except:
        wrapped_print(r.text.split('\n'), error=True)
        return 1

    dump_print(r.json(), dump_format)

    return 0
