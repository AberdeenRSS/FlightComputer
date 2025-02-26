from asyncio import Task
import asyncio
import struct
from smbus import SMBus


from datetime import timedelta
from logging import _nameToLevel
from typing import Callable, Iterable, Tuple, Type, Union
from uuid import UUID
from flight_computer.core.content.raspberry.i2c import RaspberryI2CInterface
from flight_computer.core.logic.rocket_definition import Part, Rocket

BNO_DEVICE_ID = 0x28
BNO_OPR_MODE_ADDR = 0x3D
BNO_IMU_OPR_MODE = 0b1000

QUAD_FATOR = 2**14

class BNO055_Raspberry(Part):

    type = 'Sensor.IMU'

    state_check_interval = 5
    '''Configures how often the setup state of the sensor is being checked in seconds'''

    sensor_state_last_checked = 0

    operating_mode = 0

    # Set update to only every 5 seconds as 
    # battery information is low frequency
    min_update_period = timedelta(milliseconds=10)
    min_measurement_period = timedelta(milliseconds=5)

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], i2c: RaspberryI2CInterface, start_enabled = True):

        self.enabled = start_enabled

        i2c.i2c_loop_callbacks.add(self.make_i2c_callback())

        self.desired_operating_mode = BNO_IMU_OPR_MODE
        self.i2c_device_id = BNO_DEVICE_ID

        super().__init__(_id, name, parent, list()) # type: ignore

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            *super().get_measurement_shape(),
            ('i2c_address', 1, 'i'),
            ('operating_mode', 1, 'i'),
            ('acceleration', 0, [('x', 'f'), ('y', 'f'), ('z', 'f')]),
            ('orientation',  0, [('x', 'f'), ('y', 'f'), ('z', 'f'), ('w', 'f')])
        ]

    def get_accepted_commands(self):
        return [
            *super().get_accepted_commands()
        ]
    
    def get_command_callbacks(self):
        return [
            *super().get_command_callbacks()
        ]
   
    def update(self):

        return
    
    def make_i2c_callback(self):

        def i2c_callback(i2c, now, iteration):

            if (now - self.sensor_state_last_checked) > self.state_check_interval:
                self.sensor_state_last_checked = now

                operating_mode = i2c.read_byte_data(self.i2c_device_id, BNO_OPR_MODE_ADDR)

                if operating_mode != self.operating_mode:
                    self.operating_mode = operating_mode
                    self.submit_measurement(3, operating_mode) # Report new operating mode
                    self.log(f'Changed operating mode to 0x{operating_mode:02x}')

                # Device is in config mode or changed config -> we need to configure it
                if operating_mode == 0 or operating_mode != self.desired_operating_mode:
                    i2c.write_byte_data(self.i2c_device_id, BNO_OPR_MODE_ADDR, self.desired_operating_mode)
                    self.log(f'Request change of operating mode from 0x{operating_mode:02x} to 0x{self.desired_operating_mode:02x}')
                    return # we need to wait for the device to be configured

            # Sensor not configured to read data -> return
            if self.operating_mode == 0:
                return
            
            acc = i2c.read_i2c_block_data(self.i2c_device_id,  0x08, 6)
            orientation = i2c.read_i2c_block_data(self.i2c_device_id,  0x20, 8)

            x, y, z = struct.unpack('hhh', bytearray(acc))

            x = x/100
            y = y/100
            z = z/100

            w, x, y, z = struct.unpack('hhhh', bytearray(orientation))

            w = w/QUAD_FATOR
            x = x/QUAD_FATOR
            y = y/QUAD_FATOR
            z = z/QUAD_FATOR

            self.submit_measurement(4, (x, y, z))
            self.submit_measurement(5, (x, y, z, w))

        
        return i2c_callback