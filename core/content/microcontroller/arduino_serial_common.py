from abc import ABC, abstractmethod
from asyncio import Future, Task
from dataclasses import dataclass
from logging import getLogger
from typing import Callable, Collection
from core.content.microcontroller.arduino.messages.messages import ResponseMessage, SensorData
from core.logic.commands.command import Command

from core.logic.rocket_definition import Part

LOGGER_NAME = 'Serial Adapter'


@dataclass
class RssPacket:

    index: int

    command: int

    payload_size: int

    payload: bytes

    def to_bytes(self):
        return [*self.index.to_bytes(), *self.command.to_bytes(), *self.payload_size.to_bytes(), *self.payload]

def make_default_command_callback(c: Command):

    def default_command_callback(res: Future[int]):
        exception = res.exception()
        if exception is not None:
            c.state = 'failed'
            c.response_message  = exception.args[0]
            return
        
        c.state = 'success'
    
    return default_command_callback



class ArduinoSerialAdapter:

    ''' 
    Class sitting between the hardware connection and the program level logic.
    Transforms raw serial data into program level data and back
    '''

    dataCallbacks: dict[int, Callable[[int, bytearray], None]]
    '''
    Callbacks for other parts to register on. If a command is received for that part it
    gets forwarded to that part.
    '''

    command_futures: dict[int, Future[int]]
    '''Futures that get completed when the Serial'''

    swap_futures: dict[int, Future[int]]
    '''Old futures that are scheduled for timeout'''

    send_func: Callable[[bytearray], None]

    last_keep_alive: float = 0
    '''Last point in time a keep alive was send'''

    keep_alive_interval: float = 1
    '''The interval of sending keep alive messages'''

    last_future_swap: float = 0
    '''Last time the futures where swapped to set them to timeout'''

    future_timeout: float = 1.5
    '''Time until command futures time out'''

    message_index = 0
    '''
    Index of the current message to be send
    Rolls over at 255
    '''

    def __init__(self, send_func: Callable[[bytearray], None]):
        self.send_func = send_func
        self.dataCallbacks = dict()

        self.logger = getLogger('Arduino Serial Adapter')

        self.command_futures = dict()
        self.swap_futures = dict()

        self.errorMessageDict = dict()
        self.errorMessageDict[0] = "Success"
        self.errorMessageDict[1] = "Failed : Incompatible Launch Phase"
        self.errorMessageDict[2] = "Failed : Incorrect Part Byte"
        self.errorMessageDict[3] = "Failed : Incorrect Command Byte"
        self.errorMessageDict[4] = "Failed"

    def addDataCallback(self, part: int, callback: Callable[[int, bytearray], None]):
        '''
        Adds a new callback to be called if there is data for the part
        '''
        self.dataCallbacks[part] = callback
    
    def flush_command_futures(self, reason: str):
        '''
        Sets exceptions on all outstanding command futures
        '''
        for future in self.command_futures.values():
                if not future.done():
                    future.set_exception(Exception(reason))
        
        for future in self.swap_futures.values():
            if not future.done():
                future.set_exception(Exception(reason))

    def make_on_keep_alive_done(self):
        def on_keep_alive_done(f: Future):

            if f.exception() is None:
                self.logger.info('Arduino Serial: keep alive success')
                return
                
            self.logger.error(f'Arduino Serial: keep alive failed: {f.exception()}')

        return on_keep_alive_done

    def on_read(self, a: bytearray):
        '''
        Method to be called if there is raw data received from the arduino
        '''

        try:
            # Check that the 8th bit is set (indicating response message)
            if a[0] & 0b1000_0000 > 0:

                response = ResponseMessage(a)

                if response.getResponseRequestByte() == 1:

                    if response.getIndex() not in self.command_futures:
                        return
                        
                    future = self.command_futures.pop(response.getIndex())

                    result = response.getResult()
                    
                    try:
                        future.set_result(result)
                    except Exception as e:
                        self.logger.error(f'{LOGGER_NAME}: Cannot set response future: {e}')

                else:
                    raise RuntimeError('Received request from Arduino, the arduino should only send responses')

            else:
                sensorData = SensorData(a)
                part = sensorData.getPart()
                data = sensorData.getData()

                if part not in self.dataCallbacks:
                    self.logger.warning(f'{LOGGER_NAME}: Received sensor data from arduino for unknown part: {part}')
                    return

                try:
                    # self.logger.info(f'{LOGGER_NAME}: Received sensor data for part {part}')
                    self.dataCallbacks[part](part, data)
                except Exception as e:
                    self.logger.error(f'{LOGGER_NAME}: Data callback for part {part} failed: {e.args[0]}')

        except Exception as e:
            self.logger.error(f'{LOGGER_NAME}: Failed parsing package {a}: {e.args[0]}')

    def send_message(self, partID: int, commandID: int):
        '''
        Sends the given message to the arduino and returns a future that will be
        completed if the command got processed. If the command did not get processed or
        the connection dies the future will throw
        '''

        future = Future()

        message, index = self.make_message(partID, commandID)

        self.command_futures[index] = future

        try:
            self.send_func(message)
        except Exception as e:
            self.logger.warning(f'{LOGGER_NAME}: Failed sending serial message: {e}')
            future.set_exception(e)

        return future
    
    def make_message(self, partID: int, commandID: int, pl: int = 0):
        '''
        Creates a command packet to be send to the arduino
        '''
        arr = bytearray(0 for x in range(3))

        arr[0] |= 1 << 7
        arr[0] |= partID
        arr[1] |= self.message_index
        arr[2] |= commandID << 4
        arr[2] |= pl

        message_index_used = self.message_index
        self.message_index = (self.message_index + 1) % 255 # Roll over

        return arr, message_index_used
    
    def update(self, t: float):
        
        if t > (self.last_future_swap + self.future_timeout):
            self.last_future_swap = t
            for f in self.swap_futures.values():
                if not f.done():
                    f.set_exception(TimeoutError('Sending message to arduino might have failed, no answer received'))
            
            self.swap_futures = self.command_futures
            self.command_futures = dict()

        if t > (self.last_keep_alive + self.keep_alive_interval):
            self.last_keep_alive = t
            self.logger.info(f'{LOGGER_NAME}: sending keep alive')
            future = self.send_message(0, 1)
            # future.add_done_callback(on_keep_alive_done)


class ArduinoHwBase(ABC):
    '''Base class for all arduino hw layer connections'''
    
    serial_adapter: ArduinoSerialAdapter


class ArduinoHwSelectable(Part, ABC):
    '''Base class for hw arduino interfaces that have selection options'''

    selected_device:  None | Task[str]

    device_name_list: None | Collection[str]

    @abstractmethod
    def try_connect_device_in_background(self, device_name: str):
        pass
