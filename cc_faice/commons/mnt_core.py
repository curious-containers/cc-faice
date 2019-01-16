import os
import sys

from cc_core.commons.mnt_core import MOD_DIR, LIB_DIR, PYMOD_DIR


def module_mount_points(dependencies):
    stdlib_path = os.path.split(os.__file__)[0]
    result = [[stdlib_path, PYMOD_DIR]]

    for module_name in dependencies:
        module = sys.modules[module_name]
        file_path = module.__file__
        dir_path, file_name = os.path.split(file_path)
        if file_name == '__init__.py':
            last_part = None
            n = len(module_name.split('.'))
            for _ in range(n):
                dir_path, last_part = os.path.split(dir_path)

            if last_part is not None:
                result.append([os.path.join(dir_path, last_part), os.path.join(MOD_DIR, last_part)])
        else:
            result.append([file_path, os.path.join(MOD_DIR, file_name)])

    return result


def interpreter_mount_points(dependencies):
    result = []

    for name, path in dependencies.items():
        result.append([path, os.path.join(LIB_DIR, name)])

    return result

