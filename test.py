import sys
import platform
import types
import threading
import time
import paho.mqtt.client as mqtt
from paho.mqtt.enums import MQTTProtocolVersion
from dotenv import load_dotenv
import os
import json

import random

load_dotenv()
# --- Inject fake hardware modules if not running on a real Raspberry Pi ---
if not platform.machine().startswith("arm"):
    try:
        import fake_rpi
        sys.modules['RPi'] = fake_rpi.RPi
        sys.modules['RPi.GPIO'] = fake_rpi.RPi.GPIO
        sys.modules['smbus'] = fake_rpi.smbus

        spidev = types.ModuleType("spidev")

        class FakeSpiDev:
            def open(self, bus, device): pass
            def close(self): pass
            def xfer2(self, data): return [0] * len(data)

        spidev.SpiDev = FakeSpiDev
        sys.modules['spidev'] = spidev

        print("Mocked RPi.GPIO, spidev, smbus for non-Pi system")
    except ImportError:
        print("fake-rpi is not installed. Run 'pip install fake-rpi'")
        sys.exit(1)

    class SimpleMFRC522:
        def read(self):
            return (1234567890, "Mock RFID Tag Content")
        def write(self, text):
            print(f"Pretend writing '{text}' to tag...")
else:
    from mfrc522 import SimpleMFRC522

import RPi.GPIO as GPIO



mqtt_client = mqtt.Client(protocol=MQTTProtocolVersion.MQTTv5)

def on_connect(client, userdata, flags, rc, properties):
    client.subscribe(os.getenv('BROKER_RFID_STATUS'))

def on_message(client, userdata, msg):
   
    print(msg.payload.decode())
    data = json.loads(msg.payload.decode())


    if bool(data["status"]) : 
         GPIO.output(solenoid, GPIO.HIGH)
         
    else:
        GPIO.output(solenoid, GPIO.LOW)
    


solenoid = 1 #mocking the wire connection 
GPIO.setmode(GPIO.BOARD)
GPIO.setup(solenoid, GPIO.OUT)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(os.getenv('BROKER_ADDRESS'), int(os.getenv("BROKER_PORT")))
mqtt_client.loop_start()  # Start network loop in the background

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
            tag_id, text = reader.read()
            on_rfid_detected(tag_id)
            time.sleep(1)  # Optional debounce/delay
        except Exception as e:
            print(f"Error reading RFID: {e}")
            time.sleep(1)

# Start the RFID reader in a non-blocking thread
threading.Thread(target=rfid_loop, daemon=True).start()

# --- Main application continues running ---
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting...")
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
