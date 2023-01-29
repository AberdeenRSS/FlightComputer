from datetime import datetime, timedelta
import random
from time import sleep
import msal
import json
import sys
import logging
import requests
import socketio

# Pass the parameters.json file as an argument to this Python script. E.g.: python your_py_file.py parameters.json
config = json.load(open('./secrets/api_secrets.json'))

# Create a preferably long-lived app instance that maintains a token cache.
app = msal.ConfidentialClientApplication(
    config["client_id"], 
    authority=config["authority"],
    client_credential=config["secret"]
    )

# The pattern to acquire a token looks like this.
result = None

# First, the code looks up a token from the cache.
# Because we're looking for a token for the current app, not for a user,
# use None for the account parameter.
result = app.acquire_token_for_client(scopes=f'api://{config["client_id_api"]}/.default')


if "access_token" not in result:
    print(result.get("error"))
    print(result.get("error_description"))
    print(result.get("correlation_id"))  # You might need this when reporting a bug.


vessel_req = {
    "name": "Kai",
    "parts": [
        {
            "_id": "08f95e52-d372-4827-bc3d-3e29a1ea2f9a",
            "name": "Engine x",
            "part_type": "Propulsion.Engine.Main"
        },
        {
            "_id": "6c482d13-64b5-47c7-b804-6186c3669d91",
            "name": "Electrical engine ignitors",
            "part_type": "Propulsion.Control.Ignition",
            "parent": "08f95e52-d372-4827-bc3d-3e29a1ea2f9a"
        },
        {
            "_id": "704f4a3f-c297-4f43-bf01-d6a3e870f1d4",
            "name": "Parachute",
            "part_type": "Aerodynamics.Breaks.Parachute"
        },
        {
            "_id": "25489204-b26f-405f-8010-2878c00350e0",
            "name": "Fin 1",
            "part_type": "Aerodynamics.ControlSurface.Fin"
        },
        {
            "_id": "da04e924-96e2-4382-b351-6741cf1b68e7",
            "name": "Fin 2",
            "part_type": "Aerodynamics.ControlSurface.Fin"
        },
        {
            "_id": "a1c77546-603b-4bc3-956a-db08802adafe",
            "name": "Fin 3",
            "part_type": "Aerodynamics.ControlSurface.Fin"
        },
    ]
} 

endpoint = "http://localhost:5000"
http_headers = {'Authorization': 'Bearer ' + result['access_token'],
                'Accept': 'application/json',
                'Content-Type': 'application/json'}


vessel_creation_res = requests.post(f"{endpoint}/vessel/register", headers=http_headers, json=vessel_req)

if vessel_creation_res.status_code < 200 and vessel_creation_res.status_code > 300:
    raise ConnectionError(f'Vessel could not be created {vessel_creation_res.text}')

vessel = vessel_creation_res.json()

flight_req = {
    "_vessel_id": vessel["_id"],
    "name": f"Flight at {datetime.now()}",
    "start": datetime.now().isoformat(),
    "measured_parts": {
        '08f95e52-d372-4827-bc3d-3e29a1ea2f9a': [{
            "name": "temperature",
            "type": "float"
        }],
        '6c482d13-64b5-47c7-b804-6186c3669d91': [{
            "name": "state",
            "type": "string"
        }]
    }
}

flight_res = requests.post(f"{endpoint}/flight/create", headers=http_headers, json=flight_req)
flight_id = flight_res.json()['_id']
# measurements = list()

# time = datetime.now()

# for i in range(1, 50):
#     time = time + timedelta(milliseconds=100)
#     measurements.append({
#         '_datetime': time.isoformat(),
#         'measured_values': {
#             'temperature': random.normalvariate(100, 10)
#         }
#     })

# requests.post(f"{endpoint}/flight_data/report/{flight_id}/08f95e52-d372-4827-bc3d-3e29a1ea2f9a", json=measurements, headers=http_headers)

# standard Python
sio = socketio.Client()


@sio.event
def connect():
    print("I'm connected!")
    sio.call('flight_data.subscribe', flight_id)

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

sio.connect(f"{endpoint}", headers=http_headers, transports = ['websocket'])

ignitorState = [{
        '_datetime': datetime.now().isoformat(),
        'measured_values': {
            'state': 'NOT_IGNITED'
        }
    }]

requests.post(f"{endpoint}/flight_data/report/{flight_id}/6c482d13-64b5-47c7-b804-6186c3669d91", json=ignitorState, headers=http_headers)


# Send measurements for 100s
for i in range(1, 1000):
    # sleep(0.1)
    time = datetime.now()
    measurements = [{
        '_datetime': time.isoformat(),
        'measured_values': {
            'temperature': random.normalvariate(100, 10)
        }
    }]

    requests.post(f"{endpoint}/flight_data/report/{flight_id}/08f95e52-d372-4827-bc3d-3e29a1ea2f9a", json=measurements, headers=http_headers)

sio.wait()