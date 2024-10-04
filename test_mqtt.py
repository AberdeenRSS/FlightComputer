import paho.mqtt.client as mqtt
import time
from paho.mqtt.enums import CallbackAPIVersion 

# Define MQTT broker address and topic
BROKER_ADDRESS = "127.0.0.1"  # Your MQTT broker's address
BROKER_PORT = 1883  # Default MQTT port
TOPIC = "test/topic"
MESSAGE = "Hello from the Python MQTT client!"

# The callback for when the client receives a CONNACK response from the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker successfully!")
        # Subscribe to a test topic once connected
        client.subscribe(TOPIC)
        print(f"Subscribed to topic: {TOPIC}")
        
        # Now we can publish after subscribing
        result = client.publish(TOPIC, MESSAGE)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Message '{MESSAGE}' published successfully!")
        else:
            print(f"Failed to publish message. Error code: {result.rc}")
    else:
        print(f"Connection failed with code {rc}")

# The callback for when a PUBLISH message is received from the broker
def on_message(client, userdata, msg):
    print(f"Received message: {msg.payload.decode()} on topic: {msg.topic}")

# Initialize the MQTT client
client = mqtt.Client(u7yj\)


# Assign the callbacks
client.on_connect = on_connect
client.on_message = on_message

# Connect to the MQTT broker
client.connect(BROKER_ADDRESS, BROKER_PORT, 60)

# Start the loop in a non-blocking way to process network traffic
client.loop_start()

# Keep the script running to receive messages
try:
    while True:
        time.sleep(1)  # Keep the script running
except KeyboardInterrupt:
    pass

# Stop the network loop and disconnect the client
client.loop_stop()
client.disconnect()
