
from typing import Iterable, Sequence, Tuple, Type, Union
from typing_extensions import Self
from uuid import UUID
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.rocket_definition import CommandBase, Measurements, Part, Rocket
from plyer.facades.battery import Battery
from random import random


class RandomSensor(Part):

    type = 'Sensor.Random'

    current_value = 0

    def __init__(self, _id: UUID, name: str, parent: Union[Self, Rocket, None]):
        super().__init__(_id, name, parent, list())

    def update(self, commands: Iterable[Command], now):
        self.current_value = random()

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        """Name and type of the measurement values of this part"""
        return [
            ('value', float)
        ]

    def get_accepted_commands(self) -> Iterable[Type[CommandBase]]:
        '''Commands that can be processed by this part'''
        return []

    def collect_measurements(self, now) -> Sequence[Measurements]:
        return [[self.current_value]]
