from asyncio import Future, Task
from datetime import timedelta
from typing import Collection, Iterable, Tuple, Type, Union, cast
from uuid import UUID

from dataclasses import dataclass
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.content.motor_commands.open import OpenCommand, CloseCommand, IgniteCommand
from app.logic.commands.command import Command, Command
from app.content.general_commands.enable import DisableCommand, EnableCommand, ResetCommand
from app.content.microcontroller.arduino_serial import ArduinoSerial
from app.logic.rocket_definition import Part, Rocket

from kivy.utils import platform

from app.content.messages.smessages import AMessageList

class TemperatureSensor(Part):
    type = 'Temperature'

    enabled: bool = True

    min_update_period = timedelta(milliseconds=20)

    min_measurement_period = timedelta(milliseconds=1000)

    arduino: Union[ArduinoSerial, None]


    last_ignite_future: Union[Future, None] = None

    last_command: Union[None, Command] = None

    temperature : float

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], arduino_parent: Union[ArduinoSerial, None],start_enabled=True):
        self.arduino = arduino_parent
        self.enabled = start_enabled

        super().__init__(_id, name, parent, list())  # type: ignore

        self.temperature = 0.0


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

        self.temperature = self.arduino.temperature

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('temperature', float),
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[float]]:
        return [[self.temperature]]

