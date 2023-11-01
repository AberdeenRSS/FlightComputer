
from typing import Collection, Iterable, Tuple, Type, Union, cast


class AReceivedMessage:
    partCode : float

    def __init__(self, partCode : bytes = 0x00):
        self.partCode = partCode

class CommunicationErrors:
    result : dict

    def __init__(self):
        self.result = dict()
        self.result[0x00] = 'Success'

        self.result[0x01] = 'Incompatible Launch Phase'

        self.result[0x10] = 'Message Layout Error! Wrong Start Byte'
        self.result[0x11] = 'Message Layout Error! Wrong Connection Byte'
        self.result[0x12] = 'Message Layout Error! Wrong State Byte'
        self.result[0x13] = 'Message Layout Error! WrongPartByte'
        self.result[0x14] = 'Message Layout Error! WrongCommandByte'
        self.result[0x15] = 'Message Layout Error! WrongEndByte'

    def __getitem__(self, item : bytes) -> str:
        return self.result[item]

class ResponseM(AReceivedMessage):

    commandCode : bytes

    resultCode : bytes

    def __init__(self, message : bytearray):
        super().__init__(message[3])
        self.commandCode = message[4]
        self.resultCode = message[5]

    def get_result(self) -> str:
        ce = CommunicationErrors()
        return ce[self.resultCode]

class SensorDataMessage(AReceivedMessage):
    data     : float
    partCode : float
    dataPart : float

    def __init__(self, message : bytearray):
        super().__init__(message[3])

        dataSize = int(message[5])
        self.data = float(message[6: dataSize + 6])
        self.dataPart = message[4]

    def get_data(self):
        return self.data

    def get_data_part(self):
        return self.dataPart

class ArduinoStateMessage(AReceivedMessage):

    def __init__(self, message : bytearray):
        super().__init__()




class ResponseMessage:
    message : bytearray


    def __init__(self):
        self.message = bytearray([])

    def parse(self, received_msg : bytearray) -> Union[ResponseM, SensorDataMessage, ArduinoStateMessage, None]:
        msg = None
        for i in received_msg:
            if len(self.message) and self.message[-1] != 0x7E and i == 0x7E:
                self.message.append(i)
                msg = self.checkCommandType()
                self.message = bytearray([])
            else:
                self.message.append(i)

        return msg


    def checkCommandType(self) -> Union[ResponseM, SensorDataMessage, ArduinoStateMessage, None]:
        if(len(self.message)):
            print(self.message)
            if self.message[2] == 0x00:
                return ResponseM(self.message)

            elif self.message[2] == 0x01:
                return ArduinoStateMessage(self.message)

            elif self.message[2] == 0x02:
                return  SensorDataMessage(self.message)

            return None
