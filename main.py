import threading
import time
import paho.mqtt.client as mqtt
from paho.mqtt.enums import MQTTProtocolVersion
from mfrc522 import SimpleMFRC522
from dotenv import load_dotenv
import os
import json
import logging
#uncomment all necessary requirements
import RPi.GPIO as GPIO
#import here all the dependencies of rpie such as GPIO, and etc..


def on_connect(client, userdata, flags, rc, properties):
    client.subscribe(os.getenv('BROKER_RFID_TOPIC_STATUS').replace('<location_key>',os.getenv('LOCATION_KEY')))


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        
       
        if "type" in data:
            if data["type"]=='RFID' and bool(data["status"]):
                GPIO.output(solenoid_pin,not bool(GPIO.input(solenoid_pin)))
            if data["type"]=="FP":
                if bool(data["response"]):
                    GPIO.output(solenoid_pin,GPIO.HIGH) #DOOR LOCKED
                elif not bool(data["response"])
                    GPIO.output(solenoid_pin,GPIO.LOW) #DOOR UNLOCKED

    except json.JSONDecodeError as e:
        logging.info(f"JSON Decode Error: {e}. Payload was: {msg.payload}")
    except KeyError as e:
        logging.info(f"Missing expected key in message: {e}. Payload was: {msg.payload}")
    except Exception as e:
        logging.info(f"Unexpected error handling message: {e}. Payload was: {msg.payload}")


def on_disconnect(client, userdata, rc, properties):
    logging.info("Disconnected from broker. Trying to reconnect...")
    while True:
        try:
            client.reconnect()
            logging.info("Reconnected successfully.")
            break
        except Exception as e:
            logging.info(f"Reconnect failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

# --- Callback when RFID is detected ---
def on_rfid_detected(tag_id):
    payload = {
        "tag": tag_id,
        "createdAt": time.time(),

    }
    mqtt_client.publish(os.getenv('BROKER_RFID_TOPIC_BASE').replace('<location_key>',os.getenv('LOCATION_KEY') ), json.dumps(payload))


# --- RFID scanning loop in its own thread ---
def rfid_loop():
    reader = SimpleMFRC522()
    logging.info("RFID reader initialized")
    while True:
        try:
            logging.info("Waiting for tag...")
            tag_id = reader.read_id()
            on_rfid_detected(tag_id)
            logging.info(f"tag id: {tag_id}")
            time.sleep(1.5)  # Optional debounce/delay
        except Exception as e:
            logging.info(f"Error reading RFID: {e}")
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
    mqtt_client.connect(os.getenv('BROKER_ADDRESS'),int(os.getenv('BROKER_PORT')))
    mqtt_client.username_pw_set(os.getenv("BROKER_USERNAME"), os.getenv("BROKER_PASSWORD"))
    mqtt_client.tls_set(ca_certs='certificate/emqxsl-ca.crt')
    mqtt_client.loop_start()  # Start network loop in the background

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Exiting...")
        GPIO.cleanup()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
