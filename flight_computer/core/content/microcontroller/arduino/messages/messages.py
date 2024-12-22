from typing import Collection, Iterable, Tuple, Type, Union, cast

class ResponseMessage:
    arr: bytearray

    def __init__(self, arr: bytearray):
        self.arr = arr

    def getPart(self) -> int:
        ''' Returns the part id the command was for '''
        mask = 0b0011_1111

        return self.arr[0] & mask

    def getCommand(self) -> int:
        ''' Returns the command id'''
        mask = 15

        return (self.arr[2] >> 4) & mask

    def getIndex(self) -> int:
        '''Returns the index of the command (command ids are counted up sequentially)'''
        return self.arr[1]

    def getResponseRequestByte(self) -> int:
        '''Signals if message is a request or response'''
        mask = 1
        return self.arr[0] >> 6 & mask

    def getResult(self) -> int:
        '''Payload response data from the serial device'''
        mask = 15

        return self.arr[2] & mask


class SensorData:
    arr: bytearray

    def __init__(self, arr):
        self.arr = arr

    def getPart(self) -> int:

        mask = 0b0000_1111
        return (self.arr[0] >> 1) & mask

    def getType(self) -> int:

        return self.arr[1] & 0b0000_1111

    def getPayloadLength(self) -> int:

        most_significant_bit = (self.arr[0] & 0b0000_0001) << 4 # Most significant bit of payload length is stored in byte 0
        least_significant_bits = (self.arr[1] & 0b1111_0000) >> 4

        return (most_significant_bit | least_significant_bits) + 1

    def getData(self) -> bytearray:

        # arr = []

        # for i in range(self.getPayloadLength()):
        #     arr.append(int.from_bytes(self.arr[2 + i * 2: 4 + i * 2], 'little'))

        payload_length = self.getPayloadLength()

        return self.arr[2:payload_length+2]



