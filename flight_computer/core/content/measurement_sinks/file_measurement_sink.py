
import asyncio
import base64
import json
from logging import getLogger
import struct
from typing import Collection, Iterable, Self, Sequence, Tuple, Type, Union
from uuid import UUID
from flight_computer.core.helper.binary_format_encoder import enconde_payload
from flight_computer.core.logic.measurement_sink import MeasurementSinkBase


from flight_computer.core.logic.commands.command import Command
from flight_computer.core.logic.measurement_sink import ApiMeasurementSinkBase
from flight_computer.core.logic.rocket_definition import Part, Rocket, Measurement
from pathlib import Path
import os


LOGGER_NAME = 'FileMeasurementSink'

class FileMeasurementSink(ApiMeasurementSinkBase):
     
    type = 'Measurement_Sink.File'

    start_task = None
    mqtt_client = None

    def __init__(self, _id: UUID, name: str, parent: Union[Self, Rocket, None]):
        super().__init__(_id, name, parent)

        self._config = json.load(open('./config/config.json'))
        self.global_data_dir = Path(self._config['FLIGHT_DATA_DIR'])
        self.files = dict()
        self.setup = False
        self.logger = getLogger(LOGGER_NAME)


    def update(self, now: float, iteration):

        if not self.setup:
            self.setup = True

            self.flight_data_dir = self.global_data_dir.joinpath(self.flight.name.replace('-', '_'))

            if not os.path.exists(self.flight_data_dir): 
                os.makedirs(self.flight_data_dir) 

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
    
    def get_or_create_csv(self, part: Part, shape: Tuple[str, int, Type | str | list[Tuple[str, str]]]):

        if part.name in self.files:
            return self.files[part.name]
        
        f = self.files[part.name] = open(self.flight_data_dir.joinpath(f'{part.name}_{shape[0]}.csv'), 'a')
        f.write('time,')

        if isinstance(shape, Iterable) and not isinstance(shape, tuple):
            len_m = len(shape)
            i = 0
            for d in shape:
                f.write(f'{d[0]}')
                if i < len_m-1:
                    f.write(',')
                i+=1
        else:
            f.write(shape[0])

        f.write('\n')
        f.flush()

        return f

    
    def send_last_measurements(self, now: float):

        # Swap measurement buffer
        old_buffer = self.measurement_buffer
        self.measurement_buffer = list()

        count = 0

        for b in old_buffer:
            count += len(b)
            for part, measurements in b.items():

                shapes = part.get_measurement_shape()

                for time, msg_index, payload in measurements:

                    shape = shapes[msg_index]

                    f = self.get_or_create_csv(part, shape)

                    res = f'{time},'

                    if isinstance(payload, Iterable):
                        len_m = len(payload)
                        i = 0
                        for d in payload:
                            res += str(d)
                            if i < len_m-1:
                                res += ','
                            i+=1
                    else:
                        res += str(payload)

                res += '\n'

                f.write(res)
                f.flush()

        self.submit_measurement(2, count, now)

    def __del__(self):
        for f in self.files.keys():
            f.close()

        
    
        