import asyncio
from datetime import datetime
import json
from logging import _nameToLevel, getLogger

from core.api_client import ApiClient, RealtimeApiClient
from core.flight_executer import FlightExecuter
from standalone.make_rocket import make_rocket


async def main():

    getLogger().setLevel(_nameToLevel['INFO'])

    rocket = make_rocket()

    with open('./config/secret.json') as f:

        config = json.load(f)

    api_client = ApiClient(config['api_token'])

    flight = await api_client.run_full_setup_handshake(rocket, f'Flight at {datetime.now()}')

    executor = FlightExecuter(rocket, flight, api_client)

    realtime_client = RealtimeApiClient(api_client, flight)
    await realtime_client.connect(executor.make_on_new_command())

    await executor.run_control_loop()


if __name__ == '__main__':
    with asyncio.Runner() as runner:
        runner.run(main())