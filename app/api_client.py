from datetime import datetime, timedelta
import random
from time import sleep
from typing import Union
import msal
import json
import httpx
import socketio
from asyncio import Future

class ApiClient:
    '''API client for the rss FlightManagementServer'''

    bearer_token: Future = Future()

    endpoint: str

    vessel: Union[dict, None] = None

    flight: Union[dict, None] = None
    
    flight_id: Union[str, None] = None


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

    async def register_vessel(self, vessel_req):
        async with httpx.AsyncClient() as client:
            vessel_creation_res = await client.post(f"{self.endpoint}/vessel/register", headers=self.get_basic_headers(), json=vessel_req)

            if vessel_creation_res.status_code < 200 or vessel_creation_res.status_code > 300:
                raise ConnectionError(f'Vessel could not be created {vessel_creation_res.text}')

            self.vessel = vessel_creation_res.json()
    
    async def create_new_flight(self, flight_req):
        async with httpx.AsyncClient() as client:
            flight_res = await client.post(f"{self.endpoint}/flight/create", headers=self.get_basic_headers(), json=flight_req)

            if flight_res.status_code < 200 or flight_res.status_code > 300:
                raise ConnectionError(f'Vessel could not be created {flight_res.text}')

            self.flight = flight_res.json()
            self.flight_id = self.flight['_id']

    async def report_flight_data(self, part_id, data):
        async with httpx.AsyncClient() as client:
            res = await client.post(f"{self.endpoint}/flight_data/report/{self.flight_id}/{part_id}", json=data, headers=self.get_basic_headers())

            if res.status_code < 200 or res.status_code > 300:
                raise ConnectionError(f' Error sending flight data: {res.text}')

    
    def init_socket_io(self):
        sio = socketio.Client()

        headers = self.get_basic_headers()

        @sio.event
        def connect():
            print("I'm connected!")
            sio.call('flight_data.subscribe', self.flight_id)

        @sio.event
        def connect_error(data):
            print("The connection failed!")

        @sio.event
        def disconnect():
            print("I'm disconnected!")

        @sio.on(f'flight_data.new')
        def on_data(data):
            print('data received')
            print(data)

        @sio.on('*')
        def catch_all(event, data):
            print(f'received unknown event {event}')

        sio.connect(f"{self.endpoint}", headers=headers, transports = ['websocket'])

    async def run_full_setup_handshake(self, vessel, measured_parts):

        # Wait for the auth to be finished
        await self.authenticate()

        await self.register_vessel(vessel)


        flight_req = {
            "_vessel_id": self.vessel["_id"],
            "name": f"Flight at {datetime.now()}",
            "start": datetime.now().isoformat(),
            "measured_parts": measured_parts
        }

        await self.create_new_flight(flight_req)

        self.init_socket_io()