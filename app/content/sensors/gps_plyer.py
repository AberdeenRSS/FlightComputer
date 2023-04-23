
from datetime import timedelta
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.rocket_definition import CommandBase, Part, Rocket
from plyer import gps
from plyer.facades.gps import GPS
try:
    from android.permissions import request_permissions, Permission
except:
    print('Not on android')

class PlyerGPSSensor(Part):

    type = 'Sensor.GPS'

    enabled: bool = True

    enabled_confirmed = False

    sensor_failed: bool = False

    location_data_buffer = list[Tuple[Union[float, None], Union[float, None], Union[float, None]]]()

    status_data_buffer = list[Tuple[float, float, float]]()

    min_update_period = timedelta(milliseconds=1000)

    min_measurement_period = timedelta(milliseconds=10)

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled

        # Request the android permission so that the app definetly gets location access
        try:
            request_permissions([Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION])
        except:
            print('Failed acquiring gps permissions')

        self.try_enable_gps(self.enabled)

        super().__init__(_id, name, parent, list()) # type: ignore

    def get_accepted_commands(self) -> list[Type[CommandBase]]:
        return [EnableCommand, DisableCommand]
    
    def try_enable_gps(self, enable: bool) -> bool:

        def on_location(**kwargs):

            self.enabled_confirmed = True
            print(f'received location {kwargs}')
            lat = kwargs['lat'] if 'lat' in kwargs else None
            lon = kwargs['lon'] if 'lon' in kwargs else None
            alt = kwargs['altitude'] if 'altitude' in kwargs else None

            self.location_data_buffer.append((lat, lon, alt))

        try:

            as_gps = cast(GPS, gps)

            if enable and not self.enabled_confirmed:
                self.enabled_confirmed = False
                print('Starting GPS sensor')
                as_gps.configure(on_location=on_location, on_status=self.on_status)
                as_gps.start(1, 1)
            elif not enable:
                as_gps.stop()

        except Exception as e:
            self.sensor_failed = True
            print(f'Plyer gps sensor failed: {e}')
            return False
    
        return True
    
    def on_location(self, location):
        print(location)

    def on_status(self, location):
        print(location)
   
    def update(self, commands: Iterable[Command], now):
        
        # Try to enable gps. As soon as the first location
        # is received this will stop doing anything
        self.try_enable_gps(True)


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
            ('enabled_confirmed', int),
            ('lat', float),
            ('lng', float),
            ('height', float),
        ]

    def collect_measurements(self, now) -> Iterable[Iterable[Union[str, float, int, None]]]:

        if len(self.location_data_buffer) > 0:
            res = [[
                1 if self.enabled else 0, 
                1 if self.sensor_failed else 0, 
                1 if self.enabled_confirmed else 0,
                l[0],
                l[1],
                l[2]
            ] for l in self.location_data_buffer]

            self.location_data_buffer = list(self.location_data_buffer[:-1]) # Keep the last location update
            return res
        
        return [[
            1 if self.enabled else 0,
            1 if self.sensor_failed else 0,
            1 if self.enabled_confirmed else 0,
            None,
            None,
            None
        ]]
    
