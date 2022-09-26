import requests
import paho.mqtt.client as mqtt

jwt = 'nada'

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
client.ws_set_options(path="/mqtt")#, headers={'Cookie': jwt})
client.on_connect = on_connect
client.on_message = on_message
client.on_connect_fail = on_connect_fail
client.on_log = print

client.connect("localhost", 8000, 60)

client.loop_forever()