import struct
import time
from smbus import SMBus
import math

def parse_calib_data(reg_data):

    # 1 / 2^8 */
    temp_var = 0.00390625
    reg_par_t1, = struct.unpack('<H', bytearray([reg_data[0], reg_data[1]]))
    quanpar_t1 = reg_par_t1 / temp_var
    reg_par_t2, = struct.unpack('<H', bytearray([reg_data[2], reg_data[3]]))
    temp_var = 1073741824.0
    quanpar_t2 = reg_par_t2 / temp_var
    reg_par_t3, = struct.unpack('<B', bytearray([reg_data[4]]))
    temp_var = 281474976710656.0
    quanpar_t3 = reg_par_t3 / temp_var
    reg_par_p1, = struct.unpack('<H', bytearray([reg_data[5], reg_data[6]]))
    temp_var = 1048576.0
    quanpar_p1 = (reg_par_p1 - (16384)) / temp_var
    reg_par_p2, = struct.unpack('<H', bytearray([reg_data[7], reg_data[8]]))
    temp_var = 536870912.0
    quanpar_p2 = (reg_par_p2 - (16384)) / temp_var
    reg_par_p3, = struct.unpack('<B', bytearray([reg_data[9]]))
    temp_var = 4294967296.0
    quanpar_p3 = reg_par_p3 / temp_var
    reg_par_p4, = struct.unpack('<B', bytearray([reg_data[10]]))
    temp_var = 137438953472.0
    quanpar_p4 = reg_par_p4 / temp_var
    reg_par_p5, = struct.unpack('<H', bytearray([reg_data[11], reg_data[12]]))

    # 1 / 2^3 
    temp_var = 0.125
    quanpar_p5 = reg_par_p5 / temp_var
    reg_par_p6, = struct.unpack('<H', bytearray([reg_data[14], reg_data[13]]))
    temp_var = 64.0
    quanpar_p6 = reg_par_p6 / temp_var
    reg_par_p7, = struct.unpack('<B', bytearray([reg_data[15]]))
    temp_var = 256.0
    quanpar_p7 = reg_par_p7 / temp_var
    reg_par_p8, = struct.unpack('<B', bytearray([reg_data[16]]))
    temp_var = 32768.0
    quanpar_p8 = reg_par_p8 / temp_var
    reg_par_p9, = struct.unpack('<H', bytearray([reg_data[17], reg_data[18]]))
    temp_var = 281474976710656.0
    quanpar_p9 = reg_par_p9 / temp_var
    reg_par_p10, = struct.unpack('<B', bytearray([reg_data[19]]))
    temp_var = 281474976710656.0
    quanpar_p10 = reg_par_p10 / temp_var
    reg_par_p11, = struct.unpack('<B', bytearray([reg_data[20]]))
    temp_var = 36893488147419103232.0
    quanpar_p11 = reg_par_p11 / temp_var

    return ((quanpar_t1, quanpar_t2, quanpar_t3), (quanpar_p1, quanpar_p2, quanpar_p3, quanpar_p4, quanpar_p5, quanpar_p6, quanpar_p7, quanpar_p8, quanpar_p9, quanpar_p10, quanpar_p11))

def compensate_temp(temp_calibration, uncomp_temp):
    partial_data1 = uncomp_temp - temp_calibration[0]
    partial_data2 = uncomp_temp * temp_calibration[1]

    # Update the compensated temperature in calib structure since this is
    # needed for pressure calculation
    return partial_data2 + (partial_data1 * partial_data1) * temp_calibration[2]


BMP_DEVICE_ID = 0x77

i2cbus = SMBus(1)

chip_id = i2cbus.read_byte_data(BMP_DEVICE_ID, 0x00)
print(f'chip id: {chip_id}')

config = 0b00110011
i2cbus.write_byte_data(BMP_DEVICE_ID, 0x1B, config)

time.sleep(0.1)

calib_data_block = i2cbus.read_i2c_block_data(BMP_DEVICE_ID, 0x30, 28)

calib_data = parse_calib_data(calib_data_block)

print(calib_data)

status = i2cbus.read_byte_data(BMP_DEVICE_ID, 0x03)
pressure_ready = (status & 0b00010000) > 0
temp_ready = (status & 0b0010000) > 0

print(f'Presure rdy: {pressure_ready} Temp rdy: {temp_ready}')

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

    pressure, temp = struct.unpack('<II', block_padded)

    temp = compensate_temp(calib_data[0], compensate_temp(temp))
    pressure = pressure/1000

    print(f'Pressure {pressure:.3f}kPa Temp: {temp:.3f}K')

    time.sleep(1)
