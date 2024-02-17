from asyncio import Future, Task
import asyncio
from datetime import timedelta
import threading
from time import sleep
from typing import Callable, Collection, Iterable, Tuple, Type, Union
from uuid import UUID

from dataclasses import dataclass
from app.content.microcontroller.arduino_serial_common import ArduinoHwBase, ArduinoHwSelectable, ArduinoSerialAdapter, make_default_command_callback
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand, ResetCommand
from app.content.motor_commands.open import SetIgnitionPhaseCommand
from app.content.motor_commands.open import SetPreparationPhaseCommand

from app.logic.rocket_definition import Part, Rocket

from kivy.utils import platform
from kivy.logger import Logger, LOG_LEVELS


import tinyproto


if platform == 'android':
    from jnius import autoclass
    from android.permissions import request_permissions, Permission

    BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
    BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
    BluetoothSocket = autoclass('android.bluetooth.BluetoothSocket')
    JavaUUID = autoclass('java.util.UUID')


class ArduinoOverBluetooth(ArduinoHwSelectable, ArduinoHwBase):

    type = 'Microcontroller.Arduino.Bluetooth'

    enabled: bool = True

    connected: bool = False

    min_update_period = timedelta(milliseconds=200)

    min_measurement_period = timedelta(milliseconds=1000)

    device_name_list: Collection[str] | None = None

    last_get_device_list_time: Union[float, None] = None

    get_device_list_period = 2.5
    '''2.5s period to check for available devices automatically'''

    selected_device: Union[None, Task[str]] = None

    last_selected_device: Union[None, str] = None

    read_thread: Union[None, threading.Thread] = None

    read_thread_failure = False

    last_message = None

    socket = None

    hdlc: Union[tinyproto.Hdlc, None]

    partID: int

    commandList: dict

    serial_adapter: ArduinoSerialAdapter

    read_buffer: bytearray

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):
        self.enabled = start_enabled
        super().__init__(_id, name, parent, list()) # type: ignore

        self.port_thread_lock = threading.Lock()

        self.read_buffer = bytearray(1024)

        self.hdlc = None

        self.partID = 0
        self.commandList = { 'Reset' : 0, 'Preparation' : 1, 'Ignition' : 2, 'LiftOff' : 3 }

        if platform != 'android':
            raise NotImplementedError(f'Arduino over Bluetooth unavailable on {platform}')
        
        self.serial_adapter = ArduinoSerialAdapter(self.send_message_hdlc)

        # Request the android permission so that the app gets bluetooth access
        request_permissions([Permission.BLUETOOTH, Permission.BLUETOOTH_ADMIN, Permission.BLUETOOTH_CONNECT])

    def try_get_device_list(self):
        paired_devices = BluetoothAdapter.getDefaultAdapter().getBondedDevices().toArray()
        self.device_name_list = [d.getName() for d in paired_devices]

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

        paired_devices = BluetoothAdapter.getDefaultAdapter().getBondedDevices().toArray()
        self.socket = None
        for device in paired_devices:
            if device.getName() == device_name:
                self.socket = device.createInsecureRfcommSocketToServiceRecord(
                    JavaUUID.fromString("00001101-0000-1000-8000-00805F9B34FB"))
                break

        if self.socket is None:
            raise Exception(f'Device {device_name} no longer connected')
        
        try:
            self.socket.connect()
        except Exception as e:
            self.connected = False
            self.socket = None
            raise e
        
        if not self.socket.isConnected():
            self.connected = False
            self.socket = None
            raise Exception('Connection lost')
        
        if self.read_thread is not None and self.read_thread.is_alive():
            self.connected = False
            self.socket = None
            raise Exception('Old connection still established')
        
        self.connected = True
        self.last_selected_device = device_name

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

            if self.socket is None:
                raise Exception('Not connected')

            recv_stream = self.socket.getInputStream()


            while True:

                if self.socket is None:
                    break

                if not self.socket.isConnected(): # type: ignore
                    break

                with self.port_thread_lock:
                    received_msg = None
                    read_bytes = recv_stream.read(self.read_buffer)
                    if read_bytes > 0:
                        received_msg = bytearray(self.read_buffer[0:read_bytes])
                    
                if received_msg is not None and len(received_msg) > 0:
                    hdlc.rx(received_msg)

        except Exception as ex:
            Logger.error(f'crash read thread: {ex}')
            raise ex
        finally:

            # Close the socket if possible
            if self.socket is not None:
                self.socket.close()

            self.connected = False
            self.hdlc = None
            self.socket = None

            self.serial_adapter.flush_command_futures('Lost connection')

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [EnableCommand, DisableCommand, ResetCommand, SetPreparationPhaseCommand, SetIgnitionPhaseCommand]
    
    def send_message_hdlc(self, message: bytearray):
        if self.socket is None or self.hdlc is None or not self.socket.isConnected():
            raise Exception('No serial device connected, message cannot be send')
        
        output_stream = self.socket.getOutputStream()
        
        self.hdlc.put(message)
        output_stream.write(self.hdlc.tx())


    def update(self, commands: Iterable[Command], now, iteration):

        if self.connected:
            self.serial_adapter.update(now)

        for c in commands:

            # if c.state == 'processing' and self. != c:
            #     c.state = 'failed'
            #     c.response_message = 'Another ignite command was send, this command will no longer be processed'
            #     continue

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
    
