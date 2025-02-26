import struct
import time
from smbus import SMBus

BNO_DEVICE_ID = 0x28

BNO_OPR_MODE_ADDR = 0x3D

BNO_IMU_OPR_MODE = 0b1000

i2cbus = SMBus(1)

operating_mode = i2cbus.read_byte_data(BNO_DEVICE_ID, BNO_OPR_MODE_ADDR)
print(f'Current mode: 0x{operating_mode:02x}')

i2cbus.write_byte_data(BNO_DEVICE_ID, BNO_OPR_MODE_ADDR, BNO_IMU_OPR_MODE)

time.sleep(0.1) # Sensor need time to switch modes

operating_mode = i2cbus.read_byte_data(BNO_DEVICE_ID, BNO_OPR_MODE_ADDR)
print(f'Current mode: 0x{operating_mode:02x}')

while True:

    reg = i2cbus.read_i2c_block_data(BNO_DEVICE_ID,  0x08, 6)


    x, y, z = struct.unpack('hhh', bytearray(reg))

    x = x/100
    y = y/100
    z = z/100

    time.sleep(0.1)

    print(f'x: {x}; y: {y}; z: {z}')
