import time

import paho.mqtt.client as mqtt
import requests
import json

# TODO dynamically set protocol
URL = 'localhost'
PORT = 8000
ENDPOINT = URL + ':' + str(PORT)
TOKEN_FILE = 'token.json'

jwt = None
device_code = None

# TODO remove debug
connect_timestamp = time.time()


def get_jwt(endpoint):
    global jwt, device_code

    jwt = read_token()
    if jwt is not None:
        return

    print('Calling MQTT-Wrapper to receive a Device Code & trigger Auth process...')
    device_code_res = requests.get('http://' + endpoint + '/auth/device').json()
    device_code = device_code_res['device_code']
    print('Device Code received & saved in Memory: ' + device_code)

    print("Requesting JWT from MQTT-Wrapper...")
    status_code = 400
    token_res = None
    while status_code != 200:
        payload = {'device_code': device_code}
        token_res = requests.request(
            "POST",
            'http://' + endpoint + '/auth/token',
            json=payload
        )
        status_code = token_res.status_code

        if status_code != 200:
            print("Device not yet authorized, retrying...")
            # TODO set to 600 for Production
            time.sleep(30)

    print('JWT received')
    print(token_res.json())
    jwt = token_res.json()['access_token']

    save_token(token_res.json())


def save_token(token):
    with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(token, f, ensure_ascii=False, indent=4)


def read_token():
    try:
        with open(TOKEN_FILE) as infile:
            token = json.load(infile)['access_token']
        return token
    except FileNotFoundError:
        return None


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global connect_timestamp
    print(str(int(time.time())) + ": Connected with result code " + str(rc))
    connect_timestamp = time.time()

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # client.subscribe("$SYS/#")


def on_disconnect(client, userdata, rc):
    global connect_timestamp
    connection_duration = int(time.time() - connect_timestamp)
    print(str(time.time()) + ": Disconnected after " + str(connection_duration) + " seconds with result code " + str(rc))

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))


def on_connect_fail(client, userdata):
    print("failed")


if jwt is None:
    get_jwt(ENDPOINT)

client = mqtt.Client(transport="websockets")
client.enable_logger()
client.ws_set_options(path="/mqtt", headers={'Cookie': jwt})
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.on_connect_fail = on_connect_fail
client.on_log = print

client.connect(URL, PORT, 10)

client.loop_forever()
