from copy import deepcopy


def dump_agent_cwl(red_data, stdout_file):
    outputs = deepcopy(red_data['cli']['outputs'])
    outputs['standard-out'] = {
        'type': 'stdout'
    }

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
            'return_zero': {
                'type': 'boolean?',
                'inputBinding': {
                    'prefix': '--return-zero',
                }
            }
        },
        'outputs': outputs,
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
