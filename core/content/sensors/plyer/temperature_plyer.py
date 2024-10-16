
from datetime import timedelta
from logging import getLogger
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from core.logic.commands.command import Command
from core.content.general_commands.enable import DisableCommand, EnableCommand
from core.logic.rocket_definition import Command, Part, Rocket
from plyer import temperature
from plyer.facades.temperature import Temperature


class PlyerTemperatureSensor(Part):

    type = 'Sensor.Temperature'

    min_update_period = timedelta(milliseconds=10)
    min_measurement_period = timedelta(milliseconds=10)

    status_data_rate = 1_000

    enabled: bool = True

    sensor_failed: bool = False

    temperature_value: Union[float, None] = None

    iteration_temperature_value: Union[float, None] = None


    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled
        self.logger = getLogger('Barmometer Plyer')

        self.try_enable_temperature(self.enabled)

        super().__init__(_id, name, parent, list()) # type: ignore

    def try_enable_temperature(self, enable: bool) -> bool:
        try:
            as_temperature = cast(Temperature, temperature)
            if enable:
                as_temperature.enable()
            else:
                as_temperature.disable()
        except Exception as e:
            self.sensor_failed = True
            self.logger.error(f'Plyer temperature sensor failed: {e}')
            return False
    
        return True

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [EnableCommand, DisableCommand]
   
    def update(self, commands: Iterable[Command], now, iteration):
        
        for c in commands:
            if c is EnableCommand:
                self.enabled = True
            elif c is DisableCommand:
                self.enabled = False
            else:
                c.state = 'failed' # Part cannot handle this command
                continue
            
            c.state = 'success'
        
        if self.enabled and not self.sensor_failed:
            try:    
                as_temperature = cast(Temperature, temperature)
                self.iteration_temperature_value = self.temperature_value = as_temperature.temperature

            except Exception as e:
                self.logger.error(f'Plyer temperature sensor failed: {e}')
                self.sensor_failed = True
        else:
            self.iteration_temperature_value = self.temperature_value = None
            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', '?'),
            ('sensor_failed', '?'),
            ('temperature', 'f'),
        ]

    def collect_measurements(self, now, iteration) -> Union[None, Iterable[Iterable[Union[str, float, int, None]]]]:

        if iteration % self.status_data_rate > 0 and self.iteration_temperature_value is None:
            return

        return [[self.enabled, self.sensor_failed, self.iteration_temperature_value]]
    
    def flush(self):
        self.iteration_temperature_value = None
