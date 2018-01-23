from collections import OrderedDict

from cc_faice.export.ccagent_cwl.main import main as cwl_main
from cc_faice.export.ccagent_red.main import main as red_main

from cc_faice.export.ccagent_cwl.main import DESCRIPTION as CWL_DESCRIPTION
from cc_faice.export.ccagent_red.main import DESCRIPTION as RED_DESCRIPTION

from cc_core.commons.cli_modes import cli_modes


SCRIPT_NAME = 'faice schemas'
TITLE = 'modes'
DESCRIPTION = 'Export RED_FILE to pure CWL (compatible with cwltool).'
MODES = OrderedDict([
    ('ccagent-cwl', {'main': cwl_main, 'description': CWL_DESCRIPTION}),
    ('ccagent-red', {'main': red_main, 'description': RED_DESCRIPTION})
])


def main():
    cli_modes(SCRIPT_NAME, TITLE, DESCRIPTION, MODES)
