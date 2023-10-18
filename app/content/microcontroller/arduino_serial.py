from asyncio import Future, Task
import asyncio
from datetime import timedelta
import threading
from typing import Collection, Iterable, Tuple, Type, Union, cast
from uuid import UUID

from dataclasses import dataclass
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.content.motor_commands.open import OpenCommand, CloseCommand, IgniteCommand
from app.logic.commands.command import Command, Command
from app.content.general_commands.enable import DisableCommand, EnableCommand, ResetCommand
from app.content.motor_commands.open import SetIgnitionPhaseCommand, SetLiftoffPhaseCommand, SetRecoveryPhaseCommand
from app.content.motor_commands.open import SetPreparationPhaseCommand

from app.logic.rocket_definition import Part, Rocket

from kivy.utils import platform

import tinyproto
from app.content.messages.response_message import ResponseM, ArduinoStateMessage, SensorDataMessage, ResponseMessage


from app.content.messages.smessages import AMessageList

if platform == 'android':
    from usb4a import usb
    from usbserial4a import serial4a
else:
    from serial.tools import list_ports
    from serial import Serial

@dataclass
class RssPacket:

    index: int

    command: int

    payload_size: int

    payload: bytes

    def to_bytes(self):
        return [*self.index.to_bytes(), *self.command.to_bytes(), *self.payload_size.to_bytes(), *self.payload]




