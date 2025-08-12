
import asyncio
import base64
from logging import getLogger
import struct
from typing import Collection, Iterable, Self, Sequence, Tuple, Type, Union
from uuid import UUID
from flight_computer.core.helper.binary_format_encoder import enconde_payload
from flight_computer.core.logic.measurement_sink import MeasurementSinkBase
from flight_computer.core.logic.commands.command import Command
from flight_computer.core.logic.measurement_sink import ApiMeasurementSinkBase
from flight_computer.core.logic.rocket_definition import Rocket, Measurement
from flight_computer.core.mqtt_client import MqttClient
import numpy as np

LOGGER_NAME = 'MQTT_Measurement_Sink'

class MqttMeasurementSink(ApiMeasurementSinkBase):
     
    type = 'Measurement_Sink.Mqtt'

    start_task = None
    mqtt_client = None

    max_send_frequency: float = 4
    ''' 
    Maximum send frequency in Hz.
    If a measurement type surpasses this frequency some measurements will be dropped
    '''

    _first_iteration = True

    next_m_t: np.ndarray

    def __init__(self, _id: UUID, name: str, parent: Union[Self, Rocket, None]):
        super().__init__(_id, name, parent)

        self.logger = getLogger(LOGGER_NAME)

    def update(self, now: float, iteration):

        if self._first_iteration:

            # Initialize an array with slots for every measurement possibly sent
            max_m = max(len(p.get_measurement_shape()) for p in self.rocket.parts)
            self.next_m_t = np.zeros((len(self.rocket.parts), max_m))

            self._first_iteration = False

        self.send_last_measurements(now)


    def get_measurement_shape(self) -> Collection[Tuple[str, Union[Type, str, list[Tuple[str, str]]]]]:
        
        return [
            *super().get_measurement_shape(),   
            ('commands_send_last', 0, 'd')
        ]

    def get_accepted_commands(self):
        return [
            *super().get_accepted_commands()
        ]
    
    def get_command_callbacks(self):
        return [
            *super().get_command_callbacks()
        ]

    def collect_measurements(self, now: float, iterations):
        return
    
    def send_last_measurements(self, now: float):

        m_period = 1/self.max_send_frequency

        # Swap measurement buffer
        old_buffer = self.measurement_buffer
        self.measurement_buffer = list()

        count = 0

        for b in old_buffer:
            for part, measurements in b.items():

                count += len(measurements)

                shapes = part.get_measurement_shape()

                for time, msg_index, payload in measurements:

                    cur_next_send_t = self.next_m_t[part._index][msg_index]

                    name, qos, shape = shapes[msg_index]

                    # Rate limit (always send qos > 0 messages)
                    if qos < 1 and cur_next_send_t > now:
                        continue

                    self.next_m_t[part._index][msg_index] = now + m_period
                    self.mqtt_client.client.publish(f'{self.flight._id}/m/{part._index}/{msg_index}', enconde_payload(shape, time, payload), qos)

        self.submit_measurement(2, count, now)
        
    
        