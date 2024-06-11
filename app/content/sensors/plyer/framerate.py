
from datetime import timedelta
import datetime
import time
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.rocket_definition import Command, Part, Rocket


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

    def get_accepted_commands(self) -> list[Type[Command]]:
        return []
    
    def update(self, commands: Iterable[Command], now: float, iteration):
        
        self.frames_since_last_measurement += 1

        if iteration % self.measurement_period > 0 or self.last_measurement is None:
            return
        
        time_delta = now - self.last_measurement_time
        self.last_measurement_time = now

        frame_time =  time_delta / self.frames_since_last_measurement
        self.framerate = 1/frame_time
        self.frames_since_last_measurement = 0

            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('framerate', int)
        ]

    def collect_measurements(self, now, iteration) -> Union[None, Iterable[Iterable[Union[str, float, int, None]]]]:

        return [[self.framerate]]
    
    