class ArduinoSerial(Part):

    type = 'Microcontroller.Arduino.Serial'

    enabled: bool = True

    connected: bool = False

    min_update_period = timedelta(milliseconds=1000)

    min_measurement_period = timedelta(milliseconds=1000)

    device_name_list: Union[Collection[str], None] = None

    last_get_device_list_time: Union[float, None] = None

    get_device_list_period = 2.5
    '''2.5 s period to check for available devices automatically'''

    selected_device: Union[None, Task[str]] = None

    last_selected_device: Union[None, str] = None

    read_thread: Union[None, threading.Thread] = None

    read_thread_failure = False

    last_message = None

    serial_port = None

    hdlc: Union[tinyproto.Hdlc, None]

    current_message = bytearray([])

    expected_next_response_part: Union[int, None] = None

    expected_next_response_command: Union[int, None] = None

    response_future: Union[Future, None] = None

    logs = []

    part_activated: Union[bytes, None]
    part_state:     Union[str, None]

    commands_list = []

    messageList : AMessageList

    temperature : float

    lightValue : int

    launchPhase : str

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):
        self.part_state = None
        self.part_state = None

        self.enabled = start_enabled
        super().__init__(_id, name, parent, list()) # type: ignore

        self.port_thread_lock = threading.Lock()

        self.hdlc = None

        self.messageList = AMessageList(0x00)
        self.messageList.addCommandMessage('Reset', 0x00)
        self.messageList.addCommandMessage('Preparation', 0x01)
        self.messageList.addCommandMessage('Ignition', 0x02)
        self.messageList.addCommandMessage('Liftoff', 0x03)
        self.messageList.addCommandMessage('Recovery', 0x04)

        self.temperature = 0.0
        self.lightValue = 0
        self.launchPhase = 'Preparation'


    def try_get_device_list(self):
        if platform == 'android':
            usb_device_list = usb.get_usb_device_list()
            self.device_name_list = [
                device.getDeviceName() for device in usb_device_list
            ]
        else:
            usb_device_list = list_ports.comports()
            self.device_name_list = [port.device for port in usb_device_list]


    def try_connect_device_in_background(self, device_name: str):

        # Only one connect at a time
        if self.selected_device is not None and not self.selected_device.done():
            return

        self.selected_device = asyncio.get_event_loop().create_task(self.try_connect_device(device_name))

    def try_connect_last_device_background(self):

        if self.last_selected_device is None:
            return
        
        if self.connected:
            return

        if self.selected_device is None:
            return
        
        if not self.selected_device.done():
            return
        
        if (self.device_name_list is None) or (self.last_selected_device not in self.device_name_list):
            return
        
        self.try_connect_device_in_background(self.last_selected_device)

        

    async def try_connect_device(self, device_name: str) -> str:

        # Hack to have this running the background
        await asyncio.sleep(0.01)

        self.connected = False

        if platform == 'android':
            device = usb.get_usb_device(device_name)
            if not device:
                raise Exception(
                    f"Device {device_name} not present!"
                )
            if not usb.has_usb_permission(device):
                usb.request_usb_permission(device)
                raise Exception('Permission not yet granted, try again')
            self.serial_port = serial4a.get_serial_port(
                device_name,
                9600,
                8,
                'N',
                1,
                timeout=1
            )
        else:
            self.serial_port = Serial(
                device_name,
                9600,
                8,
                'N',
                1,
                timeout=1
            )

        if self.serial_port.closed:
            self.connected = False
            return device_name
        
        self.connected = True
        self.last_selected_device = device_name

        if self.serial_port.is_open and (not self.read_thread or not self.read_thread.is_alive()):
            self.read_thread = threading.Thread(target = self.read_msg_thread)
            self.read_thread.start()
        
        return device_name

    def read_msg_thread(self):

        hdlc = tinyproto.Hdlc()

        self.hdlc = hdlc

        def on_read(b: bytes):


            if len(b) < 3:
                print('skip')
                return

            payload_size = int(b[2])

            payload = b[3:-1] if payload_size > 0 else bytes()

            package = RssPacket(int(b[0]), int(b[1]), payload_size, payload)

            #print(package)

            self.last_message = package


        message =  ResponseMessage()

        hdlc.on_read = on_read
        hdlc.crc = 8
        hdlc.begin()



        try:

            while True:
                #print(self.logs)
                    with self.port_thread_lock:
                        if not self.serial_port.is_open:
                            break
                        received_msg = self.serial_port.read(
                            self.serial_port.in_waiting
                        )
                    if received_msg:
                        response = message.parse(received_msg)
                        if response:
                            self.action(response)

        except Exception as ex:
            self.connected = False
            self.hdlc = None
            self.serial_port = None
            if self.response_future is not None and not self.response_future.done():
                self.response_future.set_exception(Exception('Lost connection to arduino'))
            print(f'crash read thread {ex.args[0]}')
            raise ex


    def action(self, response):

        if isinstance(response, ResponseM):
            self.part_state = 'success'

            if self.response_future is None or self.response_future.done():
                return

            result = response.get_result()
            if result == 'Success':
                self.response_future.set_result(result)
            else:
                self.response_future.set_exception(Exception(result))

        elif isinstance(response, SensorDataMessage):
            if response.partCode == 0x50:
                self.temperature = response.get_data()
            elif response.partCode == 0x52:
                self.lightValue = int(response.get_data())

        elif isinstance(response, ArduinoStateMessage):
            self.send_message_hdlc(self.messageList[self.launchPhase])


    def get_accepted_commands(self) -> list[Type[Command]]:
        return [EnableCommand, DisableCommand, ResetCommand, SetPreparationPhaseCommand, SetIgnitionPhaseCommand, SetLiftoffPhaseCommand, SetRecoveryPhaseCommand]
    
    def send_message_hdlc(self, message: bytearray):
        if self.serial_port is None or self.hdlc is None:
            raise Exception('No serial device connected, message cannot be send')
        
        self.hdlc.put(message)
        self.serial_port.write(self.hdlc.tx())

    def send_message(self, message : bytearray):
        '''Sends the given message to the arduino and returns a future that will be
        completed if the command got processed. If the command did not get processed or
        the connection dies the future will throw'''

        if self.response_future is not None and not self.response_future.done():
            self.response_future.set_exception(Exception('Another message was send before the arduino could process the last message'))

        future = asyncio.Future()
        self.response_future = future

        try:
            self.send_message_hdlc(message)
        except Exception as e:
            future.set_exception(e)

        return future


    def update(self, commands: Iterable[Command], now, iteration):

        for c in commands:

            if c.state == 'processing' and self.last_command != c:
                c.state = 'failed'
                c.response_message = 'Another ignite command was send, this command will no longer be processed'
                continue

            if c.state == 'processing' and self.last_ignite_future is not None and self.last_ignite_future.done():
                exception = self.last_ignite_future.exception()
                if exception is not None:
                    c.state = 'failed'
                    c.response_message = exception.args[0]
                    continue

                if self.last_ignite_future.result() == "Success":
                    c.state = 'success'
                    c.response_message = 'success'

                    if isinstance(c, SetIgnitionPhaseCommand):
                        self.launchPhase = 'Ignition'
                    elif isinstance(c, SetPreparationPhaseCommand):
                        self.launchPhase = 'Preparation'


            if isinstance(c, EnableCommand):
                self.enabled = True
                c.state = "success"
            elif isinstance(c, DisableCommand):
                self.enabled = False
                c.state = "success"

            elif isinstance(c, ResetCommand):
                self.send_message(self.messageList['Reset'])
                c.state = "success"

            elif isinstance(c, SetPreparationPhaseCommand):
                if c.state == 'received':
                    self.last_command = c
                    self.last_ignite_future = self.send_message(self.messageList['Preparation'])
                    c.state = 'processing'


            elif isinstance(c, SetIgnitionPhaseCommand):
                if c.state == 'received':
                    self.last_command = c
                    self.last_ignite_future = self.send_message(self.messageList['Ignition'])
                    c.state = 'processing'

            else:
                c.state = 'failed' # Part cannot handle this command
                continue

        if self.connected:
            return
        
        if self.last_get_device_list_time is not None and (now - self.last_get_device_list_time) < self.get_device_list_period:
            return

        self.try_get_device_list()
        self.try_connect_last_device_background()
        self.last_get_device_list_time = now

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', int),
            ('available_devices', int),
            ('connected', int),
            ('failed_connection', int),
            ('last_index', int)
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[Union[str, float, int, None]]]:

        last_index = self.last_message.index if self.last_message is not None else -1

        num_devices = len(self.device_name_list) if self.device_name_list is not None else -1

        return [[1 if self.enabled else 0, num_devices, self.connected, 1 if self.read_thread_failure else 0, last_index]]
    
