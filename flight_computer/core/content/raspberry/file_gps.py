

from datetime import timedelta
import json
from logging import _nameToLevel
from typing import Union
from uuid import UUID
from flight_computer.core.content.raspberry.i2c import RaspberryI2CInterface
from flight_computer.core.logic.rocket_definition import Part, Rocket


class FileGps(Part):

    type = 'Sensor.GPS'


    min_update_period = timedelta(milliseconds=500)
    min_measurement_period = timedelta(milliseconds=500)

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], file: str):

        super().__init__(_id, name, parent, list()) # type: ignore

        self.file = file

        # self.M_TEMP = self.measurement_index_lookup['temp']

    def make_measurement_shape(self):
        return [
            *super().make_measurement_shape(),           
        ]

    def make_accepted_commands(self):
        return [
            *super().make_accepted_commands()
        ]
    
    def make_command_callbacks(self):
        return [
            *super().make_command_callbacks()
        ]
   
    def update(self, now, iteration):

        try:

            with open(self.file, 'r') as f:

                gps_data = json.loads(f.read())

                print(gps_data)

        except Exception as e:

            self.log(f'Failed reading gps file: {e}', _nameToLevel['ERROR'])
   
