from asyncio import Future, Task
from datetime import timedelta
from typing import Collection, Iterable, Tuple, Type, Union, cast
from uuid import UUID

from dataclasses import dataclass
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.commands.command import Command
from app.logic.rocket_definition import Part, Rocket


class PressureSensor(Part):
    type = 'Pressure'

    enabled: bool = True

    min_update_period = timedelta(milliseconds=20)

    min_measurement_period = timedelta(milliseconds=1000)

    pressure : float

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled=True):
        self.enabled = start_enabled

        super().__init__(_id, name, parent, list())  # type: ignore

        self.pressure = 0.0


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
            ('pressure', float),
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[float]]:
        return [[self.pressure]]

