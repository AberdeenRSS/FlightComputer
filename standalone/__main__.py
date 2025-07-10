import asyncio
from datetime import datetime
import json
from logging import _nameToLevel, getLogger, StreamHandler
import os
import time
import sys

from flight_computer.core.api_client import ApiClient
from flight_computer.core.flight_executer import FlightExecuter
from flight_computer.core.helper.global_data_dir import set_user_data_dir
from flight_computer.core.mqtt_client import MqttClient
from standalone.make_rocket import make_rocket

async def main():

    cur_dir = os.path.dirname(os.path.realpath(__file__))

    set_user_data_dir(f'{cur_dir}/logs')
    getLogger().setLevel(_nameToLevel['INFO'])

    getLogger().addHandler(StreamHandler(sys.stdout))

    rocket = make_rocket()

    with open('./config/secret.json') as f:

        config = json.load(f)

    api_client = ApiClient(config['api_token'])

    flight = await api_client.run_full_setup_handshake(rocket, f'Flight at {datetime.now()}')

    mqtt = MqttClient(api_client, flight._id)

    await mqtt.start()

    executor = FlightExecuter(rocket, flight, api_client, mqtt)

    await executor.run_control_loop()

    mqtt.stop()

def raspberry_setup():

    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
    except Exception as e:
        getLogger().error(f'Raspberry setup not possible: {e}')


def raspberry_teardown():
    try:
        import RPi.GPIO as GPIO
        GPIO.cleanup()
    except Exception as e:
        getLogger().error(f'Raspberry setup not possible: {e}')

if __name__ == '__main__':

    raspberry_setup()
    
    with asyncio.Runner() as runner:
        runner.run(main())

    raspberry_teardown()
