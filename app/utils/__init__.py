import os

# Hardcoded MQTT ConnackResponsed as Bytecode
CONNACK_ACCEPTED = b'\x20\x02\x00\x00'
CONNACK_INVALID_AUTH = b'\x20\x02\x00\x04'
CONNACK_UNAUTHORIZED = b'\x20\x02\x00\x05'


# Fetch an EnvVar or die tryin'
def env_var(key, default=None):
    try:
        return os.environ[key]
    except KeyError:
        if default is None:
            print('Env-Var ' + key + ' missing, quitting.')
            exit(1)
        else:
            return default
