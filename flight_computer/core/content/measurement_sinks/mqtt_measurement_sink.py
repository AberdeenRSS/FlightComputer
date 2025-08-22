
from logging import getLogger, _nameToLevel
from typing import Iterable, Self, Tuple, Type, Union
from uuid import UUID
from flight_computer.core.helper.binary_format_encoder import enconde_payload
from flight_computer.core.logic.measurement_sink import ApiMeasurementSinkBase
from flight_computer.core.logic.rocket_definition import Rocket
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
            max_m = max(len(p.make_measurement_shape()) for p in self.rocket.parts)
            self.next_m_t = np.zeros((len(self.rocket.parts), max_m))

            self._first_iteration = False

        self.send_last_measurements(now)

    def make_measurement_shape(self):
        
        return [
            *super().make_measurement_shape(),   
            ('commands_send_last', 0, 'd')
        ]

    def make_accepted_commands(self):
        return [
            *super().make_accepted_commands()
        ]
    
    def make_command_callbacks(self):
        return [
            *super().make_command_callbacks()
        ]
    
    def make_config_shape(self) -> list[Tuple[str, str | Type]]:
        return [
            *super().make_config_shape(),
            ('max_send_frequency', 'f')
        ]
    
    def load_config(self, config: dict[str, str | bytes | float | int | bool | Iterable[float | int | bool]]):
        super().load_config(config)

        if 'max_send_frequency' in config:
            self.max_send_frequency = float(config['max_send_frequency']) # type: ignore

    def dump_config(self) -> dict[str, str | bytes | float | int | bool | Iterable[float | int | bool]]:
        return {
            **super().dump_config(),
            'max_send_frequency': self.max_send_frequency
        }

    def collect_measurements(self, now: float, iterations):
        return
    
    def send_last_measurements(self, now: float):

        if self.mqtt_client is None or self.mqtt_client.client is None:
            return
        
        m_period = 1/self.max_send_frequency


        # Swap measurement buffer
        old_buffer = self.measurement_buffer
        self.measurement_buffer = list()

        count = 0

        for b in old_buffer:
            for part, measurements in b.items():

                shapes = part.make_measurement_shape()

                for time, msg_index, payload in measurements:

                    cur_next_send_t = self.next_m_t[part._index][msg_index]

                    name, qos, shape = shapes[msg_index]

                    # Rate limit (always send qos > 0 messages)
                    if qos < 1 and cur_next_send_t > now:
                        continue

                    count += 1
                    self.next_m_t[part._index][msg_index] = now + m_period
                    try:
                        self.mqtt_client.client.publish(f'{self.flight._id}/m/{part._index}/{msg_index}', enconde_payload(shape, time, payload), qos)
                    except Exception as e:
                        self.log(f'Error sending measurement of type {part.measurement_shape[msg_index][0]} for {part.name}: {e}', _nameToLevel['ERROR'])

        if count > 0:
            self.submit_measurement_by_name('commands_send_last', count, now)
        
