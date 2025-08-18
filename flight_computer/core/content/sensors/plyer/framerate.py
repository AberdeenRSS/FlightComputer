
from datetime import timedelta
import time
from typing import Iterable, Tuple, Type, Union
from uuid import UUID
from flight_computer.core.logic.rocket_definition import Part, Rocket


class FramerateSensor(Part):

    type = 'Sensor.Framerate'

    min_update_period = timedelta(microseconds=1)

    min_measurement_period = timedelta(milliseconds=100)

    measurement_period = 20

    frames_since_last_measurement = 0

    last_measurement_time = time.time()

    framerate: Union[float, None] = None

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        super().__init__(_id, name, parent, list()) # type: ignore

        self.M_FPS = self.measurement_index_lookup['framerate']

    def make_accepted_commands(self):
        return [
            *super().make_accepted_commands()
        ]
    
    def make_command_callbacks(self):
        return [
            *super().make_command_callbacks()
        ]
    
    def update(self, now: float, iteration):
        
        self.frames_since_last_measurement += 1

        if iteration % self.measurement_period > 0:
            return
        
        time_delta = now - self.last_measurement_time
        self.last_measurement_time = now

        frame_time =  time_delta / self.frames_since_last_measurement
        self.framerate = 1/frame_time
        self.frames_since_last_measurement = 0

        self.submit_measurement(self.M_FPS, self.framerate, now)

            
    def make_measurement_shape(self):
        return [
            *super().make_measurement_shape(),
            ('framerate', 0, 'f')
        ]

    
    
