import os
from argparse import ArgumentParser

from cc_core.commons.files import load, read, load_and_read, dump, dump_print, file_extension

from cc_faice.commons.engines import engine_validation
from cc_faice.commons.red import parse_and_fill_template, red_validation, jinja_validation


DESCRIPTION = 'Export RED_FILE to standard CWL compatible with cwltool.'


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
        '--non-interactive', action='store_true',
        help='Do not ask for jinja template values interactively.'
    )
    parser.add_argument(
        '--dump-format', action='store', type=str, metavar='DUMP_FORMAT', choices=['json', 'yaml', 'yml'],
        default='yaml', help='Dump format for data written to files or stdout.'
    )
    parser.add_argument(
        '--dump-prefix', action='store', type=str, metavar='DUMP_PREFIX', default='dumped_',
        help='Name prefix for files dumped to storage.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    run(**args.__dict__)
    return 0


def run(red_file, jinja_file, outdir, non_interactive, dump_format, dump_prefix):
    red_raw = load(red_file, 'RED_FILE')

    jinja_data = None
    if jinja_file:
        jinja_data = load_and_read(jinja_file, 'JINJA_FILE')
        jinja_validation(jinja_data)

    red_raw_filled = parse_and_fill_template(red_raw, jinja_data, non_interactive)
    red_data = read(red_raw_filled, 'RED_FILE')
    red_validation(red_data)
    engine_validation(red_data, 'container', ['docker'], 'faice agent red')

    ext = file_extension(dump_format)
    dumped_app_cwl_file = '{}app-cli.cwl'.format(dump_prefix)
    dumped_app_red_inputs_file = '{}app-red-inputs.{}'.format(dump_prefix, ext)
    dumped_app_red_outputs_file = os.path.join(os.getcwd(), '{}app-red-outputs.{}'.format(dump_prefix, ext))
    dumped_app_job_file = os.path.join(os.getcwd(), '{}app-job.{}'.format(dump_prefix, ext))
    dumped_agent_cwl_file = '{}agent-cli.cwl'.format(dump_prefix)
    dumped_agent_job_file = os.path.join(os.getcwd(), '{}agent-job.{}'.format(dump_prefix, ext))
