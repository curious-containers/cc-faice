from collections import OrderedDict

from cc_faice.schemas.list.main import main as list_main
from cc_faice.schemas.show.main import main as show_main
from cc_faice.schemas.validate.main import main as validate_main

from cc_faice.schemas.list.main import DESCRIPTION as LIST_DESCRIPTION
from cc_faice.schemas.show.main import DESCRIPTION as SHOW_DESCRIPTION
from cc_faice.schemas.validate.main import DESCRIPTION as VALIDATE_DESCRIPTION

from cc_core.commons.cli_modes import cli_modes


SCRIPT_NAME = 'faice schemas'
TITLE = 'modes'
DESCRIPTION = 'List or show jsonschemas defined in cc-core.'
MODES = OrderedDict([
    ('list', {'main': list_main, 'description': LIST_DESCRIPTION}),
    ('show', {'main': show_main, 'description': SHOW_DESCRIPTION}),
    ('validate', {'main': validate_main, 'description': VALIDATE_DESCRIPTION})
])


def main():
    cli_modes(SCRIPT_NAME, TITLE, DESCRIPTION, MODES)
