
import asyncio
import base64
from logging import getLogger
import struct
from typing import Collection, Iterable, Self, Sequence, Tuple, Type, Union
from uuid import UUID
from flight_computer.core.logic.measurement_sink import MeasurementSinkBase


from flight_computer.core.logic.commands.command import Command
from flight_computer.core.logic.measurement_sink import ApiMeasurementSinkBase
from flight_computer.core.logic.rocket_definition import Rocket, Measurement

LOGGER_NAME = 'Mock_Measurement_Sink'

class MockMeasurementSink(ApiMeasurementSinkBase):
     
    type = 'Measurement_Sink.Mock'

    start_task = None
    mqtt_client = None

    def __init__(self, _id: UUID, name: str, parent: Union[Self, Rocket, None]):
        super().__init__(_id, name, parent)


        self.logger = getLogger(LOGGER_NAME)

    def update(self, now: float, iteration):

        return

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
   