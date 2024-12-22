
from datetime import timedelta
from logging import getLogger
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from core.logic.commands.command import Command
from core.content.general_commands.enable import DisableCommand, EnableCommand
from core.logic.rocket_definition import Command, Part, Rocket
from plyer import battery
from plyer.facades.battery import Battery


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

        self.logger = getLogger('Battery Plyer')

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
                self.logger.error(f'Plyer battery sensor failed: {e}')
                self.sensor_failed = True
        else:
            self.is_charging = None
            self.battery_percent = None
            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', '?'),
            ('sensor_failed', '?'),
            ('is_charging', '?'),
            ('battery_percentage', 'f'),
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[Union[str, float, int, None]]]:
        return [[self.enabled, self.sensor_failed, self.is_charging or False, self.battery_percent or 0]]
    
