import struct
import time
from smbus import SMBus

BNO_DEVICE_ID = 0x40

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

    x0 = i2cbus.read_byte_data(BNO_DEVICE_ID, 0x08)
    x1 = i2cbus.read_byte_data(BNO_DEVICE_ID, 0x09)
    y0 = i2cbus.read_byte_data(BNO_DEVICE_ID, 0x0A)
    y1 = i2cbus.read_byte_data(BNO_DEVICE_ID, 0x0B)
    z0 = i2cbus.read_byte_data(BNO_DEVICE_ID, 0x0C)
    z1 = i2cbus.read_byte_data(BNO_DEVICE_ID, 0x0D)

    x, y, z = struct.unpack('hhh', bytearray([x0, x1, y0, y1, z0, z1]))

    print(f'x: {x}; y: {y}; z: {z}')