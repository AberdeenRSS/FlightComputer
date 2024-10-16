
from datetime import timedelta
from logging import getLogger
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from core.logic.commands.command import Command
from core.content.general_commands.enable import DisableCommand, EnableCommand
from core.logic.rocket_definition import Command, Part, Rocket
from plyer import barometer
from plyer.facades.barometer import Barometer


class PlyerBarometerSensor(Part):

    type = 'Sensor.Barometer'

    min_update_period = timedelta(milliseconds=10)

    min_measurement_period = timedelta(milliseconds=10)

    status_data_rate = 1_000

    enabled: bool = True

    sensor_failed: bool = False

    pressure_value: Union[float, None] = None

    iteration_pressure_value: Union[float, None] = None

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled
        self.try_enable_barometer(self.enabled)

        self.logger = getLogger('Barmometer Plyer')

        super().__init__(_id, name, parent, list()) # type: ignore

    def try_enable_barometer(self, enable: bool) -> bool:
        try:
            as_barometer = cast(Barometer, barometer)
            if enable:
                as_barometer.enable()
            else:
                as_barometer.disable()
        except Exception as e:
            self.sensor_failed = True
            self.logger.error(f'Plyer barometer sensor failed: {e}')
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
                as_barometer = cast(Barometer, barometer)
                self.iteration_pressure_value = self.pressure_value = as_barometer.pressure

            except Exception as e:
                self.logger.error(f'Plyer barometer sensor failed: {e}')
                self.sensor_failed = True
        else:
            self.iteration_pressure_value = self.pressure_value = None
            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', '?'),
            ('sensor_failed', '?'),
            ('pressure_value', 'f'),
        ]

    def collect_measurements(self, now, iteration) -> Union[None, Iterable[Iterable[Union[str, float, int, None]]]]:

        if iteration % self.status_data_rate > 0 and self.iteration_pressure_value is None:
            return

        return [[self.enabled, self.sensor_failed, self.iteration_pressure_value or -9999]]
    
    def flush(self):
        self.iteration_pressure_value = None
