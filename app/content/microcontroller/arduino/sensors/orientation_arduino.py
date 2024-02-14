from asyncio import Future, Task
from datetime import timedelta
import struct
from typing import Collection, Iterable, Tuple, Type, Union, cast
from uuid import UUID

from dataclasses import dataclass
from app.content.common_sensor_interfaces.orientation_sensor import IOrientationSensor
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.content.microcontroller.arduino_serial_common import ArduinoHwBase
from app.logic.commands.command import Command
from app.content.microcontroller.arduino_serial import ArduinoOverSerial
from app.logic.rocket_definition import Part, Rocket

class OrientationSensor(Part,  IOrientationSensor):
    type = 'Orientation'

    enabled: bool = True

    min_update_period = timedelta(milliseconds=20)

    min_measurement_period = timedelta(milliseconds=50)

    arduino: ArduinoHwBase

    w: float
    x: float
    y: float
    z: float
    calibrated: bool = False

    partID = 10

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], arduino_parent: ArduinoHwBase, start_enabled=True):
        self.arduino = arduino_parent
        self.enabled = start_enabled

        super().__init__(_id, name, parent, list())  # type: ignore

        self.x = self.y = self.z = 0.0
        self.arduino.serial_adapter.addDataCallback(self.partID, self.set_measurements)

    def set_measurements(self, part: int, data: bytearray):
        self.w = int.from_bytes(data[0:2], 'little', signed=True)/32767
        self.x = int.from_bytes(data[2:4], 'little', signed=True)/32767
        self.y = int.from_bytes(data[4:6], 'little', signed=True)/32767
        self.z = int.from_bytes(data[6:8], 'little', signed=True)/32767
        self.calibrated =  bool.from_bytes(data[8:9], 'little')

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [EnableCommand, DisableCommand]

    def update(self, commands: Iterable[Command], now, iteration):

        for c in commands:

            if isinstance(c, EnableCommand):
                self.enabled = True
                c.state = "success"

            elif isinstance(c, DisableCommand):
                self.enabled = False
                c.state = "success"

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('calibrated', int),
            ('W', float),
            ('X', float),
            ('Y', float),
            ('Z', float),
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[float]]:
        return [[1 if self.calibrated else 0, self.w, self.x, self.y, self.z]]

    def get_orientation(self):
        return (self.w, self.x, self.y, self.z)