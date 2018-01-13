from argparse import ArgumentParser

from cc_core.commons.schema_list import schemas


DESCRIPTION = 'Show list of all available jsonschemas used by faice and cc-core.'


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    _ = parser.parse_args()
    return run()


def run():
    for name, schema in schemas:
        print(name)

    return 0
