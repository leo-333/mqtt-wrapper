import time

import requests
import paho.mqtt.client as mqtt
import requests

URL = 'http://localhost'
PORT = 8000
ENDPOINT = URL + ':' + str(PORT)

jwt = None
device_code = None


def get_jwt(endpoint):
    global jwt, device_code
    print('Calling MQTT-Wrapper to receive a Device Code & trigger Auth process...')
    device_code_res = requests.get(endpoint + '/auth/device').json()
    device_code = device_code_res['device_code']
    print('Device Code received & saved in Memory: ' + device_code)

    print("Requesting JWT from MQTT-Wrapper...")
    status_code = 400
    token_res = None
    while status_code != 200:
        payload = {'device_code': device_code}
        token_res = requests.request(
            "POST",
            endpoint + '/auth/token',
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


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # client.subscribe("$SYS/#")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))


def on_connect_fail(client, userdata):
    print("failed")


client = mqtt.Client(transport="websockets")
client.enable_logger()
client.ws_set_options(path="/mqtt", headers={'Cookie': jwt})
client.on_connect = on_connect
client.on_message = on_message
client.on_connect_fail = on_connect_fail
client.on_log = print

if jwt is None:
    get_jwt(ENDPOINT)

client.connect(URL, PORT, 60)

client.loop_forever()
