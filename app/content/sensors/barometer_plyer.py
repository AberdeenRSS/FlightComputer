
from datetime import timedelta
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.rocket_definition import CommandBase, Part, Rocket
from plyer import barometer
from plyer.facades.barometer import Barometer



class PlyerBarometerSensor(Part):

    type = 'Sensor.Barometer'

    enabled: bool = True

    # plyerSensor = Barometer()

    pressure_value: Union[float, None] = None

    sensor_failed: bool = False

    # Set update to only every 5 seconds as 
    # battery information is low frequency
    min_update_period = timedelta(milliseconds=10)
    min_measurement_period = timedelta(milliseconds=10)

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled
        self.try_enable_barometer(self.enabled)

        super().__init__(_id, name, parent, list()) # type: ignore

    def try_enable_barometer(self, enable: bool) -> bool:
        try:
            as_barometer = cast(Barometer, barometer)
            if enable:
                as_barometer.enable()
            else:
                as_barometer.disable()
        except Exception as e:
            self.sensor_failed = True
            print(f'Plyer barometer sensor failed: {e}')
            return False
    
        return True

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
                as_barometer = cast(Barometer, barometer)
                self.pressure_value = as_barometer.pressure

            except Exception as e:
                print(f'Plyer barometer sensor failed: {e}')
                self.sensor_failed = True
        else:
            self.pressure_value = None
            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', int),
            ('sensor_failed', int),
            ('preaaure_value', float),
        ]

    def collect_measurements(self, now) -> Iterable[Iterable[Union[str, float, int, None]]]:
        return [[1 if self.enabled else 0, 1 if self.sensor_failed else 0, self.pressure_value]]
    
