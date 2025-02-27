import asyncio
import base64
import json
from logging import getLogger
from uuid import UUID
import paho.mqtt.client as mqtt
import time
from paho.mqtt.enums import CallbackAPIVersion

from flight_computer.core.api_client import ApiClient 

# Define MQTT broker address and topic
BROKER_ADDRESS = "127.0.0.1"  # Your MQTT broker's address
BROKER_PORT = 1883  # Default MQTT port
TOPIC = "test/topic"
MESSAGE = "Hello from the Python MQTT client!"


class MqttClient:

    client: mqtt.Client

    def __init__(self, api: ApiClient, flight_id: UUID):

        self.api = api

        self._config = json.load(open('./config/config.json'))

        self.endpoint = self._config['MQQT_ENDPOINT'] or BROKER_ADDRESS
        self.port = self._config['MQTT_PORT'] or BROKER_PORT

        self.logger = getLogger('Mqtt Client')

        self.flight_id = flight_id

    # The callback for when the client receives a CONNACK response from the broker
    def make_on_connect(self):

        def connect(client, userdata, flags, rc):
            if rc == 0:
                self.logger.info("Connected to broker successfully!")
            else:
                self.logger.info(f"Connection failed with code {rc}")

        return connect
    
    def make_on_pre_connect(self):

        flight = str(self.flight_id)

        def on_pre_connect(client, userdata, *kwargs):

            # Reset password
            bearer = asyncio.run(self.api.get_flight_bearer(flight))
            client.username_pw_set("doesnotmatter",  bearer)

        return on_pre_connect
    
    def make_on_event(self, event: str):

        def on_event(client, userdata, *kwargs):

            self.logger.info(f'Mqtt event: {event}')

        return on_event
    
    def make_on_disconnect(self):

        def on_disconnect(client, userdata, reason_code):

            self.logger.info(f'disconnect. Reason {reason_code}')

        return on_disconnect


    # The callback for when a PUBLISH message is received from the broker
    def make_on_message(self):

        def on_message(client, userdata, msg):
            
            self.logger.info(f"Received message: {msg.payload.decode()} on topic: {msg.topic}")

        return on_message

    async def start(self):

        # bearer = await self.api.get_flight_bearer(str(self.flight_id))

        self.logger(f'Starting mqtt on {self.endpoint} on port {self.port}')

        # Initialize the MQTT client
        client = mqtt.Client()
        self.client = client

        # client.username_pw_set("doesnotmatter",  bearer)

        # Assign the callbacks
        client.on_connect = self.make_on_connect()
        client.on_message = self.make_on_message()
        client.on_pre_connect = self.make_on_pre_connect()
        client.on_connect_fail = self.make_on_event('connect-failed')
        # client.on_pre_connect = self.make_on_event('pre-connect')
        client.on_disconnect = self.make_on_disconnect()

        # Connect to the MQTT broker
        client.connect_async(self.endpoint, self.port, 60)

        # Start the loop in a non-blocking way to process network traffic
        err = client.loop_start()

        self.logger.info(f'started mqtt client')

    def stop(self):

        self.client.loop_stop()
        self.client.diconnect()

