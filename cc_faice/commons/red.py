import jsonschema
from copy import deepcopy
from jinja2 import Template, Environment, meta

from cc_core.commons.files import wrapped_print
from cc_core.commons.schemas.red import red_jinja_schema
from cc_core.commons.exceptions import RedSpecificationError


def dump_agent_cwl(red_data, stdout_file):
    return {
        'cwlVersion': 'v1.0',
        'class': 'CommandLineTool',
        'baseCommand': ['ccagent', 'red'],
        'doc': '',
        'requirements': {
            'DockerRequirement': {
                'dockerPull': red_data['container']['settings']['image']['url']
            }
        },
        'inputs': {
            'red-file': {
                'type': 'File',
                'inputBinding': {
                    'position': 0
                }
            },
            'outdir': {
                'type': 'string?',
                'inputBinding': {
                    'prefix': '--outdir=',
                    'separate': False
                }
            },
            'dump-format': {
                'type': 'string?',
                'inputBinding': {
                    'prefix': '--dump-format=',
                    'separate': False
                }
            },
            'ignore_outputs': {
                'type': 'boolean?',
                'inputBinding': {
                    'prefix': '--ignore-outputs',
                }
            },
        },
        'outputs': {
            'standard-out': {
                'type': 'stdout'
            }
        },
        'stdout': stdout_file
    }


def dump_agent_job(app_red_file, outdir, dump_format, ignore_outputs):
    agent_job = {
        'red-file': {
            'class': 'File',
            'path': app_red_file
        },
        'dump_format': dump_format
    }

    if outdir:
        agent_job['outdir'] = outdir

    if ignore_outputs:
        agent_job['ignore_outputs'] = ignore_outputs

    return agent_job


def dump_app_cwl(red_data):
    app_cwl = deepcopy(red_data['cli'])
    app_cwl['requirements'] = {
        'DockerRequirement': {
            'dockerPull': red_data['container']['settings']['image']['url']
        }
    }
    return app_cwl


def jinja_validation(jinja_data):
    try:
        jsonschema.validate(jinja_data, red_jinja_schema)
    except:
        raise RedSpecificationError('jinja file does not comply with jsonschema')


def parse_and_fill_template(template, jinja_data, non_interactive):
    template_values = {}
    if jinja_data:
        template_values = deepcopy(jinja_data)
    filled_template = template
    template_variables = _template_variables(template)

    if template_variables:
        remaining_template_variables = [v for v in template_variables if v not in template_values]

        if remaining_template_variables and not non_interactive:
            out = [
                '{} contains the following undeclared variables:'.format('RED_FILE')
            ]
            out += remaining_template_variables
            out += [
                '',
                'Set variables interactively...',
                ''
            ]
            wrapped_print(out)

            for v in remaining_template_variables:
                template_values[v] = input('{}: '.format(v))

        for v in template_variables:
            if not template_values.get(v):
                template_values[v] = 'null'
        t = Template(template)
        filled_template = t.render(template_values)

    return filled_template


def _template_variables(template):
    environment = Environment()
    ast = environment.parse(template)
    variables = list(meta.find_undeclared_variables(ast))
    variables.sort(reverse=True)
    return variables
