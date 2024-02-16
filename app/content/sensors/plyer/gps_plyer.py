
from datetime import timedelta
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.rocket_definition import Command, Part, Rocket
from plyer import gps
from plyer.facades.gps import GPS
from kivy import Logger

from kivy.utils import platform

if platform == 'android':
    from android.permissions import request_permissions, Permission

class PlyerGPSSensor(Part):

    #region Config

    type = 'Sensor.GPS'

    min_update_period = timedelta(milliseconds=1000)

    min_measurement_period = timedelta(milliseconds=10)

    status_data_rate = 10
    ''' Rate at which the status of this component is reported if no other data is being received (in update cycles) '''

    #endregion

    #region Peristant state

    enabled: bool = True

    enabled_confirmed = False

    sensor_failed: bool = False

    location_data_buffer: list[Tuple[Union[float, None], Union[float, None], Union[float, None]]]

    status_data_buffer: list[Tuple[float, float, float]]

    #endregion

    #region Current iteration state

    _enabled: Union[bool, None] = None

    _enabled_confirmed: Union[bool, None] = None

    _sensor_failed: Union[bool, None] = None

    #endregion

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled
        self._enabled = start_enabled

        self.location_data_buffer = list()
        self.status_data_buffer = list()

        # Request the android permission so that the app definetly gets location access
        if platform == 'android':
            request_permissions([Permission.ACCESS_COARSE_LOCATION, Permission.ACCESS_FINE_LOCATION])

        self.try_enable_gps(self.enabled)

        super().__init__(_id, name, parent, list()) # type: ignore

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [EnableCommand, DisableCommand]
    
    def try_enable_gps(self, enable: bool) -> bool:

        try:

            as_gps = cast(GPS, gps)

            if enable and not self.enabled_confirmed:
                self.enabled_confirmed = False
                self._enabled_confirmed = False
                as_gps.configure(on_location=self.make_on_location())
                as_gps.start(1, 1)
            elif not enable:
                as_gps.stop()

        except Exception as e:
            self.sensor_failed = True
            return False
    
        return True
    
    def make_on_location(self):

        def on_location(**kwargs):

            self.enabled_confirmed = True
            self._enabled_confirmed = True
            Logger.info(f'received location {kwargs}')
            lat = kwargs['lat'] if 'lat' in kwargs else None
            lon = kwargs['lon'] if 'lon' in kwargs else None
            alt = kwargs['altitude'] if 'altitude' in kwargs else None

            self.location_data_buffer.append((lat, lon, alt))

        return on_location

    def make_on_status(self):

        def on_status(**kwargs):
            
            Logger.info(f'gps status: {kwargs}')

        return on_status

    def update(self, commands: Iterable[Command], now, iteration: int):
        
        for c in commands:
            if c is EnableCommand:
                self.enabled = True
                self._enabled = True
                c.state = 'success' if self.try_enable_gps(True) else 'failed'
            elif c is DisableCommand:
                self.enabled = False
                self._enabled
                c.state = 'success' if self.try_enable_gps(False) else 'failed'
            else:
                c.state = 'failed' # Part cannot handle this command
                continue

        # Re report status every 10 cycles and try to set up GPS again if
        # enable confirmed not true yet
        if iteration % self.status_data_rate > 0:
            return

        self._enabled = self.enabled
        self._enabled_confirmed = self.enabled_confirmed
        self._sensor_failed = self.sensor_failed
        
        if not self.enabled:
            return

        # Try to enable gps. As soon as the first location
        # is received this will stop doing anything
        self.try_enable_gps(True)

            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', int),
            ('sensor_failed', int),
            ('enabled_confirmed', int),
            ('lat', float),
            ('lng', float),
            ('height', float),
        ]

    def collect_measurements(self, now, iteration) -> Union[None, Iterable[Iterable[Union[str, float, int, None]]]]:

        if len(self.location_data_buffer) > 0:
            res = [[
                1 if self.enabled else 0, 
                1 if self.sensor_failed else 0, 
                1 if self.enabled_confirmed else 0,
                l[0],
                l[1],
                l[2]
            ] for l in self.location_data_buffer]

            return res
        
        if self._enabled == None and self._enabled_confirmed == None and self._sensor_failed == None:
            return None
        
        return [[
            1 if self.enabled else 0,
            1 if self.sensor_failed else 0,
            1 if self.enabled_confirmed else 0,
            None,
            None,
            None
        ]]
    
    def flush(self):
        self._enabled = None
        self._enabled_confirmed = None
        self._sensor_failed = None
        self.location_data_buffer.clear()
        self.status_data_buffer.clear()
    
