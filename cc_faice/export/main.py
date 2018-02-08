from argparse import ArgumentParser

from cc_core.commons.files import load, read, load_and_read, dump, file_extension, wrapped_print
from cc_core.commons.red import red_validation

from cc_faice.commons.engines import engine_validation
from cc_faice.commons.red import parse_and_fill_template, jinja_validation, dump_agent_cwl, dump_agent_job, dump_app_cwl
from cc_faice.commons.docker import dump_job


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
        default='yaml', help='Dump format for data written to files or stdout, default is "yaml".'
    )
    parser.add_argument(
        '--dump-prefix', action='store', type=str, metavar='DUMP_PREFIX', default='dumped_',
        help='Name prefix for files dumped to storage, default is "_dumped".'
    )
    parser.add_argument(
        '--ignore-outputs', action='store_true',
        help='Ignore RED connectors specified in RED_FILE outputs section.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    run(**args.__dict__)
    return 0


def run(red_file, jinja_file, outdir, non_interactive, dump_format, dump_prefix, ignore_outputs):
    red_raw = load(red_file, 'RED_FILE')

    jinja_data = None
    if jinja_file:
        jinja_data = load_and_read(jinja_file, 'JINJA_FILE')
        jinja_validation(jinja_data)

    red_raw_filled = parse_and_fill_template(red_raw, jinja_data, non_interactive)
    red_data = read(red_raw_filled, 'RED_FILE')
    red_validation(red_data, False, container_requirement=True)
    engine_validation(red_data, 'container', ['docker'], 'faice export')
    if red_data['container']['settings']['image'].get('auth'):
        wrapped_print([
            'WARNING: cannot export container.settings.image.auth to cwl.',
            ''
        ], error=True)

    ext = file_extension(dump_format)
    dumped_app_cwl_file = '{}app-cli.cwl'.format(dump_prefix)
    dumped_app_red_file = '{}app-red.{}'.format(dump_prefix, ext)
    dumped_app_job_file = '{}app-job.{}'.format(dump_prefix, ext)
    dumped_agent_cwl_file = '{}agent-cli.cwl'.format(dump_prefix)
    dumped_agent_job_file = '{}agent-job.{}'.format(dump_prefix, ext)
    agent_stdout_file = 'agent-stdout.{}'.format(ext)

    dumped_app_job_data = dump_job(red_data['inputs'], '.')
    dumped_agent_cwl_data = dump_agent_cwl(red_data, agent_stdout_file)
    dumped_agent_job_data = dump_agent_job(
        dumped_app_red_file,
        outdir,
        dump_format,
        ignore_outputs
    )
    dumped_app_cwl_data = dump_app_cwl(red_data)

    dump(dumped_app_cwl_data, dump_format, dumped_app_cwl_file)
    dump(red_data, dump_format, dumped_app_red_file)
    dump(dumped_app_job_data, dump_format, dumped_app_job_file)
    dump(dumped_agent_cwl_data, dump_format, dumped_agent_cwl_file)
    dump(dumped_agent_job_data, dump_format, dumped_agent_job_file)

    option2_command = 'cwltool {} {}'.format(dumped_app_cwl_file, dumped_app_job_file)
    if outdir:
        option2_command = '{} --outdir {}'.format(option2_command, outdir)

    wrapped_print([
        'OPTION 1:',
        'Use cwltool to execute app in container via "ccagent red" with support for RED inputs and outputs.',
        '$ cwltool {} {}'.format(dumped_agent_cwl_file, dumped_agent_job_file),
        '',
        'OPTION 2:',
        'Use cwltool to execute app in container with support for local input and output files '
        '(modify input file paths in {} first).'.format(dumped_app_job_file),
        '$ {}'.format(option2_command)
    ])
