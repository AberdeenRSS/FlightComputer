
from typing import Iterable, Tuple, Type, Union
from typing_extensions import Self
from uuid import UUID
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.rocket_definition import CommandBase, Part, Rocket
from plyer.facades.battery import Battery



class PlyerBatterySensor(Part):

    type = 'Sensor.Battery'

    enabled: bool = True

    plyerSensor = Battery()

    battery_percent: Union[float, None] = None

    sensor_failed: bool = False

    is_charging: Union[None, bool] = None

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled

        super().__init__(_id, name, parent, list()) # type: ignore

    def get_accepted_commands(self) -> list[Type[CommandBase]]:
        return [EnableCommand, DisableCommand]
   
    def update(self, commands: Iterable[Command], now):
        
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
                self.plyerSensor.get_state()
                self.is_charging = self.plyerSensor.status.isCharging
                self.battery_percent = self.plyerSensor.status.percentage
            except:
                self.sensor_failed = True
        else:
            self.is_charging = None
            self.battery_percent = None
            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', int),
            ('sensor_failed', int),
            ('is_charging', int),
            ('battery_percentage', float),
        ]

    def collect_measurements(self, now) -> Iterable[Iterable[Union[str, float, int, None]]]:
        return [[1 if self.enabled else 0, 1 if self.sensor_failed else 0,  1 if self.is_charging else 0, self.battery_percent]]
    
