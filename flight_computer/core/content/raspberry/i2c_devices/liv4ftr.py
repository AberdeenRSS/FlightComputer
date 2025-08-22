

from datetime import timedelta
from typing import Union
from uuid import UUID
from flight_computer.core.content.raspberry.i2c import RaspberryI2CInterface
from flight_computer.core.logic.rocket_definition import Part, Rocket


class LIV4FTR(Part):

    type = 'Sensor.GPS'

    i2c_device_id = 0x3A

    min_update_period = timedelta(milliseconds=10)
    min_measurement_period = timedelta(milliseconds=5)

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], i2c: RaspberryI2CInterface):

        super().__init__(_id, name, parent, list()) # type: ignore

        i2c.i2c_loop_callbacks.add(self.make_i2c_callback())

        self.i2c_part = i2c

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

        return
    
    def make_i2c_callback(self):

        def i2c_callback(i2c, now, iteration):

            buffer = list()
            self.log(f'{self.i2c_part.i2c_device_port}: {self.i2c_device_id:.2x}')

            while True:
                # Read NMEA messages from gps
                char = i2c.read_byte_data(self.i2c_device_id, 0xFF)
                if char > 127:
                    continue
                # No more messages
                if char == 0:
                    break
                buffer.append(char)
            
            messages = bytes(buffer).decode('ascii').splitlines()

            for msg in messages:
                print(msg)
        
        return i2c_callback
