class Message:
    partCode     : bytes
    commandCode  : bytes

    def __init__(self, partCode: chr = 0x00, commandCode: chr = 0x00):
        self.partCode = partCode
        self.commandCode = commandCode

    def getMessage(self):
        messageStart = messageEnd = 0x7E
        direction = messageType = 0x00

        message = [messageStart, direction, messageType, self.partCode, self.commandCode, messageEnd]
        return bytearray(message)


class AMessageList:
    partCode     : chr
    messageDict  : dict()

    def __init__(self, partCode: chr = 0x00):
        self.partCode = partCode
        self.messageDict = dict()

    def addCommandMessage(self, commandName: str, commandCode: chr):
        self.messageDict[commandName] = Message(self.partCode, commandCode)

    def sendCommand(self, messageNmae: str) -> bytearray :
        return self.messageDict[messageNmae].getMessage()

    def __getitem__(self, key : str)-> bytearray:
        return self.messageDict[key].getMessage()


