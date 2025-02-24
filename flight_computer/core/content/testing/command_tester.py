from datetime import timedelta
from typing import Collection, Iterable, Sequence, Tuple, Type, Union
from uuid import UUID, uuid4
from flight_computer.core.content.microcontroller.arduino.parts.igniter import IgniterSensor
from flight_computer.core.content.microcontroller.arduino.parts.servo import ServoSensor
from flight_computer.core.content.microcontroller.arduino_serial_common import ArduinoHwBase
from flight_computer.core.content.motor_commands.open import CloseCommand, IgniteCommand, OpenCommand
from flight_computer.core.logic.commands.command import Command
from flight_computer.core.logic.commands.command_helper import is_completed_command
from flight_computer.core.logic.rocket_definition import Measurements, Part, Rocket
from logging import _nameToLevel

class CommandTestPart(Part):
    '''Triggers things periodically for testing'''

    type: str = 'test.commands'

    min_update_period: timedelta = timedelta(milliseconds=10)

    min_measurement_period: timedelta = timedelta(milliseconds=10)

    def __init__(self, _id: UUID, name: str, rocket: Rocket):
        super().__init__(_id, name, rocket, [])


    def update(self, now: float, iteration: int) -> Union[None, Collection[Command]]:
        pass

    def on_string_command(self, timestamp: float, payload: str):

        self.submit_measurement(2, 'String command acknowledgement')

        self.log('Received string command')        

    def on_complex_command(self, timestamp: float, payload: tuple[str, bool]):

        self.submit_measurement(3, ('Command received', True))

        self.log('Complex msg received')

    def get_measurement_shape(self) -> Collection[Tuple[str, Type]]:
        return [
            *super().get_measurement_shape(),
            ('string-command-callback', 2, str),
            ('complex-payload-callback', 2, [('value-a', str), ('value-b', '?')])
            ]
    
    def get_command_callbacks(self):

        return [
            *super().get_command_callbacks(),
            self.on_string_command,
            self.on_complex_command
        ]

    def get_accepted_commands(self) -> Iterable[Type[Command]]:
        return [
            *super().get_accepted_commands(),
            ('string-payload-command', str),
            ('complex-payload', [('value-a', str), ('value-b', '?')])
        ]

    def collect_measurements(self, now: float, iteration: int) -> Union[None, Sequence[Measurements]]:
        """Should give back all measurements obtained since the last tick"""
        return 

