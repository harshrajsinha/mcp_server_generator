
import os

class ImproperlyConfigured(Exception):
    """Environment variable not configured properly."""

    pass

def get_env_value(env_variable, optional = False):
    try:
        return os.environ[env_variable]
    except KeyError:
        if optional :
            return ""
        else :
            error_msg = 'Set the {} environment variable'.format(env_variable)
            raise ImproperlyConfigured(error_msg)


AUDIT_LOGS = get_env_value('AUDIT_LOGS', optional= True)
