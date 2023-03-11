
import asyncio
from datetime import datetime
from random import random
from typing import Iterable, Tuple, Union, cast
from kivy.app import App
from kivy.uix.label import Label
from plyer.facades.accelerometer import Accelerometer
from kivy.core.window import Window
from plyer import accelerometer
from app.api_client import ApiClient, RealtimeApiClient
from uuid import uuid4
from app.logic.commands.command import Command
from app.logic.execution import topological_sort
from app.logic.rocket_definition import Part
from app.rockets.make_spatula import make_spatula
from app.models.flight import Flight
from app.models.command import Command as CommandModel
from app.logic.rocket_definition import Rocket

rocket: Rocket

flight: Flight

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
    await init_flight(api_client)
    realtime_client = RealtimeApiClient(api_client, flight)
    execution_order = topological_sort(rocket.parts)

    measurement_buffers = dict[Part, list[Iterable[Union[str, bool, float, None]]]]()

    async def update():

        new_commands = realtime_client.swap_command_buffer()

        commands_by_part = dict[Part, list[Command]]()

        for c in new_commands:
            part_of_command = rocket.part_lookup.get(cast(CommandModel, c)._id)
            if part_of_command is None:
                continue
            if part_of_command not in commands_by_part:
                commands_by_part[part_of_command] = list()
            commands_by_part[part_of_command].append(Command())

        for p in execution_order:

            commands = commands_by_part.get(p)
            p.update(commands or [])

        for p in execution_order:

            if p not in measurement_buffers:
                measurement_buffers[p] = list()

            measurement_buffers[p].extend(p.collect_measurements())

        for p in execution_order:
            p.flush()


    while True:
        await update()
        # await draw()

async def init_flight(api_client: ApiClient):

    global rocket
    global flight

    rocket = make_spatula()
    flight = await api_client.run_full_setup_handshake(rocket)

