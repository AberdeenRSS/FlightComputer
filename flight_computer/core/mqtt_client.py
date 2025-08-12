import asyncio
import base64
import json
from logging import getLogger
import socket
from threading import Thread
from typing import Callable
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

    client: mqtt.Client | None = None

    _thread: Thread | None = None

    thread_abort: bool = False

    initial_reconnect_timeout = 1

    max_reconnect_timeout = 10

    def __init__(self, api: ApiClient, flight_id: UUID):

        self.api = api

        self._config = json.load(open('./config/config.json'))

        self.endpoint =  self._config['MQQT_ENDPOINT'] if 'MQQT_ENDPOINT' in self._config else BROKER_ADDRESS
        self.port = self._config['MQTT_PORT'] if 'MQTT_PORT' in self._config else BROKER_PORT

        self.logger = getLogger('Mqtt Client')

        self.flight_id = flight_id

        self.connected = False

        self.connect_listeners = set()
        self.message_listeners = set()

        self._cur_reconnect_timeout = self.initial_reconnect_timeout

    def add_on_connect_listener(self, listener: Callable[[mqtt.Client], None], call_immediately: bool = False):

        self.connect_listeners.add(listener)
        if call_immediately and self.client is not None and self.connected:
            listener(self.client)

    def add_message_listener(self, listener: Callable[[mqtt.MQTTMessage], None]):
        self.message_listeners.add(listener)


    # The callback for when the client receives a CONNACK response from the broker
    def make_on_connect(self):

        def connect(client, userdata, flags, rc):
            if rc == 0:
                self._cur_reconnect_timeout = self.initial_reconnect_timeout
                self.logger.info("Connected to broker successfully!")
                self.connected = True
                for l in self.connect_listeners:
                    l(client)
            else:
                self.logger.info(f"Connection failed with code {rc}")

        return connect
    
    def make_on_pre_connect(self):

        flight = str(self.flight_id)

        def on_pre_connect(client, userdata, *kwargs):

            # Reset password
            # bearer = asyncio.run(self.api.get_flight_bearer(flight))
            client.username_pw_set("doesnotmatter",  'bearer')

        return on_pre_connect
    
    def make_on_event(self, event: str):

        def on_event(client, userdata, *kwargs):

            self.logger.info(f'Mqtt event: {event}')

        return on_event
    
    def make_on_disconnect(self):

        def on_disconnect(client: mqtt.Client, userdata, reason_code):

            # if reason_code == mqtt.MQTT_ERR_PROTOCOL:
            #     self.logger.warning('Client disconnected, due to protocol error, trying reconnect')
            #     try:
            #         client.reconnect()
            #     except Exception as e:
            #         self.logger.error(f'Reconnect failed: {e}')
            #     return
            
            self.logger.info(f'Client disconnected, reason: {reason_code}')

        return on_disconnect


    # The callback for when a PUBLISH message is received from the broker
    def make_on_message(self):

        def on_message(client, userdata, msg):
            
            for l in self.message_listeners:
                l(msg)

            # self.logger.info(f"Received message: {msg.payload.decode()} on topic: {msg.topic}")

        return on_message
    
    def make_on_log(self):

        def on_log(client, userdata, level, msg):
            self.logger.log(level, msg)

        return on_log
    

    def _thread_main(self) -> None:

        try:

            self.logger.info(f'Starting mqtt on {self.endpoint} on port {self.port}')

            while not self.thread_abort:

                # Initialize the MQTT client
                client = mqtt.Client(reconnect_on_failure=False, protocol=mqtt.MQTTv31)
                self.client = client

                # client.username_pw_set("doesnotmatter",  bearer)
                client.max_queued_messages = 10
                client.reconnect_delay_set(1, 10)

                # Assign the callbacks
                client.on_connect = self.make_on_connect()
                client.on_message = self.make_on_message() 
                client.on_pre_connect = self.make_on_pre_connect()
                client.on_connect_fail = self.make_on_event('connect-failed')
                # client.on_pre_connect = self.make_on_event('pre-connect')
                client.on_disconnect = self.make_on_disconnect()
                client.on_log = self.make_on_log()

                # Connect to the MQTT broker
                client.connect_async(self.endpoint, int(self.port), 10)

                self.logger.info(f'started mqtt client')

                while not self.thread_abort and not client._thread_terminate:

                    reconnect = False
                    try:
                        err = client.loop_forever()

                        # if err == mqtt.MQTT_ERR_PROTOCOL:
                        #     self.logger.warning('Client disconnected, due to protocol error, trying reconnect')
                        #     reconnect = True

                        if reconnect:
                            self.wait_and_update_reconnect_timeout()
                            client.reconnect()
                            continue
                    
                    # Gracefully handle name reasuliton errors, these can happen if the network changes (e.g. between wifi and lte)
                    except socket.gaierror as e:
                        self.logger.error(f'Client disconnected due to name resolution error, trying reconnect in {self._cur_reconnect_timeout}s')
                    except TimeoutError as e:
                        self.logger.error(f'Client disconnected due to timeout, trying reconnect in {self._cur_reconnect_timeout}s')

                    break

                self.wait_and_update_reconnect_timeout()

        finally:
            self._thread = None

    def wait_and_update_reconnect_timeout(self):

        wait_time = 0

        while not self.thread_abort and wait_time < self._cur_reconnect_timeout:
            time.sleep(0.1)
            wait_time += 0.1

        self._cur_reconnect_timeout = self._cur_reconnect_timeout*2
        if self._cur_reconnect_timeout > self.max_reconnect_timeout:
            self._cur_reconnect_timeout = self.max_reconnect_timeout

    def start(self):

        if self._thread is not None:
            raise Exception('Client already running, call stop first')
        
        self.thread_abort = False
        self._thread = Thread(target=self._thread_main, name='FlightComputer_Mqtt')
        self._thread.daemon = True
        self._thread.start()


    def stop(self):

        if self._thread is None:
            return
        
        self.thread_abort = True
        
        if self.client is None:
            return
        
        self.client._thread_terminate = True
