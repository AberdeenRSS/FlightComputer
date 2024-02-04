from typing import Collection, Iterable, Tuple, Type, Union, cast

class ResponseMessage:
    arr: bytearray

    def __init__(self, arr: bytearray):
        self.arr = arr

    def getPart(self) -> int:
        mask = 63

        return self.arr[0] & mask

    def getCommand(self) -> int:
        mask = 15

        return (self.arr[2] >> 4) & mask

    def getIndex(self) -> int:
        return self.arr[1]

    def getResponseRequestByte(self) -> int:
        mask = 1
        return self.arr[0] >> 6 & mask

    def getResult(self) -> int:
        mask = 15

        return self.arr[2] & mask


class SensorData:
    arr: bytearray

    def __init__(self, arr):
        self.arr = arr

    def getPart(self) -> int:
        mask = 127

        return self.arr[0] & mask

    def getType(self) -> int:
        mask = 15

        return (self.arr[1] >> 4) & mask

    def getPayloadLength(self) -> int:
        mask = 15

        return self.arr[1] & mask

    def getData(self) -> list[int]:
        arr = []
        for i in range(self.getPayloadLength()):
            arr.append(int.from_bytes(self.arr[2 + i * 2: 4 + i * 2], 'little'))

        return arr


messageIndex = 1
def sendCommand(partID : int, commandID : int, pl : int = 0):
    global messageIndex
    arr = bytearray(0 for x in range(3))

    arr[0] |= 1 << 7
    arr[0] |= partID
    arr[1] |= messageIndex
    arr[2] |= commandID << 4
    arr[2] |= pl

    messageIndex += 1
    return arr, messageIndex - 1
