from datetime import timedelta
from typing import Iterable, Tuple, Type, Union, cast
from uuid import UUID
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.rocket_definition import Command, Part, Rocket
from kivy import Logger

try:
    from kivy.utils import platform

    if platform == 'android':
        # from android.permissions import request_permissions, Permission
        from jnius import autoclass
        from android.permissions import request_permissions, Permission

except:
    print('Not running in kivy app')


class PyjiniusGPSSensor(Part):

    #region Config

    type = 'Sensor.GPS'

    min_update_period = timedelta(milliseconds=10)

    min_measurement_period = timedelta(milliseconds=10)

    status_data_rate = 1_000


    #endregion

    #region Status

    enabled: bool = True

    sensor_failed: bool = False

    hardware = None
    
    #endregion 

    #region Sensor Data

    locations: list[Tuple[float, float, float]]

    provider: Union[None, str] = None

    # acceleration: Union[None, Tuple[float, float, float]]

    # accuracy: Union[int, None] = None

    # iteration_acceleration: Union[None, list[Tuple[float, float, float]]] = None

    # iteration_accuracy: Union[int, None] = None

    #endregion

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled
        self.locations = list()

        if platform == 'android':
            request_permissions([Permission.ACCESS_COARSE_LOCATION, Permission.ACCESS_FINE_LOCATION])

        self.try_enable(self.enabled)
        

        super().__init__(_id, name, parent, list()) # type: ignore

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [EnableCommand, DisableCommand]
    
    def try_enable(self, enable: bool) -> bool:
        try:

            Logger.info('GPS: Trying to initialzie')

            # Init the native class
            self.hardware = autoclass('org.rss.GPS')
            self.hardware.refreshOrStart()

            Logger.info(f'GPS: Initialized; {[p for p in self.hardware.providers]} are available as providers')

        except Exception as e:
            self.sensor_failed = True
            self.hardware = None
            Logger.error(f'Native gps sensor failed: {e}')
            return False
    
        return True
    
    def update(self, commands: Iterable[Command], now, iteration):
        
        for c in commands:
            if isinstance(c, EnableCommand):
                success = self.try_enable(True)
                c.state = 'success' if success else 'failed'
                c.response_message = 'Successfully enabled accelerometer' if success else 'Accelerometer unavailable'
                if success:
                    self.enabled = True
            elif isinstance(c, DisableCommand):
                success = self.try_enable(False)
                c.state = 'success' if success else 'failed'
                c.response_message = 'Successfully disabled accelerometer' if success else 'Failed disabling accelerometer'
                if success: 
                    self.enabled = False
            else:
                c.state = 'failed' # Part cannot handle this command
                c.response_message = f'Cannot process commands of type {c.command_type}'
                continue
            
        if self.hardware is not None:

            try:    
                last_events = self.hardware.lastEvents

                self.hardware.flush()

                Logger.info(f'Got {len(last_events)} locations, using {self.hardware.provider} provider')

                self.provider = self.hardware.provider

                for l in last_events:
                    self.locations.append((l.getLatitude(), l.getLongitude(), l.getAltitude()))

            except Exception as e:
                Logger.error(f'Plyer gravity sensor failed: {e}')
                self.sensor_failed = True
        # else:
            # self.iteration_acceleration = self.acceleration = None
            # self.iteration_accuracy = self.accuracy = None
            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', '?'),
            ('sensor_failed', '?'),
            ('provider', '10s'),
            ('lat', 'f'),
            ('lng', 'f'),
            ('alt', 'f')
        ]

    def collect_measurements(self, now, iteration) -> Union[None, Iterable[Iterable[Union[str, float, int, None]]]]:

        if iteration % self.status_data_rate > 0 and len(self.locations) < 1 and self.provider is None:
            return []
        
        if len(self.locations) < 1:
            return []
            # return [[self.enabled, self.sensor_failed, self.provider or '', 0, 0, 0]]
        
        return [[self.enabled, self.sensor_failed, self.provider or '', *l] for l in self.locations]
    
    
    def flush(self):

        self.locations = list()
        
