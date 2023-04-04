
import asyncio
from datetime import datetime, timedelta
from random import random
from typing import Collection, Iterable, Sequence, Tuple, Union, cast
from kivy.app import App
from kivy.uix.label import Label
from plyer.facades.accelerometer import Accelerometer
from kivy.core.window import Window
from plyer import accelerometer
from app.api_client import ApiClient, RealtimeApiClient
from uuid import uuid4
from app.logic.commands.command import Command
from app.logic.execution import topological_sort
from app.logic.measurement_sink import ApiMeasurementSinkBase, MeasurementSinkBase, MeasurementsByPart
from app.logic.rocket_definition import Measurements, Part
from app.models.flight_measurement import FlightMeasurement, FlightMeasurementSchema
from app.rockets.make_spatula import make_spatula
from app.models.flight import Flight
from app.models.command import Command as CommandModel
from app.logic.rocket_definition import Rocket
from datetime import datetime
import time


MAX_SEND_DELAY = timedelta(milliseconds=2000)

# The minimum time for each frame in seconds
MAX_FRAME_TIME = 0.001

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

    # Get list of all available measurement sinks
    measurement_sinks = [p for p in rocket.parts if isinstance(p, MeasurementSinkBase)]

    for p in rocket.parts:
        if isinstance(p, ApiMeasurementSinkBase):
            p.api_client = api_client
            p.flight = flight

    def control_loop(iteration: int, last_update: float):

        now = time.time()
        now_datetime = datetime.fromtimestamp(now)

        # Make a list of all new commands sorted by part
        new_commands = realtime_client.swap_command_buffer()
        commands_by_part = dict[Part, list[Command]]()
        for c in new_commands:
            part_of_command = rocket.part_lookup.get(cast(CommandModel, c)._id)
            if part_of_command is None:
                continue
            if part_of_command not in commands_by_part:
                commands_by_part[part_of_command] = list()
            commands_by_part[part_of_command].append(Command())

        # Call update on every part
        for p in execution_order:
            commands = commands_by_part.get(p)
            # Only update if the part is due for update this iteration
            if p.last_update is None or (now - p.last_update) > p.min_update_period.total_seconds():
                try:
                    p.update(commands or [], now)
                    p.last_update = now
                except:
                    print(f'Iteration {iteration}: Part {p.name} failed to update')

        # Gather all measurements of all parts
        current_measurements = MeasurementsByPart()
        for p in execution_order:
            # Only get measurements if the part is due for update this iteration
            if p.last_measurement is None or (now - p.last_measurement) > p.min_measurement_period.total_seconds():
                try:
                    current_measurements[p] = (p.last_measurement or now, now, p.collect_measurements(now))
                    p.last_measurement = now
                except:
                    print(f'Iteration {iteration}: Part {p.name} failed to take measurements')

        # Flush all parts (free memory)
        for p in execution_order:
            try:
                p.flush()
            except:
                print(f'Iteration {iteration}: Part {p.name} failed to flush')

        if len(current_measurements) < 1:
            return now

        for sink in measurement_sinks:
            sink.measurement_buffer.append(current_measurements)

        return now

    async def run_control_loop():
            # Run the update loop
        flight_loop_iteration = 0
        last_update = time.time()
        while True:
            update_end_time = control_loop(flight_loop_iteration, last_update)
            flight_loop_iteration += 1
            time_passed = update_end_time - last_update
            last_update = update_end_time

            wait_time = MAX_FRAME_TIME - time_passed
            if wait_time < 0:
               continue
        
            cast(Label, app.label).text = f'Frame Time: {str((time_passed if time_passed > MAX_FRAME_TIME else MAX_FRAME_TIME)*1000)}ms'
            await asyncio.sleep(wait_time)
            # await draw()

    control_loop_task = asyncio.create_task(run_control_loop())
    await control_loop_task


async def init_flight(api_client: ApiClient):

    global rocket
    global flight

    rocket = make_spatula()
    flight = await api_client.run_full_setup_handshake(rocket)

