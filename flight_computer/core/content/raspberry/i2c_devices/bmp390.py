from asyncio import Task
import asyncio
import struct
import time
from smbus import SMBus
from logging import _nameToLevel

from datetime import timedelta
from logging import _nameToLevel
from typing import Callable, Iterable, Tuple, Type, Union
from uuid import UUID
from flight_computer.core.content.raspberry.i2c import RaspberryI2CInterface
from flight_computer.core.logic.rocket_definition import Part, Rocket

BMP_DEVICE_ID = 0x77

BMP_CHIP_ID = 0x00
BMP_MAIN_CONFIG = 0x1B
BMP_CALIBRATION_DATA = 0x31
BMP_STATUS = 0x03

def to_uint16(msb, lsb):
    x, = struct.unpack('>H', bytearray([msb, lsb]))
    return x

def to_int16(msb, lsb):
    x, = struct.unpack('>h', bytearray([msb, lsb]))
    return x

def to_in8(byte):
    x, = struct.unpack('>b', bytearray([byte]))
    return x

def parse_calib_data(reg_data):

    reg_par_t1 = to_uint16(reg_data[1], reg_data[0])
    quanpar_t1 = reg_par_t1 * 2**8
    reg_par_t2 = to_uint16(reg_data[3], reg_data[2])
    quanpar_t2 = reg_par_t2 / 2**30
    reg_par_t3 = to_in8(reg_data[4])
    quanpar_t3 = reg_par_t3 / 2**48

    reg_par_p1= to_int16(reg_data[6], reg_data[5])
    quanpar_p1 = (reg_par_p1 - (2**14)) / 2**20
    reg_par_p2 = to_int16(reg_data[8], reg_data[7])
    quanpar_p2 = (reg_par_p2 - (2**14)) / 2**29
    reg_par_p3 = to_in8(reg_data[9])
    quanpar_p3 = reg_par_p3 / 2**32
    reg_par_p4 = to_in8(reg_data[10])
    quanpar_p4 = reg_par_p4 / 2**37
    reg_par_p5 = to_uint16(reg_data[12], reg_data[11])
    quanpar_p5 = reg_par_p5 * 2**3
    reg_par_p6 = to_uint16(reg_data[14], reg_data[13])
    quanpar_p6 = reg_par_p6 / 2**6
    reg_par_p7 = to_in8(reg_data[15])
    quanpar_p7 = reg_par_p7 / 2**8
    reg_par_p8 = to_in8(reg_data[16])
    quanpar_p8 = reg_par_p8 / 2**15
    reg_par_p9 = to_int16(reg_data[18], reg_data[17])
    quanpar_p9 = reg_par_p9 / 2**48
    reg_par_p10 = to_in8(reg_data[19])
    quanpar_p10 = reg_par_p10 / 2**48
    reg_par_p11 = to_in8(reg_data[20])
    quanpar_p11 = reg_par_p11 / 2**65

    #return ((reg_par_t1, reg_par_t2, reg_par_t3), (reg_par_p1, reg_par_p2, reg_par_p3, reg_par_p4, reg_par_p5, reg_par_p6, reg_par_p7, reg_par_p8, reg_par_p9, reg_par_p10, reg_par_p11))
    return ((quanpar_t1, quanpar_t2, quanpar_t3), (quanpar_p1, quanpar_p2, quanpar_p3, quanpar_p4, quanpar_p5, quanpar_p6, quanpar_p7, quanpar_p8, quanpar_p9, quanpar_p10, quanpar_p11))

def compensate_temp(temp_calibration, uncomp_temp):
    partial_data1 = uncomp_temp - temp_calibration[0]
    partial_data2 = partial_data1 * temp_calibration[1]

    return partial_data2 + ((partial_data1 * partial_data1) * temp_calibration[2])

def compensate_pressure(p_calib, uncomp_pressure, temp):

    partial_data1 = p_calib[5] * temp
    partial_data2 = p_calib[6] * temp**2
    partial_data3 = p_calib[7] * temp**3
    partial_out1 = p_calib[4] + partial_data1 + partial_data2 + partial_data3

    partial_data1 = p_calib[1] * temp
    partial_data2 = p_calib[2] * temp**2
    partial_data3 = p_calib[3] * temp**3
    partial_out2 = uncomp_pressure * (p_calib[0] + partial_data1 + partial_data2 + partial_data3)

    partial_data1 = uncomp_pressure**2
    partial_data2 = p_calib[8] + p_calib[9] * temp
    partial_data3 = partial_data1 * partial_data2
    partial_data4 = partial_data3 + uncomp_pressure**3 * p_calib[10]

    return partial_out1 + partial_out2 + partial_data4

class BNO055_Raspberry(Part):

    type = 'Sensor.Barometetric_Altimeter'

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
        self.configured = False

        i2c.i2c_loop_callbacks.add(self.make_i2c_callback())

        super().__init__(_id, name, parent, list()) # type: ignore

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            *super().get_measurement_shape(),
            ('i2c_address', 1, 'i'),
            ('temperature', 0, 'f'),
            ('pressure', 0, 'f'),
        ]

    def get_accepted_commands(self):
        return [
            *super().get_accepted_commands()
        ]
    
    def get_command_callbacks(self):
        return [
            *super().get_command_callbacks()
        ]
   
    def update(self, now, iteration):

        return
    
    def make_i2c_callback(self):

        def i2c_callback(i2c, now, iteration):

            if not self.configured:

                self.configured = True
                # chip_id = i2cbus.read_byte_data(BMP_DEVICE_ID, 0x00)
                # print(f'chip id: {chip_id}')

                self.log('BMP390 not configured yet, sending configuration commands...')

                config = 0b00110011
                i2c.write_byte_data(BMP_DEVICE_ID, 0x1B, config)
                time.sleep(0.01)
                i2c.write_byte_data(BMP_DEVICE_ID, 0x19, 0x00)
                time.sleep(0.01)
                i2c.write_byte_data(BMP_DEVICE_ID, 0x1C, 0)
                time.sleep(0.01)
                i2c.write_byte_data(BMP_DEVICE_ID, 0x1D, 0)
                time.sleep(0.01)
                calib_data_block = i2c.read_i2c_block_data(BMP_DEVICE_ID, 0x31, 27)
                self.calib_data = parse_calib_data(calib_data_block)

                status = i2c.read_byte_data(BMP_DEVICE_ID, 0x03)

                pressure_ready = (status & 0b00010000) > 0
                temp_ready = (status & 0b0010000) > 0

                if not pressure_ready or not temp_ready:
                    self.log(f'Failed configuration. Pressure ready: {pressure_ready}; Temp ready: {temp_ready}', _nameToLevel['ERROR'])

                self.log('Successfuly configured sensor')

            block = i2c.read_i2c_block_data(BMP_DEVICE_ID,  0x04, 6)

            pressure_uncomp = ((block[2]<<16 | block[1]<<8 | block[0]))
            temp_uncomp = ((block[5]<<16 | block[4]<<8 | block[3]))

            temp_compensated = compensate_temp(self.calib_data[0], temp_uncomp)
            pressure_compensated = compensate_pressure(self.calib_data[1], pressure_uncomp, temp_compensated)

            self.submit_measurement(3, temp_compensated)
            self.submit_measurement(4, pressure_compensated)

        
        return i2c_callback