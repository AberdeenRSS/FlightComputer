from asyncio import Future
from datetime import timedelta
from typing import Iterable, Tuple, Type, Union
from uuid import UUID
from app.content.microcontroller.arduino_serial_common import ArduinoHwBase

from app.content.motor_commands.open import IgniteCommand
from app.content.microcontroller.arduino.parts.servo import ServoSensor
from app.logic.commands.command import Command
from app.content.microcontroller.arduino_serial import ArduinoOverSerial, make_default_command_callback
from app.logic.commands.command_helper import is_new_command
from app.logic.rocket_definition import Part, Rocket


class IgniterSensor(Part):
    type = 'Igniter'

    enabled: bool = True

    min_update_period = timedelta(milliseconds=100)

    min_measurement_period = timedelta(milliseconds=1000)

    arduino: ArduinoHwBase

    last_ignited: Union[float, None] = None

    triggered: bool

    commandList: dict

    partID: int = 2

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], arduino_parent: ArduinoHwBase, parachute: ServoSensor, start_enabled=True):
        self.arduino = arduino_parent
        
        self.enabled = start_enabled
        self.state = 'ready'
        super().__init__(_id, name, parent, list())  # type: ignore

        self.partID = 2
        self.commandList = { 'Ignite' : 0 }

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [IgniteCommand]

    def update(self, commands: Iterable[Command], now, iteration):
        for c in commands:
            if isinstance(c, IgniteCommand):

                if self.arduino is None:
                    c.state = 'failed'
                    c.response_message = 'No arduino connected'
                    continue

                if is_new_command(c):
                    future = self.arduino.serial_adapter.send_message(self.partID, self.commandList['Ignite'])
                    future.add_done_callback(make_default_command_callback(c))
                    self.last_ignited = now
                    c.state = 'processing'

            else:
                c.state = 'failed'  # Part cannot handle this command
                continue

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', '?'),
            ('Ignited', '?'),
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[Union[int, int]]]:
        return [[self.enabled, self.state]]
