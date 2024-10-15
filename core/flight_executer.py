import asyncio
from logging import _nameToLevel, getLogger
import time
from typing import Callable, Collection, Iterable, cast
from datetime import datetime
from core.api_client import ApiClient, RealtimeApiClient
from core.helper.file_logger import FileLogger
from core.helper.global_data_dir import reset_flight_data_dir
from core.logic.commands.command import Command, Command
from core.logic.commands.command_helper import deserialize_command, gather_known_commands, is_completed_command, make_command_schemas
from core.logic.to_vessel_and_flight import to_vessel_and_flight
from core.models.command import Command as CommandModel, CommandSchema
from core.logic.execution import topological_sort
from core.logic.measurement_sink import ApiMeasurementSinkBase, MeasurementSinkBase, MeasurementsByPart
from core.logic.rocket_definition import Part, Rocket

from core.models.flight import Flight

LOGGER_NAME = 'FlightExecutor'



class FlightExecuter:

    known_commands: dict[str, type[Command]]
    '''
    List of commands known within the context of the flight. Used to
    initialize the actual command objects from the models send by the 
    server
    '''

    command_buffer: list[Command]

    executed_commands: list[Command]

    deleted: bool = False

    def __init__(self, rocket: Rocket, flight: Flight, api_client: ApiClient, min_computation_frame_time: float = 0.050, min_ui_frame_time: float = 0.050) -> None:
    
        self.logger = getLogger('Flight Exector')

        self.command_buffer = list()
        self.executed_commands = list()

        self.rocket = rocket
        self.flight = flight
        self.min_computation_frame_time = min_computation_frame_time
        self.min_ui_frame_time = min_ui_frame_time

        self.execution_order = topological_sort(self.rocket.parts)
        self.known_commands = gather_known_commands(self.rocket)
        self.command_schemas = make_command_schemas(self.known_commands)

        self.api_client = api_client


        self.send_command_responses_task = asyncio.get_event_loop().create_task(self.send_command_responses())

        self.last_iteration_time = 0
        self.cur_wait_time = 0

        reset_flight_data_dir()
        self.file_logger = FileLogger()

        # Get list of all available measurement sinks
        self.measurement_sinks = [p for p in self.rocket.parts if isinstance(p, MeasurementSinkBase)]

        for p in self.rocket.parts:
            if isinstance(p, ApiMeasurementSinkBase):
                self.logger.debug(f'Initialized part {p.type} as a measurement sink')
                p.api_client = self.api_client
                p.flight = self.flight

        self.logger.addHandler(self.file_logger)

    def make_on_new_command(self):
        def on_new_command(models: Collection[CommandModel]):


            for c in models:
                self.logger.info(f'{LOGGER_NAME}: Received new command of type {c._command_type} with creation time {c.create_time} (ID: {c._id}, PartID: {c._part_id})')
                c.state = 'received'

            self.command_buffer.extend([deserialize_command(self.known_commands, c) for c in models])
        return on_new_command

    def swap_command_buffer(self) -> list[Command]:

        old = self.command_buffer
        self.command_buffer = list[Command]()
        return old

    async def run_control_loop(self, update_ui_hook: Callable | None = None):

        # Run the update loop
        flight_loop_iteration = 0
        last_update: float = time.time()
        last_ui_update = 0
        while True:

            update_start_time = time.time()
            
            update_end_time = self.control_loop(flight_loop_iteration, last_update)
            
            if update_end_time > (last_ui_update + self.min_ui_frame_time):
                last_ui_update = update_end_time

                if update_ui_hook is not None:
                    update_ui_hook()

            flight_loop_iteration += 1

            time_passed = update_end_time - last_update
            last_update = update_end_time

            wait_time = self.min_computation_frame_time - time_passed
            if wait_time < 0:
               continue
        
            # cast(Label, core.label).text = f'Frame Time: {str((time_passed if time_passed > MAX_FRAME_TIME else MAX_FRAME_TIME)*1000)}ms'
            await asyncio.sleep(wait_time)

            # Try to keep the maximum frame times but to also give
            # time to other processes. 
            # If it took longer for the last iteration to run
            # increase the waiting time by a 10th as well .
            # If it was shorter decrease it by a 10th
            # if self.last_iteration_time > update_time:
            #     self.cur_wait_time += update_time/2
            # else:
            #     self.cur_wait_time -= (self.last_iteration_time-update_time)/1.5
            
            # if self.cur_wait_time > 0:
            #     await asyncio.sleep(self.cur_wait_time)


            # await draw()

    def control_loop(self, iteration: int, last_update: float):

        now = time.time()
        now_as_date = datetime.fromtimestamp(now)

        # Make a list of all new commands sorted by part
        new_commands = self.swap_command_buffer()
        commands_by_part = dict[Part, list[Command]]()
        self.add_command_by_part(new_commands, commands_by_part)

        if(self.logger.isEnabledFor(_nameToLevel['DEBUG'])):
            self.logger.debug(f'{LOGGER_NAME}: Control loop iteration {iteration}. Time {datetime.fromtimestamp(now)}. {len(new_commands)} pending')

        # Call update on every part
        for p in self.execution_order:

            commands = commands_by_part.get(p) or []

            # Only update if the part is due for update this iteration
            if (p.last_update is not None) and ((now - p.last_update) < p.min_update_period.total_seconds()):
                self.command_buffer.extend(commands) # Re-queue all commands in this case
                if p in commands_by_part:
                    del commands_by_part[p]
                continue

            try:
                generated_commands = p.update(commands, now, iteration)

                if generated_commands is not None:

                    if(self.logger.isEnabledFor(_nameToLevel['DEBUG'])):
                        self.logger.debug(f'{LOGGER_NAME}: Iteration {iteration}. Part {p.name} successfully updated. {len(generated_commands)} emitted')
                    
                    if len(generated_commands) > 0:
                        for c in generated_commands: 
                            self.logger.info(f'{LOGGER_NAME}: Part {p.name} created a new command of type {c._command_type} with creation time {c.create_time} for part {c._part_id} (ID: {c._id}, PartID: {c._part_id})')

                    for c in generated_commands:
                        c.create_time = now_as_date

                    new_commands.extend(generated_commands)
                    self.add_command_by_part(generated_commands, commands_by_part)

                elif(self.logger.isEnabledFor(_nameToLevel['DEBUG'])):
                        self.logger.debug(f'{LOGGER_NAME}: Iteration {iteration}. Part {p.name} successfully updated')

                p.last_update = now
            except Exception as e:
                # print(f'{LOGGER_NAME}: Iteration {iteration}: Part {p.name} failed to update {e}')
                self.logger.exception(f'{LOGGER_NAME}: Iteration {iteration}: Part {p.name} failed to update {e}')

        # Gather all measurements of all parts
        current_measurements = MeasurementsByPart()
        for p in self.execution_order:
            # Only get measurements if the part is due for update this iteration or if there was a command for the part
            if (p not in commands_by_part) and (p.last_measurement is not None) and ((now - p.last_measurement) < p.min_measurement_period.total_seconds()):
                continue
            try:
                measurements = p.collect_measurements(now, iteration)

                if(self.logger.isEnabledFor(_nameToLevel['DEBUG'])):
                    self.logger.debug(f'{LOGGER_NAME}: Iteration {iteration}. Part {p.name} successfully collected measurements. New measurements: {len(measurements) if measurements is not None else "None"}')
                
                if measurements is None:
                    continue

                shape =  p.get_measurement_shape()

                for m in measurements:
                    if len(m) <= len(shape):
                        continue
                    raise Exception(f'A measurement of length {len(m)} was returned, but the part only supports measurements up to length {len(shape)}. Please verify that the get_measurement_shape method matches what is returned by collect_measurements')

                current_measurements[p] = (p.last_measurement or now, now, measurements)
                p.last_measurement = now
            except Exception as e:
                self.logger.exception(f'{LOGGER_NAME}: Iteration {iteration}: Part {p.name} failed to take measurements: {e}')

        # Flush all parts (free memory)
        for p in self.execution_order:
            try:
                p.flush()
            except:
                self.logger.exception(f'{LOGGER_NAME}: Iteration {iteration}: Part {p.name} failed to flush')


        # Set all commands to be executed, except those that are currently set to be prossesing
        for commands in commands_by_part.values():
            self.executed_commands.extend([c for c in commands if is_completed_command(c)])
            self.command_buffer.extend([c for c in commands if not is_completed_command(c)])

        if len(current_measurements) < 1:
            return now

        for sink in self.measurement_sinks:
            sink.measurement_buffer.append(current_measurements)

        self.file_logger.flush()

        return now

    def add_command_by_part(self, new_commands: Collection[Command], commands_by_part: dict[Part, list[Command]]):
        for c in new_commands:

            if c._part_id is None:
                continue

            part_of_command = self.rocket.part_lookup.get(c._part_id)
            if part_of_command is None:
                continue
            if part_of_command not in commands_by_part:
                commands_by_part[part_of_command] = list()
            commands_by_part[part_of_command].append(c)
    
    async def send_command_responses(self):

        # abort = await self.init_flight_task

        # if abort:
        #     return

        while True:

            if self.deleted:
                return

            if len(self.executed_commands) < 1:
                await asyncio.sleep(0.01)
                continue

            # swap buffer
            commands_to_send = self.executed_commands
            self.executed_commands = list()

            if len(commands_to_send) < 1:
                return

            # Set all commands to failed, if they haven't been processed yet
            for c in commands_to_send:
                if c.state == 'dispatched' or c.state == 'received':
                    c.state = 'failed'
                    c.response_message = 'Part did not process the command for an uknown reason'

            self.logger.info(f'{LOGGER_NAME}: Processed {len(commands_to_send)} commands:')
            for c in commands_to_send: 
                self.logger.info(f'{LOGGER_NAME}: Processed command {c._id} of type {c._command_type} for part {c._part_id} resulting in state {c.state}')

            c_schema = CommandSchema()

            # Convert the commands into native objects (ready to be send over the api)
            models = [ (self.command_schemas.get(c.command_type) or c_schema).dump(c) for c in commands_to_send ]

            try:
                await self.api_client.try_send_command_responses(str(self.flight._id), models)
                self.logger.info(f'{LOGGER_NAME}: Successfully trasmitted {len(commands_to_send)} commands')
            except Exception as e:
                self.logger.exception(f'{LOGGER_NAME}: Failed sending {len(models)} command responses: {e}')

    def __del__(self):

        if not self.control_loop_task.done():
            self.control_loop_task.cancel()

        if not self.init_flight_task.done():
            self.init_flight_task.cancel()

        if not self.send_command_responses_task.done():
            self.send_command_responses_task.cancel()

        if self.file_logger is not None:
            self.file_logger.flush()
            self.logger.removeHandler(self.file_logger)

        self.deleted = True
