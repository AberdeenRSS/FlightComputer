
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
from flight_computer.core.mqtt_client import MqttClient

LOGGER_NAME = 'MQTT_Measurement_Sink'

class MqttMeasurementSink(ApiMeasurementSinkBase):
     
    type = 'Measurement_Sink.Mqtt'

    start_task = None
    mqtt_client = None

    def __init__(self, _id: UUID, name: str, parent: Union[Self, Rocket, None]):
        super().__init__(_id, name, parent)


        self.logger = getLogger(LOGGER_NAME)

    def update(self, commands: Iterable[Command], now: float, iteration):


        if self.start_task is not None and self.start_task.done():
            self.send_last_measurements(now)
            return

        if self.start_task is None or self.start_task.exception() is not None:
            
            if self.mqtt_client is None:
                self.mqtt_client = MqttClient(self.api_client)

            self.start_task = asyncio.create_task(self.mqtt_client.start())


    def get_measurement_shape(self) -> Collection[Tuple[str, Union[Type, str, list[Tuple[str, str]]]]]:
        
        return [
            *super().get_measurement_shape(),   
            ('commands_send_last', 0, 'd')
        ]

    def get_accepted_commands(self) -> Iterable[Type[Command]]:

        return []

    def collect_measurements(self, now: float, iterations) -> Sequence[Measurement] | None:
        
        return None
    
    def send_last_measurements(self, now: float):

        # Swap measurement buffer
        old_buffer = self.measurement_buffer
        self.measurement_buffer = list()

        for b in old_buffer:
            for part, measurements in b.items():

                shapes = part.get_measurement_shape()

                for time, msg_index, payload in measurements:

                    name, qos, shape = shapes[msg_index]
                    self.mqtt_client.client.publish(f'{self.flight._id}/m/{part._index}/{msg_index}', enconde_payload(shape, time, payload), qos)

    
def enconde_payload(shape, time, payload):

    if shape is str:

        time_bytes = struct.pack('!d', payload)
        time_string = base64.b64encode(time_bytes).decode('utf-8') # convert bytes to string
        return  time_string + payload
    
    payload_bytes = struct.pack(f'!d{shape}', time, *payload) if isinstance(payload, Iterable) else struct.pack(f'!d{shape}', time, payload)

    return payload_bytes
        