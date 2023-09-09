from datetime import datetime, timedelta
import random
from time import sleep
from typing import Any, Callable, Collection, Coroutine, Union
from uuid import UUID
import msal
import json
import httpx
import socketio
from asyncio import Future
from app.logic.rocket_definition import Rocket
from app.logic.to_vessel_and_flight import to_vessel_and_flight
from app.models.command import Command, CommandSchema
from app.models.flight_measurement import FlightMeasurementSchema
from app.models.flight_measurement_compact import FlightMeasurementCompact, FlightMeasurementCompactSchema
from app.models.vessel import Vessel, VesselSchema
from app.models.flight import Flight, FlightSchema
from json import dumps
from kivy.logger import Logger, LOG_LEVELS
import time

LOGGER_NAME = 'ApiClient'

def format_response(response: Union[httpx.Response, None]):

    if response is None:
        return f'No response from server'

    success = response.status_code >= 200 and response.status_code < 300

    if success:
        return f'Request to {response.url} was successful (Code {response.status_code})'
    else:
        return f'Request to {response.url} failed wit code {response.status_code}: {response.text}'


class ApiClient:
    '''API client for the rss FlightManagementServer'''

    endpoint: str

    def __init__(self) -> None:

        # Pass the parameters.json file as an argument to this Python script. E.g.: python your_py_file.py parameters.json
        self._secrets_config = json.load(open('./config/api_secrets.json'))
        self._config = json.load(open('./config/config.json'))

        self.endpoint = self._config['API_ENDPOINT']

        # Create a preferably long-lived app instance that maintains a token cache.
        self.app = msal.ConfidentialClientApplication(
            self._secrets_config["client_id"],
            authority=self._secrets_config["authority"],
            client_credential=self._secrets_config["secret"]
        )

    old_token: Union[None, dict[str, Any]] = None
    old_token_time: Union[None, float] = None

    def authenticate(self):

        # try to return a cached token if available
        if self.old_token is not None and self.old_token_time is not None:

            # Check that the old token does not expire in the next minute
            if time.time() < (self.old_token_time + self.old_token['expires_in'] - 60):
                return self.old_token['access_token']

        # First, the code looks up a token from the cache.
        # Because we're looking for a token for the current app, not for a user,
        # use None for the account parameter.
        try:
            result = self.app.acquire_token_for_client(scopes=f'api://{self._secrets_config["client_id_api"]}/.default')
        except Exception as e:

            Logger.exception(f'{LOGGER_NAME}: Failed aquirering msal token: {e.args}')

            raise
    


        if "access_token" not in result:
            error = result.get("error")
            error_description = result.get("error_description")
            correlation_id = result.get("correlation_id")
            Logger.exception(f'{LOGGER_NAME}: Msal authentication failed: {error}; {error_description}; correlation_id {correlation_id}')
            exception = Exception(
                f'Error: {error} \n Description: {error_description} \n CorrelationID: {correlation_id}')
            raise exception
        
        self.old_token = result
        self.old_token_time = time.time()

        return result['access_token']

    async def request_with_error_handling_and_retry(self, func: Callable[
        [httpx.AsyncClient], Coroutine[Any, Any, httpx.Response]], retries: int = 0):

        async with httpx.AsyncClient() as client:

            response: Union[None, httpx.Response] = None

            curRetry = 0
            while (curRetry <= retries):

                try:
                    response = await func(client)
                except Exception as e:
                    Logger.exception(f'{LOGGER_NAME}: Unexpected error while sending response')

                # If successful return
                if response is not None and response.status_code >= 200 and response.status_code < 300:
                    Logger.info(f'{LOGGER_NAME}: {format_response(response)}')
                    return response

                Logger.warning(f'{LOGGER_NAME}: {format_response(response)} (Retry {curRetry})')

                curRetry += 1

            assert response is not None
            raise ConnectionError(
                f'All retries to {response.url} failed with code {response.status_code}: {response.text}')

    def authenticate_and_get_headers(self):

        bearer_token = self.authenticate()

        return {'Authorization': 'Bearer ' + bearer_token,
                'Accept': 'application/json',
                'Content-Type': 'application/json'}

    async def register_vessel(self, vessel_req) -> Vessel:

        vessel_creation_res = await self.request_with_error_handling_and_retry(
            lambda client: client.post(f"{self.endpoint}/vessel/register", headers=self.authenticate_and_get_headers(),
                                       json=vessel_req),
            3
        )

        return VesselSchema().load_safe(Vessel, vessel_creation_res.json())

    async def create_new_flight(self, flight_req):

        flight_res = await self.request_with_error_handling_and_retry(
            lambda client: client.post(f"{self.endpoint}/flight/create", headers=self.authenticate_and_get_headers(),
                                       json=flight_req),
            3
        )

        return FlightSchema().load_safe(Flight, flight_res.json())

    async def try_report_flight_data_compact(self, flight_id, data: list[FlightMeasurementCompact], timeout: float) -> \
    tuple[bool, str]:

        serialized = FlightMeasurementCompactSchema().dump_list(data)

        async with httpx.AsyncClient() as client:

            res = None

            try:
                res = await client.post(f"{self.endpoint}/flight_data/report_compact/{flight_id}", json=serialized,
                                        headers=self.authenticate_and_get_headers(), timeout=timeout)

                success = res.status_code >= 200 and res.status_code < 300

                if not success:
                    Logger.warning(f'{LOGGER_NAME}: {format_response(res)}')

                return (success, str(res.status_code))
            except TimeoutError as e:
                Logger.warning(f'{LOGGER_NAME}: Failed sending measurements due to timeout. Response: {res}')
                return (False, 'TIMEOUT')
            except  Exception as e:  
                Logger.exception(f'{LOGGER_NAME}: Unknown error sending flight data. Exception: {e}. Response: {res}')
                return (False, str(e))

    async def try_send_command_responses(self, flight_id: str, commands):

        await self.request_with_error_handling_and_retry(
            lambda client: client.post(f'{self.endpoint}/command/confirm/{flight_id}', json=json.dumps(commands),
                                       headers=self.authenticate_and_get_headers()),
            3
        )

    async def run_full_setup_handshake(self, rocket: Rocket, flight_name: str) -> Flight:

        rocket.id = UUID(self._config['rocket_id'])

        vessel, flight = to_vessel_and_flight(rocket)

        vessel_res = await self.register_vessel(VesselSchema().dump(vessel))

        rocket.version = vessel_res._version
        rocket.id = vessel_res._id

        flight._vessel_version = vessel_res._version
        flight._vessel_id = vessel_res._id
        flight.name = flight_name

        return await self.create_new_flight(FlightSchema().dump(flight))


