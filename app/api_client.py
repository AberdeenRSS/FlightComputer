import base64
from io import BytesIO
from typing import Any, Callable, Collection, Coroutine, Union
from uuid import UUID
import jwt
import json
import httpx
import socketio
from app.logic.rocket_definition import Rocket
from app.logic.to_vessel_and_flight import to_vessel_and_flight
from app.models.command import Command, CommandSchema
from app.models.flight_measurement_compact import FlightMeasurementCompact, FlightMeasurementCompactSchema
from app.models.vessel import Vessel, VesselSchema
from app.models.flight import Flight, FlightSchema
from kivy.logger import Logger
import time
import gzip

def zip_payload(payload: str) -> bytes:
    btsio = BytesIO()
    g = gzip.GzipFile(fileobj=btsio, mode='w')
    g.write(bytes(payload, 'utf8'))
    g.close()
    return btsio.getvalue()

LOGGER_NAME = 'ApiClient'

def format_response(response: Union[httpx.Response, None]):


    try:

        if response is None:
            return f'No response from server'

        success = response.status_code >= 200 and response.status_code < 300

        if success:
            return f'Request to {response.url} was successful (Code {response.status_code})'
        else:
            return f'Request to {response.url} failed wit code {response.status_code}: {response.text}'
    
    except:
        return 'Response could not be formatted'


