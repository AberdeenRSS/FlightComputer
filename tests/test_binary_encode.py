
import time
import pytest
from flight_computer.core.helper.binary_format_encoder import enconde_payload, decode_payload, enconde_payload_internal

def test_encode_str():

    test_str = 'Some test string äh umlaute, interessant 😅'

    encoded = enconde_payload(str, time.time(), test_str)

    timestamp, decoded = decode_payload(str, encoded)

    assert test_str == decoded

def test_encode_struct():

    format = 'di?'

    tst_double = 3.34333e22
    tst_int = 2304
    tst_bool = True

    encoded = enconde_payload(format, time.time(), (tst_double, tst_int, tst_bool))

    timestamp, decoded = decode_payload(format, encoded)

    assert tst_double == decoded[0]
    assert tst_int == decoded[1]
    assert tst_bool == decoded[2]

def test_array():

    format = '[di?]'

    tst = [(2.343434, 59684, False), (2.343434e-11, 684, True), (12e10, 3, False)]

    encoded = enconde_payload(format, time.time(), tst)

    timestamp, decoded = decode_payload(format, encoded)

    i = 0
    for v in tst:
        j = 0
        for vv in v:
            assert vv == decoded[i][j]
            j += 1
        i += 1

def test_multiple():

    tst_double = 3.34333e22
    tst_int = 2304
    tst_bool = True
    test_str = 'Some test string äh umlaute, interessant 😅'
    tst_list = [(2.343434, 59684, False), (2.343434e-11, 684, True), (12e10, 3, False)]

    format = [('value_a', 'di?'), ('value_b', str), ('some_list', '[di?]')]

    encoded = enconde_payload(format, time.time(), [(tst_double, tst_int, tst_bool), test_str, tst_list])

    timestamp, decoded = decode_payload(format, encoded)

    assert tst_double == decoded[0][0]
    assert tst_int == decoded[0][1]
    assert tst_bool == decoded[0][2]

    assert test_str == decoded[1]

    i = 0
    for v in tst_list:
        j = 0
        for vv in v:
            assert vv == decoded[2][i][j]
            j += 1
        i += 1
