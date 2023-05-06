
from typing import Iterable, Sequence, Tuple, Type, Union
from typing_extensions import Self
from uuid import UUID
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.rocket_definition import CommandBase, Measurements, Part, Rocket
from plyer.facades.battery import Battery
from random import random
from datetime import timedelta


class TemperatureSensor(Part):

    type = 'Sensor.Themperture'

    min_update_period = timedelta(milliseconds=10)

    min_measurement_period = timedelta(milliseconds=10)

    status_data_rate = 1_000

    enabled: bool = True

    sensor_failed: bool = False

    temperature: Union[None, float] = None

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):
        self.enabled = start_enabled
        super().__init__(_id, name, parent, list()) # type: ignore

    def update(self, commands: Iterable[Command], now):
        self.temperature = random()

    def get_accepted_commands(self) -> list[Type[CommandBase]]:
        return [EnableCommand, DisableCommand]

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        '''Commands that can be processed by this part'''
        return [
            ('enabled', int),
            ('sensor_failed', int),
            ('temperature', float),
        ]

    def collect_measurements(self, now) -> Iterable[Iterable[Union[str, float, int, None]]] :
        return [[1 if self.enabled else 0, 1 if self.sensor_failed else 0, self.temperature]]
