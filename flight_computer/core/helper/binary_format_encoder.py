import base64
import struct
import sys
from typing import Collection, Iterable

INT_SIZE = struct.calcsize('i')
DOUBLE_SIZE = struct.calcsize('d')

def enconde_payload(shape: type | str | list[tuple[type | str]], time: float, payload) -> tuple[bytes, int]:

    # Top level case
    res = bytearray(DOUBLE_SIZE + calc_payload_size(shape, payload))

    # Write time to result
    struct.pack_into('!d', res, 0, time)
    offset = DOUBLE_SIZE

    enconde_payload_internal(shape, payload, res, offset)
    return res


def enconde_payload_internal(shape: type | str | list[tuple[type | str]], payload, res: bytes, offset: int, top_level: bool = True) -> tuple[bytes, int]:

    # Hot path for struct shaped payloads (high performance case as high frequency values are like this) 
    if isinstance(shape, str):

        # Array of data case
        if shape.startswith('['):
            payload_len = len(payload)

            if not top_level:
                # Add length
                struct.pack_into('!i', res, offset, payload_len)
                offset += INT_SIZE

            for v in payload:
                res, offset = enconde_payload_internal(shape[1:-1], v, res, offset, False)

            return res, offset

        struct.pack_into(f'!{shape}', res, offset, *payload if isinstance(payload, Collection) else payload)
        offset += struct.calcsize(shape)
        return res, offset

    if shape == str:
        encoded_str = payload.encode('utf-8')
        str_len = len(encoded_str)
        if top_level:
            res[offset:offset+str_len] = encoded_str
            offset += str_len
            return res, offset
        
        # Add string length
        struct.pack_into('!i', res, offset, str_len)
        offset += INT_SIZE

        res[offset:offset+str_len] = encoded_str
        offset += str_len
        return res, offset

    if isinstance(shape, tuple):
        res, offset = enconde_payload_internal(shape[1], payload, res, offset, False)
        return res, offset

    if isinstance(shape, Collection):
        i = 0
        for s in shape:
            res, offset = enconde_payload_internal(s, payload[i], res, offset, False)
            i += 1
        return res, offset
    
    raise Exception()

def calc_payload_size(shape: type | str | list[tuple[type | str]], payload, top_level: bool = True):

    if shape == str:
        if top_level:
            return sys.getsizeof(payload) - sys.getsizeof('')
        return INT_SIZE + sys.getsizeof(payload) - sys.getsizeof('')

    if isinstance(shape, str):

        if shape.startswith('['):
            if top_level:
                return struct.calcsize(shape[1:-1])*len(payload)
            return INT_SIZE + struct.calcsize(shape[1:-1])*len(payload)

        return struct.calcsize(shape)
    
    if isinstance(shape, tuple):
        return calc_payload_size(shape[1], payload, False)

    if isinstance(shape, Collection):
        i = 0
        sum = 0
        for s in shape:
            sum += calc_payload_size(s[1], payload[i], False)
            i +=1
        return sum
    
    raise Exception()


def decode_payload(shape: type | str | list[tuple[type | str]], payload: bytes):

    time = struct.unpack_from('!d', payload, 0)

    res, offset = decode_payload_internal(shape, payload, DOUBLE_SIZE)

    return time, res

def decode_payload_internal(shape: type | str | list[tuple[type | str]], payload: bytes, offset: int, top_level: bool = True):

    # Hot path for struct shaped payloads (high performance case as high frequency values are like this) 
    if isinstance(shape, str):

        # Array of data case
        if shape.startswith('['):

            if top_level:
                payload_len = int((len(payload) - offset)/struct.calcsize(shape[1:-1]))
            else:
                payload_len, = struct.unpack_from('!i', payload, offset)
                offset += INT_SIZE

            res = list()

            for i in range(0, payload_len):
                resi, offset = decode_payload_internal(shape[1:-1], payload, offset, False)
                res.append(resi)
            return res, offset

        res = struct.unpack_from(f'!{shape}', payload, offset)
        offset += struct.calcsize(shape)
        return res if len(res) > 1 else res[0], offset

    if shape == str:

        if top_level:
            str_len = len(payload) - offset
        else:
            str_len, = struct.unpack_from('!i', payload, offset)
            offset += INT_SIZE

        res = payload[offset:offset+str_len].decode()
        offset += str_len
        
        return res, offset

    if isinstance(shape, tuple):
        res, offset = decode_payload_internal(shape[1], payload, offset, False)
        return res, offset

    if isinstance(shape, Collection):
        res = list()
        for s in shape:
            resi, offset = decode_payload_internal(s, payload, offset, False)
            res.append(resi)
        return res, offset
    
    raise Exception()