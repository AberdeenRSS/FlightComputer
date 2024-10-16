from asyncio import Future, Task
from datetime import timedelta
import struct
from time import time
from typing import Collection, Iterable, Tuple, Type, Union, cast
from uuid import UUID

from dataclasses import dataclass
from core.content.common_sensor_interfaces.data_age import IDataAge
from core.content.common_sensor_interfaces.orientation_sensor import IOrientationSensor
from core.content.common_sensor_interfaces.pressure import IPressureSensor
from core.content.common_sensor_interfaces.temperature import ITemperatureSensor
from core.content.general_commands.enable import DisableCommand, EnableCommand
from core.content.microcontroller.arduino_serial_common import ArduinoHwBase
from core.logic.commands.command import Command
from core.content.microcontroller.arduino_serial import ArduinoOverSerial
from core.logic.rocket_definition import Part, Rocket

class PressureArduinoSensor(Part, IDataAge, IPressureSensor, ITemperatureSensor):
    type = 'Pressure'

    enabled: bool = True

    min_update_period = timedelta(milliseconds=20)

    min_measurement_period = timedelta(milliseconds=50)

    arduino: ArduinoHwBase

    pressure: float | None = None

    temperature: float | None = None

    calibrated: bool = False

    last_data_received: float | None = None

    partID = 11

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], arduino_parent: ArduinoHwBase, start_enabled=True):
        self.arduino = arduino_parent
        self.enabled = start_enabled

        super().__init__(_id, name, parent, list())  # type: ignore

        self.arduino.serial_adapter.addDataCallback(self.partID, self.set_measurements)

    def set_measurements(self, part: int, data: bytearray):
        self.pressure = struct.unpack_from('<f', data[0:4])[0]
        self.temperature = struct.unpack_from('<f', data[4:8])[0]
        self.last_data_received = time()

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
            ('temperature', 'f'),
            ('pressure', 'f'),
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[float | None]]:
        return [[self.temperature or 0, self.pressure or 0]]
    
    def get_data_age(self):
        return self.last_data_received
    
    def get_pressure(self):
        return self.pressure # if self.pressure is not None else None # Convert to Pascal
    
    def get_temperature(self):
        return (self.temperature + 273.15) if self.temperature is not None else None # Convert to Kelvin
