import asyncio
import math
import time
from typing import Iterable, Sequence, Tuple, Type, Union
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from app.api_client import ApiClient
from app.logic.commands.command import Command, Command
from app.logic.measurement_sink import ApiMeasurementSinkBase, MeasurementSinkBase
from app.logic.rocket_definition import Measurements, Part, Rocket
from app.models.flight import Flight
from app.models.flight_measurement import FlightMeasurement
from typing_extensions import Self
from kivy.logger import Logger, LOG_LEVELS

from app.models.flight_measurement_compact import FlightMeasurementCompact

LOGGER_NAME = 'Measurement_Sink'

class ApiMeasurementSink(ApiMeasurementSinkBase):
     
    type = 'Measurement_Sink.Api'

    target_send_period = timedelta(seconds=1)

    send_timeout = timedelta(seconds=20)

    send_task: Union[None, asyncio.Task] = None

    last_send_success_time: Union[None, float] = None

    last_send_attempt_time: Union[None, float] = None

    last_send_success: bool = True

    last_send_duration: Union[None, float] = None

    drop_rate: float = 1

    def __init__(self, _id: UUID, name: str, parent: Union[Self, Rocket, None]):
        super().__init__(_id, name, parent)

    def update(self, commands: Iterable[Command], now: float, iteration):

        # If the last send was not completed yet do nothing
        if self.send_task is not None and not self.send_task.done():
            return
        
        # Otherwise initiate next send
        self.send_task = asyncio.create_task(self.send_last_measurements(now))

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('send_success', int),
            ('send_duration', float),
            ('drop_rate', float)
        ]

    def get_accepted_commands(self) -> Iterable[Type[Command]]:
        return []

    def collect_measurements(self, now: float, iterations) -> Sequence[Measurements]:

        if self.last_measurement is not None and self.last_send_attempt_time is not None and self.last_measurement < self.last_send_attempt_time:
            return []
        
        return [
            [1 if self.last_send_success else 0, self.last_send_duration, self.drop_rate]
        ]
    
    async def send_last_measurements(self, now: float):

        await asyncio.sleep(0.1)

        # Swap measurement buffer
        old_buffer = self.measurement_buffer
        self.measurement_buffer = list()

        if(Logger.isEnabledFor(LOG_LEVELS['debug'])):
            Logger.debug(f'{LOGGER_NAME}: Starting measurment dispatch. {len(old_buffer)} in curent buffer')

        # A drop rate of 1 means every measurement is send
        # 2 only every second, etc.
        drop_rate = 1

        # If the last send took too long adjust the drop rate as a percentage of the overshoot
        if self.last_send_duration is not None and self.last_send_duration > self.target_send_period.total_seconds():
            drop_rate = self.last_send_duration/self.target_send_period.total_seconds()


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
            # to ensure it gets send
            i = m_count
            for m in measurements:
                if ((m_count-i) % drop_rate) < 1:
                    filtered_measurements.append(m)
                i -= 1

            parts = [s[0] for s in part.get_measurement_shape()]

            flight_measurements.append(FlightMeasurementCompact(part._id, parts, filtered_measurements))

        
        # print(f'Sending measurements for {len(flight_measurements)} parts. Drop rate: {drop_rate}.')

        if(Logger.isEnabledFor(LOG_LEVELS['debug'])):
            Logger.debug(f'{LOGGER_NAME}: Prepared measurements to be send over the Api. Trying to send measurements for {len(flight_measurements)} parts. Drop Rate: {drop_rate}')

        send_start = time.time()

        (send_success, reason) = await self.api_client.try_report_flight_data_compact(self.flight._id, flight_measurements, self.send_timeout.total_seconds())

        self.drop_rate = drop_rate
        self.last_send_attempt_time = now

        send_end = time.time()

        send_duration = send_end - send_start

        # Data was not send, therefore return old send date
        if not send_success:

            Logger.warning(f'{LOGGER_NAME}: Failed sending measurements. Reason: {reason}. Took {send_duration:02}ms')

            self.last_send_success = False
            if reason == 'TIMEOUT':
                self.last_send_duration = self.send_timeout.total_seconds()
            return
        
        if(Logger.isEnabledFor(LOG_LEVELS['debug'])):
            Logger.debug(f'{LOGGER_NAME}: Successfully send  measurements. Took {send_duration:02}ms')

        self.last_send_success = True
        self.last_send_success_time = send_end
        self.last_send_duration = send_duration