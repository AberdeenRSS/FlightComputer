from typing import Iterable, Union, Collection, Tuple, Type, Sequence
from uuid import UUID

from app.logic.rocket_definition import Part, Rocket, Measurements
from app.models.command import Command
from barometric_altitude import BarometricAltitudeSensor

def calculate_velocity(altitude: float, previous_alt: float, t: float, previous_t: float):
    return (altitude - previous_alt) / (t - previous_t)

class Baromtric_vertical_velocity(Part):

    velocity: float or None = None  # m\s

    previous_alt: float or None = 0
    previous_time: float or None = 0

    def __init__(self, _id: UUID, name: str, rocket: Rocket, altitude_sensor: BarometricAltitudeSensor):
        super().__init__(_id, name, rocket, [])

        self.altitude_sensor: BarometricAltitudeSensor = altitude_sensor


    def update(self, commands: Iterable[Command], now: float, iteration: int) -> Union[None, Collection[Command]]:
        if self.altitude_sensor.altitude is None or now is None:
            return

        altitude = self.altitude_sensor.altitude

        self.velocity = calculate_velocity(altitude, self.previous_alt, now, self.previous_time)

        self.previous_time = now
        self.previous_alt = altitude


    def get_measurement_shape(self) -> Collection[Tuple[str, Type]]:
        return [
            ('velocity', float),
        ]

    def get_accepted_commands(self) -> Iterable[Type[Command]]:
        return []

    def collect_measurements(self, now: float, iteration: int) -> Union[None, Sequence[Measurements]]:
        """Should give back all measurements obtained since the last tick"""
        return [[self.velocity or -9999]]

