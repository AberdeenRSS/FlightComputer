
from datetime import timedelta
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.rocket_definition import CommandBase, Part, Rocket
from plyer import gps
from plyer.facades.gps import GPS


class PlyerGPSSensor(Part):

    type = 'Sensor.GPS'

    enabled: bool = True

    sensor_failed: bool = False

    location_data_buffer = list[Tuple[float, float, float]]()

    status_data_buffer = list[Tuple[float, float, float]]()


    min_update_period = timedelta(milliseconds=10)

    min_measurement_period = timedelta(milliseconds=10)

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled
        self.try_enable_gps(self.enabled)

        super().__init__(_id, name, parent, list()) # type: ignore

    def get_accepted_commands(self) -> list[Type[CommandBase]]:
        return [EnableCommand, DisableCommand]
    
    def try_enable_gps(self, enable: bool) -> bool:
        try:
            as_gps = cast(GPS, gps)
            if enable:
                as_gps.configure(lambda l: self.on_location(l), lambda s: self.on_status(s))
                as_gps.start(1, 1)
            else:
                as_gps.stop()
        except Exception as e:
            self.sensor_failed = True
            print(f'Plyer acceleration sensor failed: {e}')
            return False
    
        return True
    
    def on_location(self, location):
        print(location)

    def on_status(self, location):
        print(location)
   
    def update(self, commands: Iterable[Command], now):
        
        for c in commands:
            if c is EnableCommand:
                self.enabled = True
                c.state = 'success' if self.try_enable_gps(True) else 'failed'
            elif c is DisableCommand:
                self.enabled = False
                c.state = 'success' if self.try_enable_gps(False) else 'failed'
            else:
                c.state = 'failed' # Part cannot handle this command
                continue
            
            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', int),
            ('sensor_failed', int),
        ]

    def collect_measurements(self, now) -> Iterable[Iterable[Union[str, float, int, None]]]:
        return [[1 if self.enabled else 0, 1 if self.sensor_failed else 0]]
    
