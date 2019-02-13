from argparse import ArgumentParser

import requests

from cc_core.commons.files import load_and_read, wrapped_print, dump_print
from cc_core.commons.red import red_validation
from cc_core.commons.templates import inspect_templates_and_secrets, fill_template, fill_validation
from cc_core.commons.engines import engine_validation

from cc_faice.agent.red.main import run as run_faice_agent_red


DESCRIPTION = 'Execute experiment according to execution engine defined in REDFILE.'


def attach_args(parser):
    parser.add_argument(
        'red_file', action='store', type=str, metavar='REDFILE',
        help='REDFILE (json or yaml) containing an experiment description as local PATH or http URL.'
    )
    parser.add_argument(
        '-v', '--variables', action='store', type=str, metavar='VARFILE',
        help='VARFILE (json or yaml) containing key-value pairs for variables in REDFILE as '
             'local PATH or http URL.'
    )
    parser.add_argument(
        '--non-interactive', action='store_true',
        help='Do not ask for RED variables interactively.'
    )
    parser.add_argument(
        '--format', action='store', type=str, metavar='FORMAT', choices=['json', 'yaml', 'yml'], default='yaml',
        help='Specify FORMAT for generated data as one of [json, yaml, yml]. Default is yaml.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    return run(**args.__dict__)


def run(red_file, variables, non_interactive, format):
    red_data = load_and_read(red_file, 'REDFILE')
    red_validation(red_data, False)
    engine_validation(red_data, 'execution', ['ccfaice', 'ccagency'], 'faice exec')

    # exec via CC-FAICE
    # equivalent to `faice agent red --debug --outputs`
    if red_data['execution']['engine'] == 'ccfaice':
        insecure = red_data['execution']['settings'].get('insecure')
        result = run_faice_agent_red(red_file, variables, True, format, None, None, None, None, None, insecure)
        dump_print(result, 'yaml')

        if result['state'] == 'succeeded':
            return 0

        return 1

    # exec via CC-Agency
    fill_data = None
    if variables:
        fill_data = load_and_read(variables, 'VARFILE')
        fill_validation(fill_data)

    template_keys_and_values, secret_values, _ = inspect_templates_and_secrets(red_data, fill_data, non_interactive)
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

    dump_print(r.json(), format)

    return 0
