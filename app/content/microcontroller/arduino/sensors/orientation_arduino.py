from asyncio import Future, Task
from datetime import timedelta
import struct
from typing import Collection, Iterable, Tuple, Type, Union, cast
from uuid import UUID

from dataclasses import dataclass
from app.content.common_sensor_interfaces.data_age import IDataAge
from app.content.common_sensor_interfaces.orientation_sensor import IOrientationSensor
from app.content.general_commands.calibrate import CalibrateZeroCommand
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.content.microcontroller.arduino_serial_common import ArduinoHwBase
from app.logic.commands.command import Command
from app.content.microcontroller.arduino_serial import ArduinoOverSerial
from app.logic.math.linear import quaternion_multiply
from app.logic.rocket_definition import Part, Rocket

import numpy as np
from time import time

class OrientationSensor(Part, IOrientationSensor, IDataAge):
    type = 'Orientation'

    enabled: bool = True

    min_update_period = timedelta(milliseconds=20)

    min_measurement_period = timedelta(milliseconds=50)

    arduino: ArduinoHwBase

    original_quat: np.ndarray

    quat: np.ndarray

    calibrated: bool = False

    last_data_received: float | None = None

    offset: np.ndarray 

    partID = 10

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], arduino_parent: ArduinoHwBase, start_enabled=True):
        self.arduino = arduino_parent
        self.enabled = start_enabled

        self.original_quat = np.array([0.0, 0.0, 0.0, 0.0], dtype=float)
        self.quat = np.array([0.0, 0.0, 0.0, 0.0], dtype=float)
        self.offset = np.array([0.0, 0.0, 0.0, 1.0], dtype=float)

        super().__init__(_id, name, parent, list())  # type: ignore

        self.x = self.y = self.z = 0.0
        self.arduino.serial_adapter.addDataCallback(self.partID, self.set_measurements)

    def set_measurements(self, part: int, data: bytearray):

        self.original_quat[0] = int.from_bytes(data[0:2], 'little', signed=True)/32767
        self.original_quat[1] = int.from_bytes(data[2:4], 'little', signed=True)/32767
        self.original_quat[2] = int.from_bytes(data[4:6], 'little', signed=True)/32767
        self.original_quat[3] = int.from_bytes(data[6:8], 'little', signed=True)/32767
        self.calibrated =  bool.from_bytes(data[8:9], 'little')

        self.quat = quaternion_multiply(self.original_quat, self.offset)

        self.last_data_received = time()

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [EnableCommand, DisableCommand, CalibrateZeroCommand]

    def calibrate(self, c: CalibrateZeroCommand):
        
        quat_len = np.linalg.norm(self.original_quat)

        if quat_len < 0.5 or quat_len > 1.5:
            c.state = 'failed'
            c.response_message = 'No/Garbage data, could not calibrate'
            return
        
        self.offset = np.array([-self.original_quat[0], self.original_quat[1], self.original_quat[2], self.original_quat[3]])

        c.state ='success'
        c.response_message = f'Calibrated with offset {self.offset}'

    def update(self, commands: Iterable[Command], now, iteration):

        for c in commands:

            if isinstance(c, EnableCommand):
                self.enabled = True
                c.state = "success"
                continue

            if isinstance(c, DisableCommand):
                self.enabled = False
                c.state = "success"
                continue

            if isinstance(c, CalibrateZeroCommand):
                self.calibrate(c)

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('calibrated', '?'),
            ('W', 'f'),
            ('X', 'f'),
            ('Y', 'f'),
            ('Z', 'f'),
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[float]]:
    
        return [[self.calibrated, self.quat[0], self.quat[1], self.quat[2], self.quat[3]]]

    def get_orientation(self):
        return (self.quat[0], self.quat[1], self.quat[2], self.quat[3])
    
    def get_data_age(self):
        return self.last_data_received