import os
import sys


PACKAGES_DIR = '/cc/packages'


def mount_points(dependencies):
    result = []

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
                result.append([os.path.join(dir_path, last_part), os.path.join(PACKAGES_DIR, last_part)])
        else:
            result.append([file_path, os.path.join(PACKAGES_DIR, file_name)])

    return result
