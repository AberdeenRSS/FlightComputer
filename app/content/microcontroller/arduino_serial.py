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

from app.logic.rocket_definition import Part, Rocket

from kivy.utils import platform

import tinyproto

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

    min_update_period = timedelta(milliseconds=1000)

    min_measurement_period = timedelta(milliseconds=1000)

    device_name_list: Union[Collection[str], None] = None

    selected_device: Union[None, Task[str]] = None

    read_thread: Union[None, threading.Thread] = None

    read_thread_failure = False

    last_message = None

    serial_port = None

    hdlc: Union[tinyproto.Hdlc, None]

    current_message = bytearray([])

    logs = []

    part_activated: Union[bytes, None]
    part_state:     Union[str, None]

    commands_list = []


    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):
        self.part_state = None
        self.part_state = None

        self.enabled = start_enabled
        super().__init__(_id, name, parent, list()) # type: ignore

        self.port_thread_lock = threading.Lock()

        self.try_get_device_list()
        self.hdlc = None



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
        self.selected_device = asyncio.get_event_loop().create_task(self.try_connect_device(device_name))

    async def try_connect_device(self, device_name: str) -> str:

        # Hack to have this running the background
        await asyncio.sleep(0.1)

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

        
        if self.serial_port.is_open and not self.read_thread:
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

        hdlc.on_read = on_read
        hdlc.crc = 8
        hdlc.begin()

        while True:
            #print(self.logs)
            try:
                with self.port_thread_lock:
                    if not self.serial_port.is_open:
                        break
                    received_msg = self.serial_port.read(
                        self.serial_port.in_waiting
                    )
                if received_msg:
                    print(received_msg)
#                   hdlc.rx(received_msg)


                    for i in received_msg:
                        if len(self.current_message) and self.current_message[-1] is not 0x7E and i is 0x7E:
                            self.current_message.append(i)
                            self.logs.append(self.current_message)
                            self.parse()
                            self.current_message = bytearray([])
                        else:
                            self.current_message.append(i)


            except Exception as ex:
                print(f'crash read thread {ex.args[0]}')
                raise ex

    def parse(self):
        print("Self - ", self.current_message)
        self.part_activated = self.current_message[3]
        if self.current_message[5] is 0x01:
            self.part_state = 'success'
        else:
            self.part_state = 'failed'
        print()

    def hz(self, part) -> Union[str, None]:
        if self.part_activated is part:
            state = self.part_state
            self.part_state = None
            self.part_activated = None
            return state

        return None

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [EnableCommand, DisableCommand, ResetCommand]

    def send_message(self, message :bytearray()) -> int:
        if message[3] is 0x02 and message[4] is 0x01:
            def kek():  # user defined function which adds +10 to given number
                self.send_message(bytearray([0x7E, 0xFF, 0x4F, 0x01, 0x04, 0x7E]))

            start_time = threading.Timer(35, kek)
            start_time.start()

        if self.serial_port is None or self.hdlc is None:
            return

        self.hdlc.put(message)
        self.serial_port.write(self.hdlc.tx())

        self.commands_list.append(bytearray([0x7E, 0xFF, 0x4F, 0x01, 0x04, 0x7E]))
        return len(self.commands_list)


    def update(self, commands: Iterable[Command], now, iteration):

        for c in commands:

            if isinstance(c, EnableCommand):
                self.enabled = True
                c.state = "success"
            elif isinstance(c, DisableCommand):
                self.enabled = False
                c.state = "success"
            elif isinstance(c, ResetCommand):
                self.send_message(bytearray([0x7E, 0xFF, 0x4F, 0x00, 0x01, 0x7E]))
                c.state = "success"
            else:
                c.state = 'failed' # Part cannot handle this command
                continue

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', int),
            ('open', int),
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[Union[str, float, int, None]]]:

        last_index = self.last_message.index if self.last_message is not None else -1

        return [[1 if self.enabled else 0, 1 if self.read_thread_failure else 0, last_index]]
    
