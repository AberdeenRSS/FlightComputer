from asyncio import Future, Task
import asyncio
from datetime import timedelta
import threading
from time import sleep
from typing import Callable, Collection, Iterable, Tuple, Type, Union
from uuid import UUID

from dataclasses import dataclass
from app.content.microcontroller.arduino_serial_common import ArduinoHwBase, ArduinoSerialAdapter, make_default_command_callback
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand, ResetCommand
from app.content.motor_commands.open import SetIgnitionPhaseCommand
from app.content.motor_commands.open import SetPreparationPhaseCommand

from app.logic.rocket_definition import Part, Rocket

from kivy.utils import platform
from kivy.logger import Logger, LOG_LEVELS


import tinyproto
from app.content.microcontroller.arduino.messages.messages import SensorData, ResponseMessage


if platform == 'android':
    from usb4a import usb
    from usbserial4a import serial4a
else:
    from serial.tools import list_ports
    from serial import Serial


class ArduinoOverSerial(Part, ArduinoHwBase):

    type = 'Microcontroller.Arduino.Serial'

    enabled: bool = True

    connected: bool = False

    min_update_period = timedelta(milliseconds=50)

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

    partID: int

    serial_adapter: ArduinoSerialAdapter

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):
        self.enabled = start_enabled
        super().__init__(_id, name, parent, list()) # type: ignore

        self.port_thread_lock = threading.Lock()

        self.hdlc = None

        self.serial_adapter = ArduinoSerialAdapter(self.send_message_hdlc)

        self.partID = 0
        self.commandList = { 'Reset' : 0, 'Preparation' : 1, 'Ignition' : 2, 'LiftOff' : 3 }


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

        hdlc.crc = 8
        hdlc.on_read = self.serial_adapter.on_read
        hdlc.begin()

        try:

            while True:

                if self.serial_port is None:
                    break

                if platform == 'android':
                    if not self.serial_port.isOpen(): # type: ignore
                        break
                else:
                    if not self.serial_port.is_open:
                        break

                with self.port_thread_lock:
                    received_msg = None
                    in_waiting = self.serial_port.in_waiting
                    if in_waiting > 0:
                        received_msg = self.serial_port.read(
                            in_waiting
                        )
                    
                if received_msg is not None and len(received_msg) > 0:
                    hdlc.rx(received_msg)

        except Exception as ex:
            
            Logger.error(f'crash read thread {ex}')
            raise ex
        finally:
            self.connected = False
            self.hdlc = None
            self.serial_port = None

            self.serial_adapter.flush_command_futures('Lost connection')

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [EnableCommand, DisableCommand, ResetCommand, SetPreparationPhaseCommand, SetIgnitionPhaseCommand]
    
    def send_message_hdlc(self, message: bytearray):
        if self.serial_port is None or self.hdlc is None:
            raise Exception('No serial device connected, message cannot be send')
        
        self.hdlc.put(message)
        self.serial_port.write(self.hdlc.tx())

    def update(self, commands: Iterable[Command], now, iteration):

        if self.connected:
            self.serial_adapter.update(now)

        for c in commands:

            if isinstance(c, EnableCommand):
                self.enabled = True
                c.state = "success"

            if isinstance(c, DisableCommand):
                self.enabled = False
                c.state = "success"

            if isinstance(c, ResetCommand):
                future = self.serial_adapter.send_message(self.partID, self.commandList['Reset'])
                future.add_done_callback(make_default_command_callback(c))
                c.state = "success"

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
    
