import paho.mqtt.client as mqtt
from random import randrange, uniform
import time

#mqttBroker = "192.168.0.26"
mqttBroker = "dedcluster.frankfurt-main.tdg.mobiledgex.net"

#username = "leo"
#password = "testoste"

client = mqtt.Client("Temperature-Test")
#client.username_pw_set(username,password)
client.connect(mqttBroker,31883)

if (client.is_connected()):
    print("connection established ...")
else:
    print("no connection: %s", client.is_connected())


while True:
    randNumber = uniform(20.0, 21.0)
    result = client.publish("TEMPERATURE", randNumber)
    print("result: %s", result) 
    print("just published " + str(randNumber) + " to topic TEMPERATURE")
    time.sleep(1)

