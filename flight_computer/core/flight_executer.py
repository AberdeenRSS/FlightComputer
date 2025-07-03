import asyncio
from logging import _nameToLevel, getLogger
import time
from typing import Any, Callable, Collection, Iterable, cast
from datetime import datetime
from flight_computer.core.api_client import ApiClient
from flight_computer.core.helper.binary_format_encoder import decode_payload
from flight_computer.core.helper.file_logger import FileLogger
from flight_computer.core.helper.global_data_dir import reset_flight_data_dir
from flight_computer.core.logic.commands.command import Command, Command
from flight_computer.core.logic.commands.command_helper import deserialize_command, is_completed_command, make_command_schemas
from flight_computer.core.logic.to_vessel_and_flight import to_vessel_and_flight
from flight_computer.core.models.command import Command as CommandModel, CommandSchema
from flight_computer.core.logic.execution import topological_sort
from flight_computer.core.logic.measurement_sink import ApiMeasurementSinkBase, MeasurementSinkBase, MeasurementsByPart
from flight_computer.core.logic.rocket_definition import Part, Rocket

from flight_computer.core.models.flight import Flight
from flight_computer.core.mqtt_client import MqttClient
import paho.mqtt.client as mqtt

LOGGER_NAME = 'FlightExecutor'

DEBUG_LOG_LEVEL = _nameToLevel['DEBUG']

