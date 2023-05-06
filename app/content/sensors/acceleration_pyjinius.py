from time import sleep
from datetime import timedelta
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.rocket_definition import CommandBase, Part, Rocket
from kivy.utils import platform

if platform == 'android':
    # from android.permissions import request_permissions, Permission
    from jnius import autoclass


class PyjiniusAccelerationSensor(Part):

    type = 'Sensor.Acceleration'

    min_update_period = timedelta(milliseconds=10)

    min_measurement_period = timedelta(milliseconds=10)

    status_data_rate = 1_000

    enabled: bool = True

    sensor_failed: bool = False

    acceleration: Union[None, Tuple[float, float, float]]

    accuracy: Union[int, None] = None

    iteration_acceleration: Union[None, list[Tuple[float, float, float]]]

    iteration_accuracy: Union[int, None] = None

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled
        self.try_enable(self.enabled)

        super().__init__(_id, name, parent, list()) # type: ignore

    def get_accepted_commands(self) -> list[Type[CommandBase]]:
        return [EnableCommand, DisableCommand]
    
    def try_enable(self, enable: bool) -> bool:
        try:
            self.hardware = autoclass('org.rss.Accelerometer')
            self.hardware.accelerometerEnable(enable)
        except Exception as e:
            self.sensor_failed = True
            print(f'Plyer gravity sensor failed: {e}')
            return False
    
        return True
   
    def update(self, commands: Iterable[Command], now, iteration):
        
        for c in commands:
            if c is EnableCommand:
                self.enabled = True
                c.state = 'success' if self.try_enable(True) else 'failed'
            elif c is DisableCommand:
                self.enabled = False
                c.state = 'success' if self.try_enable(False) else 'failed'
            else:
                c.state = 'failed' # Part cannot handle this command
                continue
            
        if self.enabled and not self.sensor_failed:
            try:    
                last_events = self.hardware.lastEvents
                self.hardware.flush()
                last_accuracy = self.hardware.lastAccuracy
                if len(last_events) > 0:
                    self.iteration_acceleration = [x.values for x in last_events]
                    self.acceleration = self.iteration_acceleration[-1]
                if last_accuracy:
                    self.accuracy = self.iteration_accuracy = last_accuracy
            except Exception as e:
                print(f'Plyer gravity sensor failed: {e}')
                self.sensor_failed = True
        else:
            self.iteration_acceleration = self.acceleration = None
            self.iteration_accuracy = self.accuracy = None
            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', int),
            ('sensor_failed', int),
            ('accuracy', int),
            ('acceleration-x', float),
            ('acceleration-y', float),
            ('acceleration-z', float),
        ]

    def collect_measurements(self, now, iteration) -> Union[None, Iterable[Iterable[Union[str, float, int, None]]]]:

        if iteration % self.status_data_rate > 0 and self.iteration_acceleration is None and self.iteration_accuracy is None:
            return
        
        if self.iteration_acceleration is not None:
            return [[
                1 if self.enabled else 0,
                1 if self.sensor_failed else 0,
                self.iteration_accuracy, 
                acc[0],
                acc[1],
                acc[2]
            ] for acc in self.iteration_acceleration]

        acc =  self.iteration_acceleration or [None, None, None]
        return [[1 if self.enabled else 0, 1 if self.sensor_failed else 0, self.iteration_accuracy,  acc[0], acc[1], acc[2]]]
    
    def flush(self):

        self.iteration_acceleration = None
        self.iteration_accuracy = None
        
