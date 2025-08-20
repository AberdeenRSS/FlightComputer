import collections
from datetime import datetime, timedelta
from typing import Collection, Iterable, Tuple, Type, Union, cast
from uuid import UUID
from flight_computer.core.logic.rocket_definition import Measurement, Part, Rocket
import numpy as np
from logging import _nameToLevel

class SimpleFlightDirector(Part):

    type = 'FlightDirector'

    min_update_period = timedelta(milliseconds=10)
    min_measurement_period = timedelta(milliseconds=5)

    altimeter: Part

    drogue_deployment_device: Part | None

    main_deployment_device: Part | None

    main_deployment_height: float = 400
    '''
    Main parachute deployment height in m
    '''

    launch_detect_speed: float = 10
    '''
    Vertical speed to detect launch in m/s
    '''

    vertical_speed_window: float = 0.3 #300ms
    '''
    The width of the sliding window used to determine the current vertical speed
    '''

    min_vertical_speed_values: int = 3 
    '''
    The minimum amount of valid altitude measurements within the widow required to
    trigger events based on vertical speed
    '''

    apogee_detect_window: float = 0.5
    '''
    For how long the rocket needs to have not ascended for apogee to be detected
    '''

    engine_burn_lockout: float = 3
    '''
    Lockout in s during which no parachute deployment will occur after launch
    '''

    landing_detect_speed: float = 0.5 #m/s
    '''
    Minimum speed threshold under which the rocket will be considered to have landed
    '''

    launch_time: float = 0

    max_alt: float = 0

    max_alt_time: float = 0

    last_flight_phase_command = 0

    flight_phase: int = 0

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], altimeter: Part, drogue_deployment_device: Part | None, main_deployment_device: Part | None):

        super().__init__(_id, name, parent, list()) # type: ignore

        self.altimeter = altimeter
        self.drogue_deployment_device = drogue_deployment_device
        self.main_deployment_device = main_deployment_device

        self.altitude_buffer = collections.deque[tuple[float, float]]([], maxlen=40)
        self.altimeter.subscribe_measurement_by_name('altitude', _id, self.on_altitude)

        self.flight_phases = ['Idle', 'Armed', 'Ascend_Lockout', 'Ascend', 'Descend', 'Descend_Main', 'Landed']
        self.flight_phase_methods = [
            None, 
            self.during_armed,
            self.during_ascend_lockout,
            self.during_ascend,
            self.during_descend,
            self.during_descend_main,   
            None
            ]

        self.M_VERT_SPEED = self.measurement_index_lookup['vertical_speed']
 
    def make_measurement_shape(self) -> Collection[Tuple[str, int, Type | str | list[Tuple[str, Type | str]]]]:
        return [
            *super().make_measurement_shape(),
            ('flight_phase', 1, 'i'),
            ('vertical_speed', 0, 'f')
        ]

    def make_accepted_commands(self):
        return [
            *super().make_accepted_commands(),
            ('arm', ''),
            ('abort', ''),
            ('force_flight_phase', 'i')
        ]
    
    def make_command_callbacks(self):
        return [
            *super().make_command_callbacks(),
            self.arm,
            self.abort,
            self.force_flight_phase
        ]
    
    def make_config_shape(self) -> list[Tuple[str, str | Type]]:
        return [
            *super().make_config_shape(),
            ('main_deployment_height', 'd'),
            ('launch_detect_speed', 'f'),
            ('engine_burn_lockout', 'f'),
            ('vertical_speed_window', 'f'),
            ('min_vertical_speed_values', 'f'),
            ('apogee_detect_window', 'f'),
            ('landing_detect_speed', 'f')
        ]
    
    def dump_config(self) -> dict[str, str | bytes | float | int | bool | Iterable[float | int | bool]]:
        return {
            **super().dump_config(),
            'main_deployment_height': self.main_deployment_height,
            'launch_detect_speed': self.launch_detect_speed,
            'engine_burn_lockout': self.engine_burn_lockout,
            'vertical_speed_window': self.vertical_speed_window,
            'min_vertical_speed_values': self.min_vertical_speed_values,
            'apogee_detect_window': self.apogee_detect_window,
            'landing_detect_speed': self.landing_detect_speed
        }
    
    def load_config(self, config: dict[str, str | bytes | float | int | bool | Iterable[float | int | bool]]):
        super().load_config(config)

        if 'main_deployment_height' in config:
            self.main_deployment_height = float(cast(float, config['main_deployment_height']))
        
        if 'launch_detect_speed' in config:
            self.launch_detect_speed = float(cast(float, config['launch_detect_speed']))

        if 'engine_burn_lockout' in config:
            self.engine_burn_lockout = float(cast(float, config['engine_burn_lockout']))

        if 'vertical_speed_window' in config:
            self.vertical_speed_window = float(cast(float, config['vertical_speed_window']))

        if 'min_vertical_speed_values' in config:
            self.min_vertical_speed_values = int(cast(int, config['min_vertical_speed_values']))

        if 'apogee_detect_window' in config:
            self.apogee_detect_window = float(cast(float, config['apogee_detect_window']))

        if 'landing_detect_speed' in config:
            self.landing_detect_speed = float(cast(float, config['landing_detect_speed']))

    def on_altitude(self, m: Measurement):
        self.altitude_buffer.appendleft((m[0], cast(float, m[2])))

    def calc_vert_speed(self, now: float) -> float | None:

        values = [(t, v) for t, v in self.altitude_buffer if ((now - t) < self.vertical_speed_window)]

        if len(values) < self.min_vertical_speed_values:
            return None
        
        delta_t = np.diff([t for t, _ in values])
        delta_x = np.diff([v for _, v in values])

        speeds = delta_x/delta_t

        return cast(float, np.average(speeds))

    def update(self, now, iteration):

        vertical_speed = self.calc_vert_speed(now)

        if vertical_speed is not None:
            self.submit_measurement(self.M_VERT_SPEED, vertical_speed, now)

        phase_method = self.flight_phase_methods[self.flight_phase]

        if phase_method is not None:
            phase_method(now, vertical_speed)

    def arm(self, t: float, _):

        if t < self.last_flight_phase_command:
            self.log(f'Ignoring arming command as command was received out of order', _nameToLevel['WARN'])
            return
        
        self.last_flight_phase_command = t

        if self.flight_phase != 0:
            self.log(f'Flight director can only be armed when in phase "Idle", currently in phase {self.flight_phases[self.flight_phase]}', _nameToLevel['ERROR'])
            return

        self.flight_phase = 1
        self.submit_measurement_by_name('flight_phase', 1)
        self.log('Armed flight director')

    def abort(self, t: float, _):

        if t < self.last_flight_phase_command:
            self.log(f'Ignoring abort command as command was received out of order', _nameToLevel['WARN'])
            return
        
        self.last_flight_phase_command = t

        self.flight_phase = 0
        self.submit_measurement_by_name('flight_phase', 0)
        self.log('Aborted flight director, back in idle')

    def force_flight_phase(self, t: float, phase: int):

        if t < self.last_flight_phase_command:
            self.log(f'Ignoring set flight phase command as command was received out of order', _nameToLevel['WARN'])
            return
        
        self.last_flight_phase_command = t
        self.flight_phase = phase
        self.submit_measurement_by_name('flight_phase', phase)
        self.log(f'Forced flight director into phase "{self.flight_phases[phase]}"')

    def record_max_alt(self):
        
        if len(self.altitude_buffer) < 1:
            return
        
        highest = max(self.altitude_buffer, key=lambda x: x[1])

        if highest[1] < self.max_alt:
            return
        
        self.max_alt_time = highest[0]
        self.max_alt = highest[1]
            
    def during_armed(self, now: float, vertical_speed: float | None):
        
        self.record_max_alt()

        if vertical_speed is None:
            return

        if vertical_speed < self.launch_detect_speed:
            return
        
        self.launch_time = now
        self.flight_phase = 2
        self.submit_measurement_by_name('flight_phase', 2, now)
        self.log(f'Launch detected at {datetime.fromtimestamp(now)}. Speed: {vertical_speed:.2f}m/s')

    def during_ascend_lockout(self, now: float, vertical_speed: float | None):
        
        self.record_max_alt()

        if now < (self.launch_time + self.engine_burn_lockout):
            return
        
        self.flight_phase = 3
        self.submit_measurement_by_name('flight_phase', 3, now)
        self.log(f'Lockout over, deployment now possible. Flight time: {(now - self.launch_time):.2f}s')

    def during_ascend(self, now: float, vertical_speed: float | None):
        
        self.record_max_alt()

        # Ensure that there is recent altitude data, before making any deployment decisions
        # This checks that there was a new altitude value as recently as 1/2 of the detect window
        last_alt_update_time = max(t for t, _ in self.altitude_buffer)
        if (now - last_alt_update_time) > (self.apogee_detect_window/2):
            return

        if (now - self.max_alt_time) < self.apogee_detect_window:
            return
              
        self.flight_phase = 4
        self.submit_measurement_by_name('flight_phase', 4, now)
        self.log(f'Apogee reached, deploying drogue. Max altitude: {self.max_alt:.2f}m. Flight time: {(now - self.launch_time):.2f}s')

        if self.drogue_deployment_device is not None:
            try:
                command_index = self.drogue_deployment_device.command_index_lookup['activate']
                self.drogue_deployment_device.command_callbacks[command_index](now, None)
                self.log(f'Triggered drogue parachute')
            except Exception as e:
                self.log(f'Failed deploying drogue: {e}', _nameToLevel['ERROR'])

    def during_descend(self, now: float, vertical_speed: float | None):

        min_descend_alt = min(v for t, v in  self.altitude_buffer if t > self.max_alt_time)

        if min_descend_alt > self.main_deployment_height:
            return
        
        self.flight_phase = 5
        self.submit_measurement_by_name('flight_phase', 5, now)
        self.log(f'Main deployment height reached, deploying main. Max altitude: {min_descend_alt:.2f}m. Flight time: {(now - self.launch_time):.2f}s')

        if self.main_deployment_device is not None:
            try:
                command_index = self.main_deployment_device.command_index_lookup['activate']
                self.main_deployment_device.command_callbacks[command_index](now, None)
                self.log(f'Triggered main parachute')
            except Exception as e:
                self.log(f'Failed deploying main: {e}', _nameToLevel['ERROR'])
                

    def during_descend_main(self, now: float, vertical_speed: float | None):

        if vertical_speed   is None or vertical_speed > self.landing_detect_speed:
            return
        
        self.flight_phase = 6
        self.submit_measurement_by_name('flight_phase', 5, now)
        self.log(f'Rocket landed. Flight time: {(now - self.launch_time):.2f}s')

