
import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+ str(rc))
    client.subscribe("hello/#")

def on_message(client,userdata,msg):
    print(msg.topic + " " + str(msg.payload.decode()))
        
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print('Connecting')

client.connect('localhost',1883,60)
client.loop_forever()
