from collections import OrderedDict

from cc_faice.version import VERSION

from cc_faice.agent.main import main as agent_main
from cc_faice.schemas.main import main as schemas_main
from cc_faice.file_server.main import main as file_server_main
from cc_faice.export.main import main as export_main

from cc_faice.agent.main import DESCRIPTION as AGENT_DESCRIPTION
from cc_faice.schemas.main import DESCRIPTION as SCHEMAS_DESCRIPTION
from cc_faice.file_server.main import DESCRIPTION as FILE_SERVER_DESCRIPTION
from cc_faice.export.main import DESCRIPTION as EXPORT_DESCRIPTION

from cc_core.commons.cli_modes import cli_modes


SCRIPT_NAME = 'faice'
TITLE = 'tools'
DESCRIPTION = 'FAICE Copyright (C) 2018  Christoph Jansen. This software is distributed under the AGPL-3.0 ' \
              'LICENSE and is part of the Curious Containers project (https://www.curious-containers.cc).'
MODES = OrderedDict([
    ('agent', {'main': agent_main, 'description': AGENT_DESCRIPTION}),
    ('export', {'main': export_main, 'description': EXPORT_DESCRIPTION}),
    ('schemas', {'main': schemas_main, 'description': SCHEMAS_DESCRIPTION}),
    ('file-server', {'main': file_server_main, 'description': FILE_SERVER_DESCRIPTION})
])


def main():
    cli_modes(SCRIPT_NAME, TITLE, DESCRIPTION, MODES, VERSION)
