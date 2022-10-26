import os
import jwt

# Hardcoded MQTT ConnackResponses as Bytecode
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
            print('No Env-Var set for ' + key + ', using default Value ' + str(default))
            return default


def verify_jwt(token, pub_key=None):
    # Check if JWT is valid by verifying its signature with Keycloaks PubKey
    payload = None
    if pub_key is not None:
        payload = jwt.decode(token, pub_key, algorithms=["RS256"])
    else:
        # if no pubKey is provided, skip verifying the signature
        payload = jwt.decode(token, None, algorithms='none')
    return payload
