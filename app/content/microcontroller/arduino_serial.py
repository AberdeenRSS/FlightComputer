from asyncio import Future, Task
import asyncio
from datetime import timedelta
import threading
from typing import Collection, Iterable, Tuple, Type, Union, cast
from uuid import UUID

from dataclasses import dataclass
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.commands.command import Command, CommandBase

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


class ArduinoSerial(Part):

    type = 'Microcontroller.Arduino.Serial'

    enabled: bool = True

    min_update_period = timedelta(milliseconds=1)

    min_measurement_period = timedelta(milliseconds=1)

    device_name_list: Union[Collection[str], None] = None

    selected_device: Union[None, Task[str]] = None

    read_thread: Union[None, threading.Thread] = None

    read_thread_failure = False

    last_message = None

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled
        super().__init__(_id, name, parent, list()) # type: ignore

        self.port_thread_lock = threading.Lock()

        self.try_get_device_list()



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

        def on_read(b: bytes):

            if len(b) < 3:
                print('skip')
                return

            payload_size = int(b[2])

            payload = b[3:-1] if payload_size > 0 else bytes()

            package = RssPacket(int(b[0]), int(b[1]), payload_size, payload)

            self.last_message = package

        hdlc.on_read = on_read
        hdlc.crc = 8
        hdlc.begin()

        while True:
            try:
                with self.port_thread_lock:
                    if not self.serial_port.is_open:
                        break
                    received_msg = self.serial_port.read(
                        self.serial_port.in_waiting
                    )
                if received_msg:
                    hdlc.rx(received_msg)
            except Exception as ex:
                print(f'crash read thread {ex.args[0]}')
                raise ex

    def get_accepted_commands(self) -> list[Type[CommandBase]]:
        return [EnableCommand, DisableCommand]
   
    def update(self, commands: Iterable[Command], now, iteration):
        
        for c in commands:
            if c is EnableCommand:
                self.enabled = True
            elif c is DisableCommand:
                self.enabled = False
            else:
                c.state = 'failed' # Part cannot handle this command
                continue
            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', int),
            ('communication_failure', int),
            ('last_packet_index', int)
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[Union[str, float, int, None]]]:

        last_index = self.last_message.index if self.last_message is not None else -1

        return [[1 if self.enabled else 0, 1 if self.read_thread_failure else 0, last_index]]
    
