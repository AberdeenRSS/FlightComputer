import asyncio
from io import TextIOWrapper
import json
import math
import time
from typing import Iterable, Sequence, Tuple, Type, Union
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from app.helper.global_data_dir import get_user_data_dir
from app.logic.commands.command import Command, Command
from app.logic.measurement_sink import MeasurementSinkBase
from app.logic.rocket_definition import Measurements, Part, Rocket
from app.models.flight import Flight
from app.models.flight_measurement import FlightMeasurement
from typing_extensions import Self
from kivy.logger import Logger, LOG_LEVELS
from kivy.app import App

import os
from pathlib import Path

from app.models.flight_measurement_compact import FlightMeasurementCompact, FlightMeasurementCompactSchema

LOGGER_NAME = 'Measurement_Sink'

class FileMeasurementSink(MeasurementSinkBase):
     
    type = 'Measurement_Sink.File'

    target_store_period = timedelta(seconds=0.3)

    store_timeout = timedelta(seconds=1)

    store_task: Union[None, asyncio.Task] = None

    last_store_success_time: Union[None, float] = None

    last_store_attempt_time: Union[None, float] = None

    last_store_success: bool = True

    last_store_duration: Union[None, float] = None

    drop_rate: float = 1

    folder_created = False

    current_file_count = 0

    current_file_iteration = 0

    current_file_handle: Union[None, TextIOWrapper] = None

    def __init__(self, _id: UUID, name: str, parent: Union[Self, Rocket, None]):
        super().__init__(_id, name, parent)

        date_file_safe = datetime.now().isoformat().replace('-', '_').replace(':', '_').replace('.', '_')

        self.flight_data_folder = Path(f'{get_user_data_dir()}/flight_at_{date_file_safe}')

    def update(self, commands: Iterable[Command], now: float, iteration):

        # If the last store was not completed yet do nothing
        if self.store_task is not None and not self.store_task.done():
            return
        
        # Otherwise initiate next store
        self.store_task = asyncio.create_task(self.store_last_measurements(now))

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('store_success', int),
            ('store_duration', float),
            ('drop_rate', float)
        ]

    def get_accepted_commands(self) -> Iterable[Type[Command]]:
        return []

    def collect_measurements(self, now: float, iterations) -> Sequence[Measurements]:

        if self.last_measurement is not None and self.last_store_attempt_time is not None and self.last_measurement < self.last_store_attempt_time:
            return []
        
        return [
            [1 if self.last_store_success else 0, self.last_store_duration, self.drop_rate]
        ]
    
    async def store_last_measurements(self, now: float):

        await asyncio.sleep(0.1)

        if not self.folder_created:
            try:

                self.flight_data_folder.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f'Failed instantiating measurement folder {e}')
            self.folder_created = True

        self.open_new_file_if_required()

        if self.current_file_handle is None:
            return

        # Swap measurement buffer
        old_buffer = self.measurement_buffer
        self.measurement_buffer = list()

        if(Logger.isEnabledFor(LOG_LEVELS['debug'])):
            Logger.debug(f'{LOGGER_NAME}: Starting measurment dispatch. {len(old_buffer)} in curent buffer')

        # A drop rate of 1 means every measurement is store
        # 2 only every second, etc.
        drop_rate = 1

        # If the last store took too long adjust the drop rate as a percentage of the overshoot
        if self.last_store_duration is not None and self.last_store_duration > self.target_store_period.total_seconds():
            drop_rate = self.last_store_duration/self.target_store_period.total_seconds()


        combined_measurement_dict = dict[Part, list[Tuple[float, list[Union[float, int, str]]]]]()

        for measurement_dicts in old_buffer:


            for part, (start, end, measurements) in measurement_dicts.items():

                m_count = len(measurements)
                i = 0
                time_increment = end-start
                for m in measurements:

                    # try:
                    #     inflated = part.inflate_measurement(m)
                    # except:
                    #     print(f'Failed inflating measurement for part {part.name}')
                    #     continue

                    measurement_timestamp = start + (time_increment*i)
                    # as_date = datetime.fromtimestamp(measurement_timestamp, tz=timezone.utc)
                    if part not in combined_measurement_dict:
                        combined_measurement_dict[part] = list()
                    combined_measurement_dict[part].append((measurement_timestamp, m))
                    i += 1

        flight_measurements = list[FlightMeasurementCompact]()

        for part, measurements in combined_measurement_dict.items():
            m_count = len(measurements)
            filtered_measurements = list[Tuple[float, list[Union[float, int, str]]]]()
            # Drop the measurement if overwhelmed
            # Start with the last measurement as index 0
            # to ensure it gets store
            i = m_count
            for m in measurements:
                if ((m_count-i) % drop_rate) < 1:
                    filtered_measurements.append(m)
                i -= 1

            parts = [s[0] for s in part.get_measurement_shape()]

            flight_measurements.append(FlightMeasurementCompact(part._id, parts, filtered_measurements))

        
        # print(f'storeing measurements for {len(flight_measurements)} parts. Drop rate: {drop_rate}.')

        if(Logger.isEnabledFor(LOG_LEVELS['debug'])):
            Logger.debug(f'{LOGGER_NAME}: Prepared measurements to be store over the Api. Trying to store measurements for {len(flight_measurements)} parts. Drop Rate: {drop_rate}')

        store_start = time.time()

        store_success = False

        serialized = FlightMeasurementCompactSchema().dump_list(flight_measurements)

        try:
            self.current_file_handle.write(json.dumps(serialized))
            store_success = True
        except Exception as e:
            print(f'Failed writing measurements to file: {e}')
            self.current_file_handle = None # Reset file


        self.drop_rate = drop_rate
        self.last_store_attempt_time = now

        store_end = time.time()

        store_duration = store_end - store_start

        # Data was not store, therefore return old store date
        if not store_success:

            Logger.warning(f'{LOGGER_NAME}: Failed storeing measurements. Took {store_duration:02}ms')

            self.last_store_success = False
            self.last_store_duration = self.store_timeout.total_seconds()
            return
        
        if(Logger.isEnabledFor(LOG_LEVELS['debug'])):
            Logger.debug(f'{LOGGER_NAME}: Successfully store  measurements. Took {store_duration:02}ms')

        self.last_store_success = True
        self.last_store_success_time = store_end
        self.last_store_duration = store_duration
    
    def open_new_file_if_required(self):

        self.current_file_iteration = self.current_file_iteration + 1

        if self.current_file_handle is not None and self.current_file_iteration < 1000:
            return
        
        if self.current_file_handle:
            try:
                self.current_file_handle.close()
            except:
                print('Error closing last file handle')
        
        self.current_file_iteration = 0
        self.current_file_count = self.current_file_count + 1


        path = Path(f'{self.flight_data_folder.as_posix()}/{self.current_file_count}.json')

        try:
            self.current_file_handle = path.open('a')
        except Exception as e:
            print(f'Failed creating measurement file: {e}')