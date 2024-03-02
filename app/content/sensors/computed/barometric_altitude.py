from datetime import timedelta
import math
from typing import Collection, Iterable, Sequence, Tuple, Type, Union
from uuid import UUID
from app.content.common_sensor_interfaces.pressure import IPressureSensor
from app.content.common_sensor_interfaces.temperature import ITemperatureSensor
from app.logic.commands.command import Command
from app.logic.rocket_definition import Measurements, Part, Rocket

__ALTITUDE_EQ_EXPONENT__ = 1/5.257

def calculate_altitude(p_0: float, p: float, t: float):
    '''Source: https://physics.stackexchange.com/questions/333475/how-to-calculate-altitude-from-current-temperature-and-pressure'''

    return  ((math.pow(p_0/p, __ALTITUDE_EQ_EXPONENT__) - 1) * t) / 0.0065

class BarometricAltitudeSensor(Part):
    '''Triggers things periodically for testing'''

    type: str = 'Sensor.Altitude.Barometric'

    min_update_period: timedelta = timedelta(milliseconds=100)

    min_measurement_period: timedelta = timedelta(milliseconds=100)

    pressure_sea_level: float | None = None
    '''Pressure at sea level in Pascal'''

    altitude: float | None = None

    def __init__(self, _id: UUID, name: str, rocket: Rocket, pressure_sensor: IPressureSensor, temperature_sensor: ITemperatureSensor):
        super().__init__(_id, name, rocket, [])

        self.pressure_sensor = pressure_sensor
        self.temperature_sensor = temperature_sensor

    def update(self, commands: Iterable[Command], now: float, iteration: int) -> Union[None, Collection[Command]]:
        
        if self.pressure_sea_level is None:
            return

        pressure = self.pressure_sensor.get_pressure()
        temperature = self.temperature_sensor.get_temperature()

        if pressure is None or temperature is None:
            return

        self.altitude = calculate_altitude(self.pressure_sea_level, pressure, temperature)


    def get_measurement_shape(self) -> Collection[Tuple[str, Type]]:
        return [
            ('altitude', float),
            # ('pressure-sea-lvl', float),
            ]

    def get_accepted_commands(self) -> Iterable[Type[Command]]:
        return []

    def collect_measurements(self, now: float, iteration: int) -> Union[None, Sequence[Measurements]]:
        """Should give back all measurements obtained since the last tick"""
        return [[self.altitude]]

