import struct
import time
from smbus import SMBus
import math

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

def compensate_int_temp(uncomp_temp, calib_data):

    partial_data1 = uncomp_temp - (256 * calib_data[0])
    partial_data2 = calib_data[1] * partial_data1
    partial_data3 = partial_data1 * partial_data1
    partial_data4 = partial_data3 * calib_data[2]
    partial_data5 = (partial_data2 * 262144) + partial_data4
    partial_data6 = partial_data5 / 4294967296

    return ((partial_data6 * 25) / 16384, partial_data6)


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


BMP_DEVICE_ID = 0x77

i2cbus = SMBus(1)

chip_id = i2cbus.read_byte_data(BMP_DEVICE_ID, 0x00)
print(f'chip id: {chip_id}')

config = 0b00110011
i2cbus.write_byte_data(BMP_DEVICE_ID, 0x1B, config)

time.sleep(0.1)

i2cbus.write_byte_data(BMP_DEVICE_ID, 0x19, 0x00)

time.sleep(0.1)

i2cbus.write_byte_data(BMP_DEVICE_ID, 0x1C, 0)

time.sleep(0.1)

i2cbus.write_byte_data(BMP_DEVICE_ID, 0x1D, 0)

time.sleep(0.1)

calib_data_block = i2cbus.read_i2c_block_data(BMP_DEVICE_ID, 0x31, 27)

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

    #print(block)

    pressure = ((block[2]<<16 | block[1]<<8 | block[0]))
    temp = ((block[5]<<16 | block[4]<<8 | block[3]))

    temp_compensated = compensate_temp(calib_data[0], temp)
    pressure_compensated = compensate_pressure(calib_data[1], pressure, temp_compensated)

    #print(f'Temp raw: {temp:.3f}; Compensated: {temp_compensated:.3f}C')
    # print(f'Pres raw: {pressure:.3f}; Compensated: {pressure_compensated:.3f}kPa')

    p_0 = 103000
    __ALTITUDE_EQ_EXPONENT__ = 1/5.257
    alt = ((math.pow(p_0/pressure_compensated, __ALTITUDE_EQ_EXPONENT__) - 1) * temp_compensated) / 0.0065

    print(f'{pressure_compensated/100:.3f}kPa; Alt: {alt:.2f}')



    time.sleep(1)
