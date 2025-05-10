import threading
import time
import paho.mqtt.client as mqtt
from paho.mqtt.enums import MQTTProtocolVersion
from mfrc522 import SimpleMFRC522
from dotenv import load_dotenv
import os
import json
#uncomment all necessary requirements
import RPi.GPIO as GPIO
#import here all the dependencies of rpie such as GPIO, and etc..


def on_connect(client, userdata, flags, rc, properties):
    client.subscribe(os.getenv('BROKER_RFID_TOPIC'))


def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    payload = {
        "status": True,
    }

    if not data["tag"] is None:
        mqtt_client.publish(os.getenv('BROKER_RFID_STATUS'), json.dumps(payload))



def on_disconnect(client, userdata, rc, properties):
    print("Disconnected from broker. Trying to reconnect...")
    while True:
        try:
            client.reconnect()
            print("Reconnected successfully.")
            break
        except Exception as e:
            print(f"Reconnect failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)




if __name__ == "__main__":
    load_dotenv()



    mqtt_client = mqtt.Client(protocol=MQTTProtocolVersion.MQTTv5)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.connect(os.getenv('BROKER_ADDRESS'), int(os.getenv("BROKER_PORT")))
    mqtt_client.loop_start()  # Start network loop in the background

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

