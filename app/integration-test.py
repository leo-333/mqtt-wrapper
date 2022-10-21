import time
import jwt as jwt_lib
import threading
import paho.mqtt.client as mqtt
import requests
import json

URL = 'localhost'
PORT = 8000
ENDPOINT = URL + ':' + str(PORT)

# Current Record: 300
# TODO: track current client connections as metric
CLIENT_CONNECTIONS = 10
CLIENT_EXECUTION_DURATION = 100
CLIENT_USE_SAME_JWT = True


def get_jwt(endpoint, client_id):

    jwt = read_token(client_id)
    if jwt is not None:
        return jwt

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

    save_token(token_res.json(), client_id)

    return token_res.json()['access_token']


def save_token(token, client_id):
    with open('token-' + str(client_id) + '.json', 'w', encoding='utf-8') as f:
        json.dump(token, f, ensure_ascii=False, indent=4)


def read_token(client_id):
    try:
        with open('token-' + str(client_id) + '.json') as infile:
            jwt_from_file = json.load(infile)

        token = jwt_from_file['access_token']
        # Check if token is still valid
        #if time.time() > float(token['exp']):
         #   print('Saved Token has expired')
          #  return None

        return token
    except FileNotFoundError:
        return None


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print(str(int(time.time())) + ": Connected with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")


def on_disconnect(client, userdata, rc):
    print(str(time.time()) + ": Disconnected with result code " + str(rc))


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))


def on_connect_fail(client, userdata):
    print("connection failed")


def start_client(client_index):
    jwt = get_jwt(ENDPOINT, i)

    client = mqtt.Client(transport="websockets")
    client.enable_logger()
    client.ws_set_options(path="/mqtt", headers={'Cookie': jwt[i]})
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.on_connect_fail = on_connect_fail
    client.on_log = print

    # print("waiting for token to expire...")
    # time.sleep(60)

    client.connect(URL, PORT, 10)

    client.loop_start()

    time.sleep(CLIENT_EXECUTION_DURATION)


# Start all Clients
client_thread_pool = []
for i in range(CLIENT_CONNECTIONS):
    # create and start client thread
    client_id = i
    if CLIENT_USE_SAME_JWT:
        client_id = 1

    client_thread = threading.Thread(target=start_client, args=(client_id,))
    client_thread_pool.append(client_thread)
    client_thread.start()

# wait until thread 1 is completely executed
for client_thread in client_thread_pool:
    # join client threads
    client_thread.join()

