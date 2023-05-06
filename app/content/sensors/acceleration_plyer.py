
from datetime import timedelta
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.rocket_definition import CommandBase, Part, Rocket
from plyer import accelerometer
from plyer.facades.accelerometer import Accelerometer


class PlyerAccelerationSensor(Part):

    type = 'Sensor.Acceleration'

    min_update_period = timedelta(milliseconds=1)

    min_measurement_period = timedelta(milliseconds=1)

    status_data_rate = 1000

    enabled: bool = True

    sensor_failed: bool = False

    acceleration: Union[None, Tuple[float, float, float]]

    iteration_acceleration: Union[None, Tuple[float, float, float]]

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled
        self.try_enable_accelerometer(self.enabled)

        super().__init__(_id, name, parent, list()) # type: ignore

    def get_accepted_commands(self) -> list[Type[CommandBase]]:
        return [EnableCommand, DisableCommand]
    
    def try_enable_accelerometer(self, enable: bool) -> bool:
        try:
            as_accelerometer = cast(Accelerometer, accelerometer)
            if enable:
                as_accelerometer.enable()
            else:
                as_accelerometer.disable()
        except Exception as e:
            self.sensor_failed = True
            print(f'Plyer acceleration sensor failed: {e}')
            return False
    
        return True
   
    def update(self, commands: Iterable[Command], now, iteration):
        
        for c in commands:
            if c is EnableCommand:
                self.enabled = True
                c.state = 'success' if self.try_enable_accelerometer(True) else 'failed'
            elif c is DisableCommand:
                self.enabled = False
                c.state = 'success' if self.try_enable_accelerometer(False) else 'failed'
            else:
                c.state = 'failed' # Part cannot handle this command
                continue
        
        if self.enabled and not self.sensor_failed:
            try:    
                as_accelerometer = cast(Accelerometer, accelerometer)
                self.iteration_acceleration = self.acceleration = as_accelerometer.get_acceleration()
            except Exception as e:
                print(f'Plyer acceleration sensor failed: {e}')
                self.sensor_failed = True
        else:
            self.iteration_acceleration = self.acceleration = None
            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', int),
            ('sensor_failed', int),
            ('acceleration-x', float),
            ('acceleration-y', float),
            ('acceleration-z', float),
        ]

    def collect_measurements(self, now, iteration) -> Union[None, Iterable[Iterable[Union[str, float, int, None]]]]:

        if iteration % self.status_data_rate > 0 and self.iteration_acceleration is None:
            return

        acc = self.iteration_acceleration or [None, None, None]
        return [[1 if self.enabled else 0, 1 if self.sensor_failed else 0, acc[0], acc[1], acc[2]]]
    
    def flush(self):
        self.iteration_acceleration = None
    
