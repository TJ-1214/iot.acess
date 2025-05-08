
import threading
import time
import paho.mqtt.client as mqtt
from paho.mqtt.enums import MQTTProtocolVersion
from mfrc522 import SimpleMFRC522
from dotenv import load_dotenv
import os
import json

#import here all the dependencies of rpie such as GPIO, and etc..





def on_connect(client, userdata, flags, rc, properties):
    client.subscribe(os.getenv('BROKER_RFID_STATUS'))

def on_message(client, userdata, msg):
   ''' data = json.loads(msg)

    if data['status'] : 

        #this function for receiving msg
        #insert the workflow of opening the door lock if success
    
    
    '''
    pass
  




# --- Callback when RFID is detected ---
def on_rfid_detected(tag_id):
    payload = {
        "tag": tag_id,
        "createdAt": time.time()
    }
    mqtt_client.publish(os.getenv('BROKER_RFID_TOPIC'), json.dumps(payload))

# --- RFID scanning loop in its own thread ---
def rfid_loop():
    reader = SimpleMFRC522()
    print("RFID reader initialized")

    while True:
        try:
            print("Waiting for tag...")
            tag_id = reader.read_id()
            on_rfid_detected(tag_id)
            time.sleep(1)  # Optional debounce/delay
        except Exception as e:
            print(f"Error reading RFID: {e}")
            time.sleep(1)


if __main__ == "__main__":

    load_dotenv()


    # Start the RFID reader in a non-blocking thread
    threading.Thread(target=rfid_loop, daemon=True).start()

    mqtt_client = mqtt.Client(protocol=MQTTProtocolVersion.MQTTv5)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(os.getenv('BROKER_ADDRESS'))
    mqtt_client.loop_start()  # Start network loop in the background


    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()