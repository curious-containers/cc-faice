import jsonschema
from copy import deepcopy
from jinja2 import Template, Environment, meta

from cc_core.commons.schemas.red import red_schema
from cc_core.commons.exceptions import RedSpecificationError
from cc_core.commons.cwl_io import cwl_io_validation

from cc_faice.version import RED_VERSION
from cc_faice.commons.formatting import wrapped_print


def red_validation(red_data):
    try:
        jsonschema.validate(red_data, red_schema)
    except:
        raise RedSpecificationError('red does not comply with jsonschema')

    red_version = red_data['redVersion']
    cwl_data = red_data['cli']
    inputs_data = red_data['inputs']
    outputs_data = red_data['outputs']

    if not red_version == RED_VERSION:
        raise RedSpecificationError(
            'red version "{}" specified in RED_FILE is not compatible with red version "{}" of cc-faice'.format(
                red_version, RED_VERSION
            )
        )

    cwl_io_validation(cwl_data, inputs_data, outputs_data)


def parse_and_fill_template(template, template_values, non_interactive):
    template_values_copy = deepcopy(template_values)
    filled_template = template
    template_variables = _template_variables(template)

    if template_variables:
        remaining_template_variables = [v for v in template_variables if v not in template_values_copy]

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
                template_values_copy[v] = input('{}: '.format(v))

        for v in template_variables:
            if not template_values_copy.get(v):
                template_values_copy[v] = 'null'
        t = Template(template)
        filled_template = t.render(template_values_copy)

    return filled_template


def _template_variables(template):
    environment = Environment()
    ast = environment.parse(template)
    variables = list(meta.find_undeclared_variables(ast))
    variables.sort(reverse=True)
    return variables
