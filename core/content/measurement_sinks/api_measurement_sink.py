import asyncio
from io import BytesIO
from logging import getLogger, _nameToLevel
import math
import struct
import time
from typing import Iterable, Sequence, Tuple, Type, Union
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from core.api_client import ApiClient
from core.helper.measurement_binary_helper import get_struct_format_for_part
from core.logic.commands.command import Command, Command
from core.logic.measurement_sink import ApiMeasurementSinkBase, MeasurementSinkBase
from core.logic.rocket_definition import Measurements, Part, Rocket
from core.models.flight import Flight
from core.models.flight_measurement import FlightMeasurement
from typing_extensions import Self

from core.models.flight_measurement_compact import FlightMeasurementCompact

LOGGER_NAME = 'Measurement_Sink'

CHAR_SIZE = struct.calcsize('!B')
SHORT_SIZE = struct.calcsize('!H')

class ApiMeasurementSink(ApiMeasurementSinkBase):
     
    type = 'Measurement_Sink.Api'

    target_send_period = timedelta(seconds=0.5)

    send_timeout = timedelta(seconds=10)

    send_task: Union[None, asyncio.Task] = None

    last_send_success_time: Union[None, float] = None

    last_send_attempt_time: Union[None, float] = None

    last_send_success: bool = True

    last_send_duration: Union[None, float] = None

    drop_rate: float = 1

    def __init__(self, _id: UUID, name: str, parent: Union[Self, Rocket, None]):
        super().__init__(_id, name, parent)

        self.logger = getLogger('Api Measurement Sink')

    def update(self, commands: Iterable[Command], now: float, iteration):

        # If the last send was not completed yet do nothing
        if self.send_task is not None and not self.send_task.done():
            return
        
        # Otherwise initiate next send
        self.send_task = asyncio.create_task(self.send_last_measurements(now))

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('send_success', '?'),
            ('send_duration', 'f'),
            ('drop_rate', 'f')
        ]

    def get_accepted_commands(self) -> Iterable[Type[Command]]:
        return []

    def collect_measurements(self, now: float, iterations) -> Sequence[Measurements]:

        if self.last_measurement is not None and self.last_send_attempt_time is not None and self.last_measurement < self.last_send_attempt_time:
            return []
        
        return [
            [self.last_send_success, self.last_send_duration or 0, self.drop_rate]
        ]
    
    async def send_last_measurements(self, now: float):

        await asyncio.sleep(0.1)

        # Swap measurement buffer
        old_buffer = self.measurement_buffer
        self.measurement_buffer = list()

        if(self.logger.isEnabledFor(_nameToLevel['DEBUG'])):
            self.logger.debug(f'Starting measurment dispatch. {len(old_buffer)} in curent buffer')

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

                    measurement_timestamp = start + (time_increment*i)
                    # as_date = datetime.fromtimestamp(measurement_timestamp, tz=timezone.utc)
                    if part not in combined_measurement_dict:
                        combined_measurement_dict[part] = list()
                    combined_measurement_dict[part].append((measurement_timestamp, m))
                    i += 1

        total_size = 0

        # Calculate size of resulting byte array first to optmize memory allocations
        for part, measurements in combined_measurement_dict.items():
            m_count = len(measurements)

            format = get_struct_format_for_part([t[1] for t in part.get_measurement_shape()])

            total_size += CHAR_SIZE + SHORT_SIZE # Add size for part index and number of measurements

            mesurement_size = struct.calcsize(format)

            i = m_count
            for m in measurements:
                if ((m_count-i) % drop_rate) < 1:
                    total_size += mesurement_size    
                i -= 1

            parts = [s[0] for s in part.get_measurement_shape()]

        measurement_bytes = bytearray(total_size)
        cur = 0

        for part, measurements in combined_measurement_dict.items():
            m_count = len(measurements)

            format = get_struct_format_for_part([t[1] for t in part.get_measurement_shape()])

            struct.pack_into('!B', measurement_bytes, cur, part._index)
            
            cur += CHAR_SIZE
            num_m_location = cur # record location where to later write the number of included measurements to
            cur += SHORT_SIZE

            # Drop the measurement if overwhelmed
            # Start with the last measurement as index 0
            # to ensure it gets send
            i = m_count
            included_m_count = 0
            for (t, m) in measurements:
                if ((m_count-i) % drop_rate) < 1:

                    m = [enocde_measurement(x) for x in m]
                    try:
                        struct.pack_into(format, measurement_bytes, cur, t, *m)
                        cur += struct.calcsize(format)
                    except Exception as e:
                        self.logger.warn(f'failed to prepare measuremetns of part {part.name} at time {t} for sending: {e.args[0]}')
                    
                    included_m_count += 1
                
                i -= 1

            struct.pack_into('!H', measurement_bytes, num_m_location, included_m_count) # Write number of incldued measurements to remembered location


        
        # print(f'Sending measurements for {len(flight_measurements)} parts. Drop rate: {drop_rate}.')

        if(self.logger.isEnabledFor(_nameToLevel['DEBUG'])):
            self.logger.debug(f'Prepared measurements to be send over the Api. Trying to send measurements for {combined_measurement_dict.items()} parts. Drop Rate: {drop_rate}')

        send_start = time.time()

        (send_success, reason) = await self.api_client.try_report_binray_flight_data(self.flight._id, bytes(measurement_bytes), self.send_timeout.total_seconds())

        self.drop_rate = drop_rate
        self.last_send_attempt_time = now

        send_end = time.time()

        send_duration = send_end - send_start

        # Data was not send, therefore return old send date
        if not send_success:

            self.logger.warning(f'Failed sending measurements. Reason: {reason}. Took {send_duration:02}ms')

            self.last_send_success = False
            if reason == 'TIMEOUT':
                self.last_send_duration = self.send_timeout.total_seconds()
            return
        
        if(self.logger.isEnabledFor(_nameToLevel['DEBUG'])):
            self.logger.debug(f'Successfully send  measurements. Took {send_duration:02}ms')

        self.last_send_success = True
        self.last_send_success_time = send_end
        self.last_send_duration = send_duration

def enocde_measurement(m):

    if isinstance(m, str):
        return m.encode()
    
    return m