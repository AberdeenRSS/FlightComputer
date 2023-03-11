from datetime import datetime, timedelta
import random
from time import sleep
from typing import Any, Union
from uuid import UUID
import msal
import json
import httpx
import socketio
from asyncio import Future
from app.logic.rocket_definition import Rocket
from app.logic.to_vessel_and_flight import to_vessel_and_flight
from app.models.command import Command, CommandSchema
from app.models.vessel import Vessel, VesselSchema
from app.models.flight import Flight, FlightSchema
from json import dumps

class ApiClient:
    '''API client for the rss FlightManagementServer'''

    bearer_token: Future = Future()

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

    async def authenticate(self):

        # First, the code looks up a token from the cache.
        # Because we're looking for a token for the current app, not for a user,
        # use None for the account parameter.
        result = self.app.acquire_token_for_client(scopes=f'api://{self._secrets_config["client_id_api"]}/.default')

        if "access_token" not in result:
            error = result.get("error")
            error_description = result.get("error_description")
            correlation_id = result.get("correlation_id")
            print(error)
            print(error_description)
            print(correlation_id)  # You might need this when reporting a bug.
            exception = Exception(f'Error: {error} \n Description: {error_description} \n CorrelationID: {correlation_id}')
            self.bearer_token.set_exception(exception)
            raise exception

        self.bearer_token.set_result(result['access_token'])

    def get_basic_headers(self):
        return {'Authorization': 'Bearer ' + self.bearer_token.result(),
                'Accept': 'application/json',
                'Content-Type': 'application/json'}

    async def register_vessel(self, vessel_req) -> Vessel:

        async with httpx.AsyncClient() as client:
            vessel_creation_res = await client.post(f"{self.endpoint}/vessel/register", headers=self.get_basic_headers(), json=vessel_req)

            if vessel_creation_res.status_code < 200 or vessel_creation_res.status_code > 300:
                raise ConnectionError(f'Vessel could not be created {vessel_creation_res.text}')

            return VesselSchema().load_safe(Vessel, vessel_creation_res.json())
    
    async def create_new_flight(self, flight_req):
        async with httpx.AsyncClient() as client:
            flight_res = await client.post(f"{self.endpoint}/flight/create", headers=self.get_basic_headers(), json=flight_req)

            if flight_res.status_code < 200 or flight_res.status_code > 300:
                raise ConnectionError(f'Vessel could not be created {flight_res.text}')

            return FlightSchema().load_safe(Flight, flight_res.json())

    async def report_flight_data(self, flight_id, part_id, data):
        async with httpx.AsyncClient() as client:
            res = await client.post(f"{self.endpoint}/flight_data/report/{flight_id}/{part_id}", json=data, headers=self.get_basic_headers())

            if res.status_code < 200 or res.status_code > 300:
                raise ConnectionError(f'Error sending flight data: {res.text}')


    async def run_full_setup_handshake(self, rocket: Rocket) -> Flight:

        rocket.id = UUID(self._secrets_config['client_id'])

        # Wait for the auth to be finished
        await self.authenticate()

        vessel, flight = to_vessel_and_flight(rocket)

        vessel_res = await self.register_vessel(VesselSchema().dump(vessel))

        rocket.version = vessel_res._version
        rocket.id = vessel_res._id

        flight._vessel_version = vessel_res._version
        flight._vessel_id = vessel_res._id

        return await self.create_new_flight(FlightSchema().dump(flight))


class RealtimeApiClient():

    base_client: ApiClient

    sio = socketio.Client()

    __commands_buffer = list[Command]()

    def __init__(self, base_client: ApiClient, flight: Flight): 

        self.base_client = base_client
        self.headers = base_client.get_basic_headers()
        self.flight = flight

    def connect(self):
        self.init_events()
        self.sio.connect(f"{self.base_client.endpoint}", headers=self.headers, transports = ['websocket'])
        self.sio.call('commands.subscribe', self.flight._id)



    def init_events(self):

        @self.sio.event
        def connect():
            self.sio.call('commands.subscribe', self.flight._id)

        @self.sio.event
        def connect_error(data):
            print(f"The connection failed: {data}")

        @self.sio.event
        def disconnect():
            print("Socket io lost connection")
            
        @self.sio.on('command.new')
        def command_new(data: Any):
            try:
                self.__commands_buffer.extend(CommandSchema().load_list_safe(Command, data['commands']))
            except:
                print(f'Failed parsing command')

        @self.sio.on('*')
        def catch_all(event, data):
            print(f'received unknown event {event}')

    def swap_command_buffer(self) -> list[Command]:

        old = self.__commands_buffer
        self.__commands_buffer = list[Command]()
        return old


        