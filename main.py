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
    client.subscribe(os.getenv('BROKER_RFID_STATUS'))


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        solenoid_pin = int(os.getenv("SOLENOID_PIN"))
       
        if "fingerprint" in data:
            if bool(data["fingerprint"]):
                GPIO.output(solenoid_pin, GPIO.HIGH)
            elif not bool(data["fingerprint"]):
                GPIO.output(solenoid_pin, GPIO.LOW)
            

        if 	bool(GPIO.input(solenoid_pin)) :
            GPIO.output(solenoid_pin, GPIO.LOW)
        elif not bool(GPIO.input(solenoid_pin)):
            GPIO.output(solenoid_pin, GPIO.HIGH)

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}. Payload was: {msg.payload}")
    except KeyError as e:
        print(f"Missing expected key in message: {e}. Payload was: {msg.payload}")
    except Exception as e:
        print(f"Unexpected error handling message: {e}. Payload was: {msg.payload}")


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

# --- Callback when RFID is detected ---
def on_rfid_detected(tag_id):
    payload = {
        "tag": tag_id,
        "createdAt": time.time(),
        "locationKey": os.getenv('LOCATION_KEY'),
        "rfidStatus": GPIO.input(int(os.getenv("SOLENOID_PIN"))) 
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
            print(f"tag id: {tag_id}")
            time.sleep(1.5)  # Optional debounce/delay
        except Exception as e:
            print(f"Error reading RFID: {e}")
            time.sleep(1.5)


if __name__ == "__main__":
    load_dotenv()

    GPIO.setmode(GPIO.BCM)
    solenoid_pin = int(os.getenv("SOLENOID_PIN"))
    GPIO.setup(solenoid_pin, GPIO.OUT)

    # Start the RFID reader in a non-blocking thread
    threading.Thread(target=rfid_loop, daemon=True).start()

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
        GPIO.cleanup()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
