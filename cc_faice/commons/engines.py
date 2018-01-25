import jsonschema
from cc_core.commons.exceptions import EngineError
from cc_core.commons.schemas.engines.container import container_engines
from cc_core.commons.schemas.engines.execution import execution_engines
from cc_core.commons.schemas.engines.virtualization import virtualization_engines


ENGINES = {
    'container': container_engines,
    'execution': execution_engines,
    'virtualization': virtualization_engines
}


def engine_validation(red_data, engine_type, supported, mode):
    if engine_type not in ENGINES:
        raise EngineError('invlid engine type "{}"'.format(engine_type))

    if engine_type not in red_data:
        raise EngineError('engine type "{}" required in RED_FILE for "{}"'.format(engine_type, mode))

    engine = red_data[engine_type]['engine']
    settings = red_data[engine_type]['settings']

    if engine not in supported:
        raise EngineError('{}-engine "{}" not supported by "{}"'.format(engine_type, engine, mode))

    if engine not in ENGINES[engine_type]:
        raise EngineError('no schema available for {}-engine "{}" in cc_core '.format(engine_type, engine))

    schema = ENGINES[engine_type][engine]
    try:
        jsonschema.validate(settings, schema)
    except:
        raise EngineError('{}-engine "{}" does not comply with jsonschema'.format(engine_type, engine))