class RealtimeApiClient():
    base_client: ApiClient

    def __init__(self, base_client: ApiClient, flight: Flight):

        self.base_client = base_client
        self.flight = flight

        self.sio = socketio.Client(logger=True)
        self.commands_buffer = list[Command]()

    def connect(self, command_callback: Callable[[Collection[Command]], None]):
        self.init_events(command_callback)

        token = self.base_client.authenticate()

        self.sio.connect(f"{self.base_client.endpoint}", auth={'token': token})

    def init_events(self, command_callback: Callable[[Collection[Command]], None]):

        @self.sio.event
        def connect():
            try:
                self.sio.call('command.subscribe', str(self.flight._id))
            except Exception as e:
                Logger.info(f'{LOGGER_NAME}: Failed to subscribe to command stream: {e}')

        @self.sio.event
        def connect_error(data):
            print(f"The connection failed: {data}")

        @self.sio.event
        def disconnect():
            print("Socket io lost connection")

        @self.sio.on('command.new')
        def command_new(data: Any):
            try:
                commands = CommandSchema().load_list_safe(Command, data['commands'])
                command_callback(commands)

            except:
                Logger.info(f'{LOGGER_NAME}: Failed parsing command')

        @self.sio.on('*')
        def catch_all(event, data):
            Logger.info(f'{LOGGER_NAME}: received unknown event {event}')



