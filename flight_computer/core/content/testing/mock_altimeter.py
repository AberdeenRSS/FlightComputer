

from datetime import timedelta
from typing import Collection, Tuple, Type, Union
from uuid import UUID
from flight_computer.core.logic.rocket_definition import Part, Rocket


class MockAltimeter(Part):

    type = 'Sensor.Mock_Altimeter'
   

    min_update_period = timedelta(milliseconds=10)
    min_measurement_period = timedelta(milliseconds=5)

    in_flight: bool = False

    burn_time: float = 0

    acceleration: float = 0

    main_height: float = 0

    main_speed: float = 0

    drogue_speed: float = 0

    altitude: float = 0

    speed: float = 0

    flight_start: float = 0

    last_update: float = 0
   
    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None]):

        super().__init__(_id, name, parent, list()) # type: ignore

        self.M_ALT = self.measurement_index_lookup['altitude']

    def make_measurement_shape(self) -> Collection[Tuple[str, int, Type | str | list[Tuple[str, Type | str]]]]:
        return [
            *super().make_measurement_shape(),
            ('altitude', 0, 'f'),
        ]

    def make_accepted_commands(self):
        return [
            *super().make_accepted_commands(),
            ('simulate_flight', (('burn_time', 'f'), ('motor_acceleration', 'f'), ('main_height', 'f'), ('main_speed', 'f'), ('drogue_speed', 'f')))
        ]
    
    def make_command_callbacks(self):
        return [
            *super().make_command_callbacks(),
            self.simulate_flight
        ]
   
    def update(self, now, iteration):

        if not self.in_flight:
            return
        
        flight_time = now - self.flight_start

        dt = now - self.last_update
        self.last_update = now

        if flight_time < self.burn_time:
            self.speed += self.acceleration * dt
        elif self.altitude < 0:
            self.in_flight = False
            return
        else:
            self.speed -= 10 * dt # gravity

            if self.speed < 0:
                if self.altitude > self.main_height:
                    self.speed = -self.drogue_speed
                else:
                    self.speed = -self.main_speed
        
        self.altitude += self.speed * dt

        self.submit_measurement(self.M_ALT, self.altitude, now)

    def simulate_flight(self, t: float, burn_time: float, acceleration: float, main_height: float, main_speed: float, drogue_speed: float):

        self.in_flight = True
        self.flight_start = t
        self.last_update = t
        self.speed = 0
        self.altitude = 0
        
        self.burn_time = burn_time
        self.acceleration = acceleration
        self.main_height = main_height
        self.main_speed = main_speed
        self.drogue_speed = drogue_speed