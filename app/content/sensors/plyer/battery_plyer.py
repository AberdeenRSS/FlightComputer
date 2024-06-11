
from datetime import timedelta
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.rocket_definition import Command, Part, Rocket
from plyer import battery
from plyer.facades.battery import Battery
from kivy import Logger


class PlyerBatterySensor(Part):

    type = 'Sensor.Battery'

    enabled: bool = True

    # plyerSensor = Battery()

    battery_percent: Union[float, None] = None

    sensor_failed: bool = False

    is_charging: Union[None, bool] = None

    # Set update to only every 5 seconds as 
    # battery information is low frequency
    min_update_period = timedelta(seconds=5)
    min_measurement_period = timedelta(seconds=5)

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled

        super().__init__(_id, name, parent, list()) # type: ignore

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [EnableCommand, DisableCommand]
   
    def update(self, commands: Iterable[Command], now, iteration):
        
        for c in commands:
            if isinstance(c, EnableCommand):
                self.enabled = True
            elif isinstance(c, DisableCommand):
                self.enabled = False
            else:
                c.state = 'failed' # Part cannot handle this command
                continue
            
            c.state = 'success'
        
        if self.enabled and not self.sensor_failed:
            try:    
                as_battery = cast(Battery, battery)
                as_battery.get_state()
                self.is_charging = as_battery.status['isCharging']
                self.battery_percent = as_battery.status['percentage']
            except Exception as e:
                Logger.error(f'Plyer battery sensor failed: {e}')
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

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[Union[str, float, int, None]]]:
        return [[1 if self.enabled else 0, 1 if self.sensor_failed else 0,  1 if self.is_charging else 0, self.battery_percent]]
    
