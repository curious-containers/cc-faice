from argparse import ArgumentParser


DESCRIPTION = 'Run a CommandLineTool as described in a CWL_FILE and its corresponding JOB_FILE. This tool is similar ' \
              'to agents implemented in cc-core, but uses container technologies. Refer to the CWL ' \
              '(http://www.commonwl.org) documentation for more details.'


def attach_args(parser):
    parser.add_argument(
        'cwl_file', action='store', type=str, metavar='CWL_FILE',
        help='CWL_FILE containing a CLI description (json/yaml) as local path or http url.'
    )
    parser.add_argument(
        'job_file', action='store', type=str, metavar='JOB_FILE',
        help='JOB_FILE in the CWL job format (json/yaml) as local path or http url.'
    )
    parser.add_argument(
        '-d', '--outdir', action='store', type=str, metavar='OUTPUT_DIR',
        help='Output directory, default current directory.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    return run(**args.__dict__)


def run(cwl_file, job_file, outdir):
    print(cwl_file)
    print(job_file)
    print(outdir)
    return 0
