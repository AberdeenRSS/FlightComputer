# Gets the struct descriptor for the measurement of the part see https://docs.python.org/3.5/library/struct.html
import struct
from io import BytesIO

def get_struct_format_for_part(descriptiors: list[str]) -> str:

    # First value is always the dattime of the measurement as a float
    res = '!d'

    for descriptor in descriptiors:
            res += descriptor

    return res



# def write_next_measurement(buffer: bytearray, pos: int, time: float, measurements: list, format: str):
      
#     struct.pack_into(format, buffer, pos, time, *measurements)