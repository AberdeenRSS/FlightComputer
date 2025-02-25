from smbus import SMBus

BNO_ADDR = 0x40
BNO_OPR_MODE_ADDR = 0x3D
    
i2cbus = SMBus(1)

operating_mode = i2cbus.read_byte_data(BNO_ADDR, BNO_OPR_MODE_ADDR)

print(operating_mode)

