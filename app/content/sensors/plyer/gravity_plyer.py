
from datetime import timedelta
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.rocket_definition import Command, Part, Rocket
from plyer import gravity
from plyer.facades.gravity import Gravity
from kivy import Logger

class PlyerGravitySensor(Part):

    type = 'Sensor.Gravity'

    min_update_period = timedelta(milliseconds=100)

    min_measurement_period = timedelta(milliseconds=100)

    status_data_rate = 1_000

    enabled: bool = True

    sensor_failed: bool = False

    gravity_value: Union[None, Tuple[float, float, float]]

    iteration_gravity_value: Union[None, Tuple[float, float, float]]

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled
        self.try_enable_gravity(self.enabled)

        super().__init__(_id, name, parent, list()) # type: ignore

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [EnableCommand, DisableCommand]
    
    def try_enable_gravity(self, enable: bool) -> bool:
        try:
            as_gravity = cast(Gravity, gravity)
            if enable:
                as_gravity.enable()
            else:
                as_gravity.disable()
        except Exception as e:
            self.sensor_failed = True
            Logger.error(f'Plyer gravity sensor failed: {e}')
            return False
    
        return True
   
    def update(self, commands: Iterable[Command], now, iteration):
        
        for c in commands:
            if c is EnableCommand:
                self.enabled = True
                c.state = 'success' if self.try_enable_gravity(True) else 'failed'
            elif c is DisableCommand:
                self.enabled = False
                c.state = 'success' if self.try_enable_gravity(False) else 'failed'
            else:
                c.state = 'failed' # Part cannot handle this command
                continue
            
        if self.enabled and not self.sensor_failed:
            try:    
                as_gravity = cast(Gravity, gravity)
                self.iteration_gravity_value = self.gravity_value = as_gravity.gravity
            except Exception as e:
                Logger.error(f'Plyer gravity sensor failed: {e}')
                self.sensor_failed = True
        else:
            self.iteration_gravity_value = self.gravity_value = None
            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', '?'),
            ('sensor_failed', '?'),
            ('gravity-x', 'f'),
            ('gravity-y', 'f'),
            ('gravity-z', 'f'),
        ]

    def collect_measurements(self, now, iteration) -> Union[None, Iterable[Iterable[Union[str, float, int, None]]]]:

        if iteration % self.status_data_rate > 0 and self.iteration_gravity_value is None:
            return

        grav =  self.iteration_gravity_value or [0, 0, 0]
        return [[self.enabled, self.sensor_failed, grav[0], grav[1], grav[2]]]
    
    def flush(self):
        self.iteration_gravity_value = None
        
