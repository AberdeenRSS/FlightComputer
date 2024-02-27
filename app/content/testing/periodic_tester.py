from datetime import timedelta
from typing import Collection, Iterable, Sequence, Tuple, Type, Union
from uuid import UUID, uuid4
from app.content.microcontroller.arduino.parts.igniter import IgniterSensor
from app.content.microcontroller.arduino.parts.servo import ServoSensor
from app.content.microcontroller.arduino_serial_common import ArduinoHwBase
from app.content.motor_commands.open import CloseCommand, IgniteCommand, OpenCommand
from app.logic.commands.command import Command
from app.logic.commands.command_helper import is_completed_command
from app.logic.rocket_definition import Measurements, Part, Rocket


class PeriodicTester(Part):
    '''Triggers things periodically for testing'''

    type: str = 'Tester'

    min_update_period: timedelta = timedelta(milliseconds=100)

    min_measurement_period: timedelta = timedelta(milliseconds=100)

    last_ignite_command: None | IgniteCommand = None

    last_parachute_command: None | OpenCommand | CloseCommand = None

    last_ignite_command_time: float = 0

    last_parachute_command_time: float = 0

    last_ignite_success: None | int = None

    last_parachute_success: None | int = None

    ignite_period = 3

    parachute_period = 4

    def __init__(self, _id: UUID, name: str, rocket: Rocket, parachute: ServoSensor, igniter: IgniterSensor):
        super().__init__(_id, name, rocket, [])

        self.parachute = parachute
        self.igniter = igniter


    def update(self, commands: Iterable[Command], now: float, iteration: int) -> Union[None, Collection[Command]]:
        
        new_commands = list[Command]()

        self.last_ignite_success = None
        self.last_parachute_success = None

        if self.last_ignite_command is None or (is_completed_command(self.last_ignite_command) and now > self.last_ignite_command_time + self.ignite_period):

            if self.last_ignite_command is not None:
                self.last_ignite_success = 1 if self.last_ignite_command.state == 'success' else 0

            new_ignite = IgniteCommand()
            new_ignite._id = uuid4()
            new_ignite._part_id = self.igniter._id
            new_commands.append(new_ignite)

            self.last_ignite_command = new_ignite
            self.last_ignite_command_time = now
        
        if self.last_parachute_command is None or (is_completed_command(self.last_parachute_command) and now > self.last_parachute_command_time + self.parachute_period):

            if self.last_parachute_command is not None:
                self.last_parachute_success = 1 if self.last_parachute_command.state == 'success' else 0

            new_parachute_command = OpenCommand() if isinstance(self.last_parachute_command, CloseCommand) else CloseCommand()
            new_parachute_command._id = uuid4()
            new_parachute_command._part_id = self.parachute._id
            new_commands.append(new_parachute_command)

            self.last_parachute_command = new_parachute_command
            self.last_parachute_command_time = now

        return new_commands

    def get_measurement_shape(self) -> Collection[Tuple[str, Type]]:
        return [
            ('igniter-success', int),
            ('parachute-success', int),
            ]

    def get_accepted_commands(self) -> Iterable[Type[Command]]:
        return []

    def collect_measurements(self, now: float, iteration: int) -> Union[None, Sequence[Measurements]]:
        """Should give back all measurements obtained since the last tick"""
        return [[self.last_ignite_success, self.last_parachute_success]]

