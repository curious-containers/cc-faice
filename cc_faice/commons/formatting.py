import sys
import textwrap


def wrapped_print(blocks, error=False):
    if error:
        for block in blocks:
            print(textwrap.fill(block), file=sys.stderr)
    else:
        for block in blocks:
            print(textwrap.fill(block))
