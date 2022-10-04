import requests
import paho.mqtt.client as mqtt

jwt = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJqSkNFS0hrVkpBR09DSExyRXAzOEJwM294YUpwZkxBQ3FvWlN6LXpRLTdzIn0.eyJleHAiOjE2NjYyODIzODQsImlhdCI6MTY2NDg4NjgzMSwiYXV0aF90aW1lIjoxNjY0ODg2ODE5LCJqdGkiOiJmYWJiNmYzZS1kNTMzLTRkZjYtYmIxOS0wOGFkOWE2M2I2YzYiLCJpc3MiOiJodHRwczovL2F1dGguY3NwLXN0YWdpbmcuZW5nLXNvZnR3YXJlbGFicy5kZS9hdXRoL3JlYWxtcy9kZWZhdWx0Iiwic3ViIjoiYjliNmY1MWMtYWQ3MS00ZTcxLTkyNzUtNjFiY2RmOWMyM2U1IiwidHlwIjoiQmVhcmVyIiwiYXpwIjoibXF0dC13cmFwcGVyIiwic2Vzc2lvbl9zdGF0ZSI6IjY5OGFjYzg2LTg5MzgtNDI4Zi04Y2Y4LTg2YmU0YmEwZDNhMCIsImFjciI6IjEiLCJzY29wZSI6ImVtYWlsIHByb2ZpbGUiLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwibmFtZSI6IkpvbmFzIExlaXRuZXIiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJqb25hcy5sZWl0bmVyIiwiZ2l2ZW5fbmFtZSI6IkpvbmFzIiwiZmFtaWx5X25hbWUiOiJMZWl0bmVyIiwiZW1haWwiOiJqb25hcy5sZWl0bmVyQGVuZy1pdHMuZGUifQ.K7jnYvbtWU_Y90RtSF87BBRDvghaTSVcfBGDaz9Sns7OwzICHD5LCwIiiGFDMRKpka01Syi6GyWO0bMUqHfitRn6t4VV2pTMqZ5H2v10OrVVSyDDKy57RvstleGeb9qj4l8LwlOodMhfRF6Ie4P9LSJYpo8nUThLHv-oRxfUXkyiMlvUKaj7kdhlbKizZeuBMjkpXQOTFraygv2wwDhT7jiFPVtlXC1s6BMxfcrdxicOdc27P2UIWZRoZZE6MSQxGvyTzWcN83l_5Aqz1EsSzam49uwHx0FcJeq-uTzusnPZY9MXU6p_mS2UMZejIc5JuLKsaaX5e6uDmFcDB6eT-A"

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

client.connect("localhost", 8000, 60)

client.loop_forever()