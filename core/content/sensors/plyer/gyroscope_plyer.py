
from datetime import timedelta
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from core.logic.commands.command import Command
from core.content.general_commands.enable import DisableCommand, EnableCommand
from core.logic.rocket_definition import Command, Part, Rocket
from plyer import gyroscope
from plyer.facades.gyroscope import Gyroscope
from kivy import Logger


class PlyerGyroscopeSensor(Part):

    type = 'Sensor.Gyroscope'

    min_update_period = timedelta(milliseconds=10)
    min_measurement_period = timedelta(milliseconds=10)

    status_data_rate = 1_000

    enabled: bool = True

    sensor_failed: bool = False

    rotation: Union[None, Tuple[float, float, float]] = None

    iteration_rotation: Union[None, Tuple[float, float, float]] = None

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled

        self.try_enable_gyroscope(self.enabled)

        super().__init__(_id, name, parent, list()) # type: ignore

    def try_enable_gyroscope(self, enable: bool) -> bool:
        try:
            as_gyroscope = cast(Gyroscope, gyroscope)
            if enable:
                as_gyroscope.enable()
            else:
                as_gyroscope.disable()
        except Exception as e:
            self.sensor_failed = True
            Logger.error(f'Plyer gyroscope sensor failed: {e}')
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
                as_gyroscope = cast(Gyroscope, gyroscope)
                self.iteration_rotation = self.rotation = as_gyroscope.rotation

            except Exception as e:
                Logger.error(f'Plyer gyroscope sensor failed: {e}')
                self.sensor_failed = True
        else:
            self.iteration_rotation = self.rotation = None
            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', '?'),
            ('sensor_failed', '?'),
            ('rotation-x', 'f'),
            ('rotation-y', 'f'),
            ('rotation-z', 'f'),
        ]

    def collect_measurements(self, now, iteration) -> Union[None, Iterable[Iterable[Union[str, float, int, None]]]]:

        if iteration % self.status_data_rate > 0 and self.iteration_rotation is None:
            return

        rot =  self.iteration_rotation or [0, 0, 0]
        return [[self.enabled, self.sensor_failed, rot[0], rot[1], rot[2]]]
    
    def flush(self):
        self.iteration_rotation = None