class ApiClient:
    '''API client for the rss FlightManagementServer'''

    endpoint: str

    gzip = True

    def __init__(self, auth_code: str) -> None:

        self.auth_code = auth_code

        self._config = json.load(open('./config/config.json'))

        self.endpoint = self._config['API_ENDPOINT']


    old_token_decoded: Union[None, dict[str, Any]] = None
    old_token: Union[None, str] = None

    async def authenticate(self):

        # try to return a cached token if available
        if self.old_token_decoded is not None and self.old_token is not None:

            # Check that the old token does not expire in the next minute
            if time.time() < (self.old_token_decoded['exp'] - 60):
                return self.old_token

        # First, the code looks up a token from the cache.
        # Because we're looking for a token for the current app, not for a user,
        # use None for the account parameter.
        try:
            result = await self.request_with_error_handling_and_retry(lambda client: client.post('/auth/authorization_code_flow', data={'token':self.auth_code}), 3, False) # type: ignore
        except Exception as e:
            Logger.exception(f'{LOGGER_NAME}: Authentication failed: {e.args}')
            raise
    
        if result.is_error:
            Logger.exception(f'{LOGGER_NAME}: Authentication failed: {result.text}')
            raise Exception(f'{LOGGER_NAME}: Authentication failed: {result.text}')

        auth_response = result.json()
        bearer = auth_response['token']

        try:
            header = jwt.get_unverified_header(bearer)
            decoded_bearer = jwt.decode(bearer, algorithms=header['alg'], verify=False, options={'verify_signature': False})
        except Exception as e:
            Logger.exception(f'{LOGGER_NAME}: Authentication failed: Invalid bearer token: {e}')
            raise Exception(f'{LOGGER_NAME}: Authentication failed: Invalid bearer token: {e}')

        self.old_token = bearer
        self.old_token_decoded = decoded_bearer

        return bearer

    async def request_with_error_handling_and_retry(self, func: Callable[
        [httpx.AsyncClient], Coroutine[Any, Any, httpx.Response]], retries: int = 0, auth: bool = True) -> httpx.Response:

        async with httpx.AsyncClient() as client:

            client.base_url = self.endpoint
            
            if auth:
                bearer = await self.authenticate()
                client.headers.setdefault('Authorization', 'Bearer ' + bearer)

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

    async def register_vessel(self, vessel_req) -> Vessel:


        vessel_creation_res = await self.request_with_error_handling_and_retry(
            lambda client: client.post("/vessel/register", json=vessel_req),
            3
        )

        return VesselSchema().load_safe(Vessel, vessel_creation_res.json())

    async def create_new_flight(self, flight_req):

        flight_res = await self.request_with_error_handling_and_retry(
            lambda client: client.post("/flight/create", json=flight_req),
            3
        )

        return FlightSchema().load_safe(Flight, flight_res.json())
    
    async def try_report_binray_flight_data(self, flight_id, data: bytes, timeout: float) -> tuple[bool, str]:

        async with httpx.AsyncClient() as client:

            bearer = await self.authenticate()

            client.base_url = self.endpoint
            client.headers.setdefault('Authorization', 'Bearer ' + bearer)
            client.headers.setdefault('Content-Type', 'application/octet-stream')

            res = None

            try:
                res = await client.post(f"/flight_data/report_binary/{flight_id}", content=data, timeout=timeout)

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

    async def try_report_flight_data_compact(self, flight_id, data: list[FlightMeasurementCompact], timeout: float) -> \
        tuple[bool, str]:

            serialized = FlightMeasurementCompactSchema().dump_list(data)

            additional_headers = dict()

            if self.gzip:
                # content = zip_payload(json.dumps(serialized))
                content = gzip.compress(json.dumps(serialized).encode('utf-8'))

                deb  = base64.b64encode(content)

            async with httpx.AsyncClient() as client:

                bearer = await self.authenticate()

                client.base_url = self.endpoint
                client.headers.setdefault('Authorization', 'Bearer ' + bearer)
                if self.gzip:
                    client.headers.setdefault('Content-Encoding', 'gzip')
                    client.headers.setdefault('Content-Type', 'application/json')

                res = None

                try:
                    if self.gzip:
                        res = await client.post(f"/flight_data/report_compact/{flight_id}", content=content, timeout=timeout, headers=additional_headers)
                    else:
                        res = await client.post(f"/flight_data/report_compact/{flight_id}", json=serialized, timeout=timeout)

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


    async def try_report_flight_data_compact(self, flight_id, data: list[FlightMeasurementCompact], timeout: float) -> \
    tuple[bool, str]:

        serialized = FlightMeasurementCompactSchema().dump_list(data)

        additional_headers = dict()

        if self.gzip:
            # content = zip_payload(json.dumps(serialized))
            content = gzip.compress(json.dumps(serialized).encode('utf-8'))

            deb  = base64.b64encode(content)

        async with httpx.AsyncClient() as client:

            bearer = await self.authenticate()

            client.base_url = self.endpoint
            client.headers.setdefault('Authorization', 'Bearer ' + bearer)
            if self.gzip:
                client.headers.setdefault('Content-Encoding', 'gzip')
                client.headers.setdefault('Content-Type', 'application/json')

            res = None

            try:
                if self.gzip:
                    res = await client.post(f"/flight_data/report_compact/{flight_id}", content=content, timeout=timeout, headers=additional_headers)
                else:
                    res = await client.post(f"/flight_data/report_compact/{flight_id}", json=serialized, timeout=timeout)

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
            lambda client: client.post(f'/command/confirm/{flight_id}', json=commands),
            3
        )

    async def run_full_setup_handshake(self, rocket: Rocket, flight_name: str) -> Flight:
        
        await self.authenticate()

        if self.old_token_decoded is None:
            raise Exception('Auth failure')

        vessel_id = self.old_token_decoded['uid']
        rocket.id = UUID(vessel_id)

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

        self.sio = socketio.Client(logger=False)
        self.commands_buffer = list[Command]()

    async def connect(self, command_callback: Callable[[Collection[Command]], None]):
        self.init_events(command_callback)

        bearer = await self.base_client.authenticate()

        self.sio.connect(self.base_client.endpoint, auth={'token': bearer})
        

    def init_events(self, command_callback: Callable[[Collection[Command]], None]):

        @self.sio.event
        def connect():
            try:
                self.sio.call('command.subscribe_as_vessel', str(self.flight._id))
            except Exception as e:
                Logger.info(f'{LOGGER_NAME}: Failed to subscribe to command stream: {e}')

        @self.sio.event
        def connect_error(data):
            Logger.error(f"The connection failed: {data}")

        @self.sio.event
        def disconnect():
            Logger.info("Socket io lost connection")

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

    def __del__(self):
        if self.sio.connected:
            self.sio.disconnect() 
