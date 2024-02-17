from asyncio import Future, Task
from datetime import timedelta
import struct
from typing import Collection, Iterable, Tuple, Type, Union, cast
from uuid import UUID

import numpy as np
from app.content.common_sensor_interfaces.data_age import IDataAge
from app.logic.math.linear import rotate_vector_by_quaternion

from dataclasses import dataclass
from app.content.common_sensor_interfaces.orientation_sensor import IOrientationSensor
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.commands.command import Command
from app.content.microcontroller.arduino_serial import ArduinoOverSerial
from app.logic.rocket_definition import Part, Rocket

class PositiveAttitudeAnalyzer(Part, IDataAge):
    type = 'Analyzer.Attitude.Absolute'

    enabled: bool = True

    min_update_period = timedelta(milliseconds=20)

    min_measurement_period = timedelta(milliseconds=50)

    orientation_sensor: IOrientationSensor

    last_good_data_update: float | None = None

    pointing_up: int | None = None
    '''
    1 -> pointing up
    0 -> unknown/in between (depends on dead zones defined)
    -1 -> pointing down
    '''

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], orientation_sensor: IOrientationSensor):

        self.orientation_sensor = orientation_sensor

        super().__init__(_id, name, parent, [orientation_sensor])   # type: ignore

    def get_accepted_commands(self) -> list[Type[Command]]:
        return []

    def update(self, commands: Iterable[Command], now, iteration):

        orientation = self.orientation_sensor.get_orientation()

        if orientation is None:
            self.pointing_up = 0
            return

        quat_len = np.linalg.norm(orientation)

        # Should be a unit quaternion
        if quat_len < 0.5 or quat_len > 1.5:
            self.pointing_up = 0
            return

        up_vector = np.array([0.0, 0.0, 1.0], dtype=float)

        as_quat = np.array([orientation[0], orientation[1], orientation[2], orientation[3]], dtype=float)

        pointing_vector = rotate_vector_by_quaternion(up_vector, as_quat)

        self.pointing_up = 1 if pointing_vector[2] > 0 else -1

        self.last_good_data_update = now
        

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('pointing_up', int)
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[float | None]]:
        return [[self.pointing_up]]
    
    def get_data_age(self) -> float | None:
        return self.last_good_data_update

