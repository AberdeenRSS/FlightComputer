import asyncio
from datetime import datetime
import json
from logging import _nameToLevel, getLogger
import os
import time

from flight_computer.core.api_client import ApiClient, RealtimeApiClient
from flight_computer.core.flight_executer import FlightExecuter
from flight_computer.core.helper.global_data_dir import set_user_data_dir
from flight_computer.core.mqtt_client import MqttClient
from standalone.make_rocket import make_rocket



async def main():

    cur_dir = os.path.dirname(os.path.realpath(__file__))

    set_user_data_dir(f'{cur_dir}/logs')
    getLogger().setLevel(_nameToLevel['INFO'])

    rocket = make_rocket()

    with open('./config/secret.json') as f:

        config = json.load(f)

    api_client = ApiClient(config['api_token'])

    # mqtt = MqttClient(api_client)

    # await mqtt.start()

    # # Keep the script running to receive messages
    # try:
    #     while True:
    #         time.sleep(1)  # Keep the script running
    # except KeyboardInterrupt:
    #     pass

    # mqtt.stop()


    flight = await api_client.run_full_setup_handshake(rocket, f'Flight at {datetime.now()}')

    executor = FlightExecuter(rocket, flight, api_client)

    realtime_client = RealtimeApiClient(api_client, flight)
    await realtime_client.connect(executor.make_on_new_command())

    await executor.run_control_loop()


if __name__ == '__main__':
    with asyncio.Runner() as runner:
        runner.run(main())