import struct
import time
from smbus import SMBus
import math

BMP_DEVICE_ID = 0x77

i2cbus = SMBus(1)

chip_id = i2cbus.read_byte_data(BMP_DEVICE_ID, 0x00)
print(f'chip id: {chip_id}')

config = 0b00110011
i2cbus.write_byte_data(BMP_DEVICE_ID, 0x1B, config)

time.sleep(0.1)

#subdiv_settings = i2cbus.read_byte_data(BMP_DEVICE_ID, 0x1D)
#print(f'Subdivs: {subdiv_settings}')

status = i2cbus.read_byte_data(BMP_DEVICE_ID, 0x03)
pressure_ready = (status & 0b00010000) > 0
temp_ready = (status & 0b0010000) > 0

print(f'Presure rdy: {pressure_ready}; Temp rdy: {temp_ready}')

# operating_mode = i2cbus.read_byte_data(BNO_DEVICE_ID, BNO_OPR_MODE_ADDR)
# print(f'Current mode: 0x{operating_mode:02x}')

# i2cbus.write_byte_data(BNO_DEVICE_ID, BNO_OPR_MODE_ADDR, BNO_IMU_OPR_MODE)

# time.sleep(0.1) # Sensor need time to switch modes

# operating_mode = i2cbus.read_byte_data(BNO_DEVICE_ID, BNO_OPR_MODE_ADDR)
# print(f'Current mode: 0x{operating_mode:02x}')

while True:

    block = i2cbus.read_i2c_block_data(BMP_DEVICE_ID,  0x04, 6)

    print(block)

    block_padded = bytearray([0, 0, 0, 0, 0, 0, 0, 0])
    block_padded[1:4] = block[0:3]
    block_padded[5:8] = block[3:6]

    pressure, temp = struct.unpack('!II', block_padded)

    pressure = pressure/1000

    print(f'Pressure {pressure:.3f}kPa; Temp: {temp:.3f}K')

    time.sleep(1)
