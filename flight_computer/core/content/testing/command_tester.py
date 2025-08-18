from datetime import timedelta
from typing import Collection, Iterable, Sequence, Tuple, Type, Union
from uuid import UUID
from flight_computer.core.logic.commands.command import Command
from flight_computer.core.logic.rocket_definition import Measurements, Part, Rocket

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

        self.submit_measurement_by_name('string-command-callback', 'String command acknowledgement')

        self.log(f'Received string command with payload: {payload}')        

    def on_complex_command(self, timestamp: float, payload: tuple[str, bool]):

        self.submit_measurement_by_name('complex-payload-callback', ('Command received', True))

        self.log('Complex msg received')

    def on_int_command(self, timestamp: float, payload: int):

        self.log(f'Received integer payload: {payload}')


    def make_measurement_shape(self):
        return [
            *super().make_measurement_shape(),
            ('string-command-callback', 2, str),
            ('complex-payload-callback', 2, [('value-a', str), ('value-b', '?')]),
            ]
    
    def make_command_callbacks(self):

        return [
            *super().make_command_callbacks(),
            self.on_string_command,
            self.on_complex_command,
            self.on_int_command
        ]

    def make_accepted_commands(self):
        return [
            *super().make_accepted_commands(),
            ('string-payload-command', str),
            ('complex-payload', [('value-a', str), ('value-b', '?')]),
            ('int-payload', 'i')
        ]

    def collect_measurements(self, now: float, iteration: int) -> Union[None, Sequence[Measurements]]:
        """Should give back all measurements obtained since the last tick"""
        return 

