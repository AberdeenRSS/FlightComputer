import struct
import time
from smbus import SMBus
import math

BMP_DEVICE_ID = 0x77


i2cbus = SMBus(1)

# operating_mode = i2cbus.read_byte_data(BNO_DEVICE_ID, BNO_OPR_MODE_ADDR)
# print(f'Current mode: 0x{operating_mode:02x}')

# i2cbus.write_byte_data(BNO_DEVICE_ID, BNO_OPR_MODE_ADDR, BNO_IMU_OPR_MODE)

# time.sleep(0.1) # Sensor need time to switch modes

# operating_mode = i2cbus.read_byte_data(BNO_DEVICE_ID, BNO_OPR_MODE_ADDR)
# print(f'Current mode: 0x{operating_mode:02x}')

while True:

    block = i2cbus.read_i2c_block_data(BMP_DEVICE_ID,  0x04, 6)


    pressure = struct.unpack('h', bytearray(block))


    time.sleep(0.1)
