
import asyncio
from datetime import datetime
from typing import cast
from kivy.app import App
from kivy.uix.label import Label
from plyer.facades.accelerometer import Accelerometer
from kivy.core.window import Window
from plyer import accelerometer
from app.api_client import ApiClient
from uuid import uuid4

accelerometer = cast(Accelerometer, accelerometer)

class SensorFrame:

    acceleration = None

    def poll(self):
        try:
            accelerometer.enable()
            self.acceleration = accelerometer.acceleration
        except:
            pass

class RSSFlightComputer(App):

    label = None

    def build(self):

        # request_permissions([Permission.HIGH_SAMPLING_RATE_SENSORS])

        self.label = Label(text=f'Init')
        return self.label

app = RSSFlightComputer()

def init_app():
    return app, run_loop

async def run_loop():

    api_client = ApiClient()

    # flight_initialization_done, flight_initialization_running  = await asyncio.wait({asyncio.create_task(init_flight(api_client))})

    await init_flight(api_client)

    sensors = SensorFrame()

    async def update():
        sensors.poll()



        acc_data =  [{
                '_datetime': datetime.now().isoformat(),
                'measured_values': {
                    'state': 'Active',
                }
            }]

        measurements = acc_data[0]['measured_values']

        if sensors.acceleration is not None:
            measurements['acceleration-x'] = sensors.acceleration[0]
            measurements['acceleration-y'] = sensors.acceleration[1]
            measurements['acceleration-z'] = sensors.acceleration[2]


        await api_client.report_flight_data('a55fa0f0-6396-4f5b-99c7-811245239383', acc_data)

    async def draw():
        app.label.text = f'Current accelertation: {sensors.acceleration}'

    while True:
        await asyncio.sleep(0.5)
        await update()
        await draw()

async def init_flight(api_client: ApiClient):
    vessel_req = {
        "name": "Kai",
        "_id": uuid4().__str__(),
        "_version": 0,
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
            {
                "_id": "a55fa0f0-6396-4f5b-99c7-811245239383",
                "name": "Accelerometer",
                "part_type": "Sensor.Accelerometer"
            },
        ]
    } 

    measured_parts = {
        '08f95e52-d372-4827-bc3d-3e29a1ea2f9a': [{
            "name": "temperature",
            "type": "float"
        }],
        'a55fa0f0-6396-4f5b-99c7-811245239383': [
            {
                "name": "state",
                "type": "string"
            },
            {
                "name": "acceleration-x",
                "type": "float"
            },
            {
                "name": "acceleration-y",
                "type": "float"
            },
            {
                "name": "acceleration-z",
                "type": "float"
            }
        ]
    }

    await api_client.run_full_setup_handshake(vessel_req, measured_parts)

