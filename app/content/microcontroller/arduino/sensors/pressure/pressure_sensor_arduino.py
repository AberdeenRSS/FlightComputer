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

class PressureArduinoSensor(Part):
    type = 'Pressure'

    enabled: bool = True

    min_update_period = timedelta(milliseconds=20)

    min_measurement_period = timedelta(milliseconds=50)

    arduino: ArduinoHwBase

    pressure: float | None = None

    temperature: float | None = None

    calibrated: bool = False

    partID = 11

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], arduino_parent: ArduinoHwBase, start_enabled=True):
        self.arduino = arduino_parent
        self.enabled = start_enabled

        super().__init__(_id, name, parent, list())  # type: ignore

        self.arduino.serial_adapter.addDataCallback(self.partID, self.set_measurements)

    def set_measurements(self, part: int, data: bytearray):
        self.pressure = struct.unpack_from('<f', data[0:4])[0]
        self.temperature = struct.unpack_from('<f', data[4:8])[0]

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
            ('temperature', float),
            ('pressure', float),
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[float | None]]:
        return [[self.temperature, self.pressure]]
