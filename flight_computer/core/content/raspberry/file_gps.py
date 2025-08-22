

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
            ('lat', 0, 'f'),
            ('lon', 0, 'f'),   
            ('speed', 0, 'f'),    
            ('valid', 0, '?')
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

                if 'lat' in gps_data and gps_data['lat'] is not None:
                    self.submit_measurement_by_name('lat', gps_data['lat'])

                if 'lat' in gps_data and gps_data['lon'] is not None:
                    self.submit_measurement_by_name('lon', gps_data['lon'])

                if 'speed' in gps_data and gps_data['speed'] is not None:
                    self.submit_measurement_by_name('speed', gps_data['speed'])

                if 'valid' in gps_data and gps_data['valid'] is not None:
                    self.submit_measurement_by_name('valid', gps_data['valid'])

        except Exception as e:

            self.log(f'Failed reading gps file: {e}', _nameToLevel['ERROR'])
   
