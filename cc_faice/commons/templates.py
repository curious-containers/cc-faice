import sys
from getpass import getpass

import keyring
from cc_core.commons.exceptions import TemplateError, ParsingError
from cc_core.commons.parsing import split_into_parts
from cc_core.commons.templates import TEMPLATE_SEPARATOR_START, TEMPLATE_SEPARATOR_END, get_dict_sub_key_string, \
    get_list_sub_key_string, get_template_keys, is_template_key, is_protected_key


def complete_red_templates(red_data, keyring_service, fail_if_interactive):
    """
    Replaces templates inside the given red data. Requests the template keys of the red data from the keyring using the
    given keyring service.
    :param red_data: The red data to complete template keys for
    :type red_data: dict[str, Any]
    :param keyring_service: The keyring service to use for requests
    :type keyring_service: str
    :param fail_if_interactive: Dont ask the user interactively for key values, but fail with an exception
    """
    template_keys = set()
    get_template_keys(red_data, template_keys)

    templates = _get_templates(template_keys, keyring_service, fail_if_interactive)
    _complete_templates(red_data, templates)


def _ask_for_template_value(template_key):
    """
    Asks the user interactively for the given key
    :param template_key: The key to ask for
    :return: The users input
    """
    if template_key.protected:
        value = getpass('{} (protected): '.format(template_key.key))
    else:
        value = input('{}: '.format(template_key.key))
    return value


def _get_templates(template_keys, keyring_service, fail_if_interactive):
    """
    Returns a dictionary containing template keys and values.
    To fill in the template keys, first the keyring service is requested for each key,
    afterwards the user is asked interactively.
    :param template_keys: A set of template keys to query the keyring or ask the user
    :type template_keys: set[TemplateKey]
    :param keyring_service: The keyring service to query
    :param fail_if_interactive: Dont ask the user interactively for key values, but fail with an exception
    :return: A dictionary containing a mapping of template keys and values
    :rtype: dict
    :raise TemplateError: If not all TemplateKeys could be resolved and fail_if_interactive is set
    """

    templates = {}
    keys_that_could_not_be_fulfilled = []

    first_interactive_key = True

    for template_key in template_keys:
        # try keyring
        template_value = keyring.get_password(keyring_service, template_key.key)
        if template_value is not None:
            templates[template_key.key] = template_value
        else:  # ask user
            if fail_if_interactive:
                keys_that_could_not_be_fulfilled.append(template_key.key)
                continue

            if first_interactive_key:
                print('Asking for template values:')
                sys.stdout.flush()
                first_interactive_key = False

            template_value = _ask_for_template_value(template_key)
            templates[template_key.key] = template_value

    if keys_that_could_not_be_fulfilled:
        raise TemplateError('Could not resolve the following template keys: "{}".'
                            .format(keys_that_could_not_be_fulfilled))

    return templates


def _resolve_template_string(template_string, templates, key_string):
    """
    Replaces the template keys inside the given template string.
    :param template_string: The string in which templates are to be replaced.
    :param templates: The templates to use
    :param key_string: The key string describing where the template string is found in the red file.
    :return: The template string with template keys resolved
    """
    try:
        parts = split_into_parts(template_string, TEMPLATE_SEPARATOR_START, TEMPLATE_SEPARATOR_END)
    except ParsingError as e:
        raise TemplateError('Could not parse template "{}" in "{}". Failed with the following message:\n{}'
                            .format(template_string, key_string, str(e)))
    result = []
    for p in parts:
        if is_template_key(p):
            resolved = templates[p[2:-2]]
            result.append(resolved)
        else:
            result.append(p)

    return ''.join(result)


def get_secret_values(red_data):
    """
    Returns a list of secret values found in the given red data.
    A secret value is a value found under a protected key
    :param red_data: A dictionary containing the red data
    :return: A list of secret values found in the given red data
    """
    secret_values = []
    _append_secret_values(red_data, secret_values)
    return secret_values


def _append_secret_values(data, secret_values, protected=False):
    """
    Appends secret values found in data to secret_values
    :param data: The data to search in for secret values
    :param secret_values: The list of secret values
    :param protected: Indicates if the given value is protected or not
    """
    if isinstance(data, dict):
        for key, value in data.items():
            sub_protected = protected or is_protected_key(key)
            _append_secret_values(value, secret_values, sub_protected)
    elif isinstance(data, list):
        for value in data:
            _append_secret_values(value, secret_values, protected)
    else:
        if protected:
            secret_values.append(data)


def normalize_keys(data):
    """
    Removes starting underscores from the keys in data
    :param data: The data in which keys with underscores should be replaced without underscore
    """
    if isinstance(data, dict):
        keys = list(data.keys())
        for key in keys:
            value = data[key]
            if key.startswith('_'):
                normalized_key = key[1:]
                data[normalized_key] = value
                del data[key]
            normalize_keys(value)
    elif isinstance(data, list):
        for value in data:
            normalize_keys(value)


def _complete_templates(data, templates, key_string=None):
    """
    Fills the given templates into the given data.
    :param data: The data to complete
    :param templates: The templates to use
    :param key_string: A string representing the keys above the current data element.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            sub_key_string = get_dict_sub_key_string(key, key_string)

            if isinstance(value, str):
                completed_template_string = _resolve_template_string(value, templates, sub_key_string)
                data[key] = completed_template_string
            else:
                _complete_templates(value, templates, sub_key_string)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            sub_key_string = get_list_sub_key_string(index, key_string)

            if isinstance(value, str):
                completed_template_string = _resolve_template_string(value, templates, sub_key_string)
                data[index] = completed_template_string
            else:
                _complete_templates(value, templates, sub_key_string)
