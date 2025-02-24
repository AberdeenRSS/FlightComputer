
from datetime import timedelta
import datetime
import time
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from flight_computer.core.logic.commands.command import Command
from flight_computer.core.content.general_commands.enable import DisableCommand, EnableCommand
from flight_computer.core.logic.rocket_definition import Command, Part, Rocket


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

    def get_accepted_commands(self):
        return [
            *super().get_accepted_commands()
        ]
    
    def update(self, commands: Iterable[Command], now: float, iteration):
        
        self.frames_since_last_measurement += 1

        if iteration % self.measurement_period > 0:
            return
        
        time_delta = now - self.last_measurement_time
        self.last_measurement_time = now

        frame_time =  time_delta / self.frames_since_last_measurement
        self.framerate = 1/frame_time
        self.frames_since_last_measurement = 0

        self.submit_measurement(2, self.framerate, now)

            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            *super().get_measurement_shape(),
            ('framerate', 0, 'f')
        ]

    
    
