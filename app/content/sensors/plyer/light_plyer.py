
from datetime import timedelta
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.rocket_definition import Command, Part, Rocket
from plyer import light
from plyer.facades.light import Light
from kivy import Logger

class PlyerLightSensor(Part):

    type = 'Sensor.Light'

    min_update_period = timedelta(milliseconds=10)
    min_measurement_period = timedelta(milliseconds=10)

    status_data_rate = 1_000

    enabled: bool = True

    sensor_failed: bool = False

    illumination: Union[float, None] = None

    iteration_illumination: Union[float, None] = None


    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled
        self.try_enable_light(self.enabled)

        super().__init__(_id, name, parent, list()) # type: ignore

    def try_enable_light(self, enable: bool) -> bool:
        try:
            as_light = cast(Light, light)
            if enable:
                as_light.enable()
            else:
                as_light.disable()
        except Exception as e:
            self.sensor_failed = True
            Logger.error(f'Plyer light sensor failed: {e}')
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
                as_light = cast(Light, light)
                self.iteration_illumination = self.illumination = as_light.illumination

            except Exception as e:
                Logger.error(f'Plyer light sensor failed: {e}')
                self.sensor_failed = True
        else:
            self.iteration_illumination = self.illumination = None
            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', '?'),
            ('sensor_failed', 'i'),
            ('illumination', 'f'),
        ]

    def collect_measurements(self, now, iteration) -> Union[None, Iterable[Iterable[Union[str, float, int, None]]]]:

        if iteration % self.status_data_rate > 0 and self.iteration_illumination is None:
            return

        return [[self.enabled, self.sensor_failed, self.iteration_illumination or 0]]
    
    def flush(self):
        self.iteration_illumination