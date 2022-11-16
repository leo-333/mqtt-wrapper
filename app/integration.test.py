import time

import jwt as jwt_lib
import threading

import paho.mqtt.client
import paho.mqtt.client as mqtt
import requests
import json
import utils

URL = 'localhost'
PORT = 8000
ENDPOINT = URL + ':' + str(PORT)

# Current Record: 300
# TODO: track current client connections as metric
CLIENT_CONNECTIONS = 1
CLIENT_EXECUTION_DURATION = 100
CLIENT_USE_SAME_JWT = False


def get_jwt(client_index):
    global ENDPOINT
    jwt = read_token(client_index, ENDPOINT)
    if jwt is not None:
        return jwt

    print('Calling MQTT-Wrapper to receive a Device Code & trigger Auth process...')
    device_code_res = requests.get('http://' + ENDPOINT + '/auth/device').json()
    device_code = device_code_res['device_code']
    print('Device Code received & saved in Memory: ' + device_code)

    print("Requesting JWT from MQTT-Wrapper...")
    status_code = 400
    token_res = None
    while status_code != 200:
        payload = {'device_code': device_code}
        token_res = requests.request(
            "POST",
            'http://' + ENDPOINT + '/auth/token',
            json=payload
        )
        status_code = token_res.status_code

        if status_code != 200:
            print("Device not yet authorized, retrying...")
            # TODO set to 600 for Production
            time.sleep(30)

    print('JWT received')
    print(token_res.json())

    save_token(token_res.json(), client_index)

    return token_res.json()['access_token']


def save_token(token, client_index):
    with open('token-' + str(client_index) + '.json', 'w', encoding='utf-8') as f:
        json.dump(token, f, ensure_ascii=False, indent=4)


def read_token(client_index, endpoint):
    try:
        with open('token-' + str(client_index) + '.json') as infile:
            jwt_from_file = json.load(infile)

        token = jwt_from_file['access_token']
        # Check if token is still valid
        try:
            utils.verify_jwt(token, None)
        except jwt_lib.exceptions.PyJWTError as err:
            print('JWT expired, trying to refresh it')
            return refresh_token(jwt_from_file, endpoint, client_index)

        return token
    except FileNotFoundError:
        return None


def refresh_token(jwt, endpoint, client_index):
    payload = {'refresh_token': jwt['refresh_token']}
    token_res = requests.request(
        "POST",
        'http://' + endpoint + '/auth/refresh',
        json=payload
    )
    status_code = token_res.status_code

    if status_code != 200:
        print("Refreshing Token failed")
        return None

    print('JWT received')
    print(token_res.json())

    save_token(token_res.json(), client_index)

    return token_res.json()['access_token']


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print(str(int(time.time())) + ": Connected with result code " + str(rc))
    print(client)

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    #client.subscribe("$SYS/#")


def on_disconnect(client, userdata, rc):
    print(str(time.time()) + ": Disconnected with result code " + str(rc))
    print("Trying to reconnect...")
    start_client(userdata, False)




# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))


def on_connect_fail(client, userdata):
    print("connection failed")


def start_client(client_index, root_thread):
    jwt = get_jwt(client_index)

    client = mqtt.Client(userdata=client_index, transport="websockets")
    client.enable_logger()
    client.ws_set_options(path="/mqtt", headers={'Cookie': jwt})
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.on_connect_fail = on_connect_fail
    client.on_log = print

    client.connect(URL, PORT, 10)

    client.loop_start()

    # Only wait for the first execution to finish
    # so that subsequent executions (during JWT renewals) don't make the execution any longer
    if root_thread is True:
        time.sleep(CLIENT_EXECUTION_DURATION)


# Start all Clients
client_thread_pool = []
for i in range(CLIENT_CONNECTIONS):
    # create and start client thread
    client_id = i
    if CLIENT_USE_SAME_JWT:
        client_id = 1

    client_thread = threading.Thread(target=start_client, args=(client_id, True))
    client_thread_pool.append(client_thread)
    client_thread.start()

# wait until all client threads are executed
for client_thread in client_thread_pool:
    # join client threads
    client_thread.join()

