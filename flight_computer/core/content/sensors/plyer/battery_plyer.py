
from datetime import timedelta
from logging import getLogger
from typing import Iterable, Tuple, Type, Union, cast
from uuid import UUID
from flight_computer.core.logic.rocket_definition import Part, Rocket
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

    def get_accepted_commands(self):
        return [
            *super().get_accepted_commands()
        ]
    
    def get_command_callbacks(self):
        return [
            *super().get_command_callbacks()
        ]
   
    def update(self, now, iteration):
        
        if self.enabled and not self.sensor_failed:
            try:    
                as_battery = cast(Battery, battery)
                as_battery.get_state()
                self.is_charging = as_battery.status['isCharging']
                self.battery_percent = as_battery.status['percentage']

                self.submit_measurement(3, self.is_charging, now)
                self.submit_measurement(4, self.battery_percent, now)

            except Exception as e:
                self.logger.error(f'Plyer battery sensor failed: {e}')
                self.sensor_failed = True
        else:
            self.is_charging = None
            self.battery_percent = None
            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            *super().get_measurement_shape(),
            ('sensor_failed', 0, '?'),
            ('is_charging', 0, '?'),
            ('battery_percentage', 0, 'f'),
        ]

    