class FlightExecuter:

    deleted: bool = False

    in_run_startup: bool = True
    '''
    Denotes if the executer is currently running the first iterations of the control loop.
    These are used to establish a max. performance baseline to then home in a suitable
    loop frequenzy that doesn't limit the ui thread
    '''

    startup_run_establish_count: int = 100
    '''
    The number of iterations the executer spends with
    benchmark startup iterations
    '''

    startup_runs_total_time: int = 0

    startup_runs_count: int = 0

    iteration_wait: int = 0

    def __init__(self, rocket: Rocket, flight: Flight, api_client: ApiClient, mqtt_client: MqttClient, min_computation_frame_time: float = 0.050, min_ui_frame_time: float = 0.050) -> None:
    
        self.logger = getLogger('Flight Exector')

        self.command_buffer = list()
        self.executed_commands = list()

        self.rocket = rocket
        self.flight = flight
        self.min_computation_frame_time = min_computation_frame_time
        self.min_ui_frame_time = min_ui_frame_time

        self.execution_order = topological_sort(self.rocket.parts)

        self.api_client = api_client
        self.mqtt_client = mqtt_client

        self.last_iteration_time = 0
        self.cur_wait_time = 0

        reset_flight_data_dir()
        
        self.file_logger = FileLogger()
        self.logger.addHandler(self.file_logger)

        self.mqtt_client.add_on_connect_listener(self.make_subscribe_commands())

        # Get list of all available measurement sinks
        self.measurement_sinks = [p for p in self.rocket.parts if isinstance(p, MeasurementSinkBase)]

        for p in self.rocket.parts:
            if isinstance(p, ApiMeasurementSinkBase):
                self.logger.debug(f'Initialized part {p.type} as a measurement sink')
                p.api_client = self.api_client
                p.mqtt_client = self.mqtt_client
                p.flight = self.flight

    def make_subscribe_commands(self):

        def subscribe_commands(client: mqtt.Client):
            client.subscribe(f'{self.flight._id}/c/#', 2)
            self.mqtt_client.add_message_listener(self.make_on_command_raw())
            

        return subscribe_commands

    async def run_control_loop(self, update_ui_hook: Callable | None = None, until: float | None = None):
        '''
        Runs the control loop with throtteling
        '''

        # Run the update loop
        flight_loop_iteration = 0
        last_update: float = time.time()
        last_ui_update = 0
        while True:

            update_start_time = time.time()

            # Stop if loop should only run for limited time
            if until is not None and update_start_time > until:
                return
            
            update_end_time = self.control_loop(flight_loop_iteration, last_update)
            
            if update_end_time > (last_ui_update + self.min_ui_frame_time):
                last_ui_update = update_end_time

                if update_ui_hook is not None:
                    update_ui_hook()

            flight_loop_iteration += 1

            time_passed = update_end_time - last_update
            last_update = update_end_time

            wait_time = self.min_computation_frame_time - time_passed

            if self.in_run_startup:
                if self.startup_runs_count < self.startup_run_establish_count:

                    self.startup_runs_total_time += time_passed
                    self.startup_runs_count += 1
                    continue

                self.in_run_startup = False

                # Use 20% of the average run time as waiting time to let other threads catch up
                self.iteration_wait = (self.startup_runs_total_time / self.startup_runs_count) * 0.8
                self.logger.info(f'{LOGGER_NAME}: Control loop startup done. Iteration wait time established at {self.iteration_wait}s')

                continue
        
            await asyncio.sleep(self.iteration_wait)

    def control_loop(self, iteration: int, last_update: float, _now: float | None = None):

        now = _now or time.time()
        # now_as_date = datetime.fromtimestamp(now)

        if(self.logger.isEnabledFor(DEBUG_LOG_LEVEL)):
            self.logger.debug(f'{LOGGER_NAME}: Control loop iteration {iteration}. Time {datetime.fromtimestamp(now)}')

        # Call update on every part
        for p in self.execution_order:

            # Only update if the part is due for update this iteration
            if p.last_update is not None and ((now - p.last_update) < p.min_update_period.total_seconds()):
                continue

            try:
                p.update(now, iteration)

                if(self.logger.isEnabledFor(DEBUG_LOG_LEVEL)):
                    self.logger.debug(f'{LOGGER_NAME}: Iteration {iteration}. Part {p.name} successfully updated')

                p.last_update = now
            except Exception as e:
                # print(f'{LOGGER_NAME}: Iteration {iteration}: Part {p.name} failed to update {e}')
                self.logger.exception(f'{LOGGER_NAME}: Iteration {iteration}: Part {p.name} failed to update {e}')

        # Gather all measurements of all parts
        current_measurements = MeasurementsByPart()
        for p in self.execution_order:
            # Only get measurements if the part is due for update this iteration or if there was a command for the part
            if  (p.last_measurement is not None) and ((now - p.last_measurement) < p.min_measurement_period.total_seconds()):
                continue
            try:
                p.collect_measurements(now, iteration)
                measurements = p._measurement_buffer
                p._measurement_buffer = list()

                if(self.logger.isEnabledFor(DEBUG_LOG_LEVEL)):
                    self.logger.debug(f'{LOGGER_NAME}: Iteration {iteration}. Part {p.name} successfully collected measurements. New measurements: {len(measurements) if measurements is not None else "None"}')
                
                if measurements is None or len(measurements) < 1:
                    continue

                current_measurements[p] = measurements
                p.last_measurement = now
            except Exception as e:
                self.logger.exception(f'{LOGGER_NAME}: Iteration {iteration}: Part {p.name} failed to take measurements: {e}')

        # Flush all parts (free memory)
        for p in self.execution_order:
            try:
                p.flush()
            except:
                self.logger.exception(f'{LOGGER_NAME}: Iteration {iteration}: Part {p.name} failed to flush')

        self.file_logger.flush()

        if len(current_measurements) < 1:
            return now

        for sink in self.measurement_sinks:
            sink.measurement_buffer.append(current_measurements)

        return now
    
    def make_on_command_raw(self):
        def on_command_raw(command: mqtt.MQTTMessage):

            split_topic = command.topic.split('/')
    
            # Either not for this rocket or not a command
            if(split_topic[0] != str(self.flight._id) or split_topic[1] != 'c'):
                return
            
            part_index = int(split_topic[2])
            command_index = int(split_topic[3])
            
            time, payload =  decode_payload(self.rocket.parts[part_index].get_accepted_commands()[command_index][1], command.payload)

            self.on_command((part_index, command_index, time, payload))

        return on_command_raw


    def on_command(self,command: tuple[int, int, float, Any]):

        try:
           
           # Get the part the command is for
           part = self.rocket.parts[command[0]]

           # Execute the command on the part
           part.get_command_callbacks()[command[1]](command[2], command[3])

        except:
            self.logger.warning(f'Failed executing command for part {command[0]}')

    def __del__(self):

        # if not self.control_loop_task.done():
        #     self.control_loop_task.cancel()

        # if not self.init_flight_task.done():
        #     self.init_flight_task.cancel()

        if self.file_logger is not None:
            self.file_logger.flush()
            self.logger.removeHandler(self.file_logger)

        self.deleted = True
