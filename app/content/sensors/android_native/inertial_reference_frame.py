from datetime import timedelta
from typing import Collection, Iterable, Sequence, Tuple, Type, Union, cast
from uuid import UUID
from app.content.sensors.android_native.acceleration_pyjinius import PyjiniusAccelerationSensor

from app.content.sensors.android_native.gyroscope_pyjinius import PyjiniusGyroscopeSensor
from app.logic.commands.command import Command
from app.logic.math.linear import quaternion_multiply, rotate_vector_by_quaternion
from app.logic.rocket_definition import Measurements, Part, Rocket

import numpy as np


class InertialReferenceFrame(Part):

    #region Config

    type = 'ReferenceFrame.Inertial'

    virtual: bool = True

    dependencies: list 

    min_update_period: timedelta = timedelta(milliseconds=5)

    min_measurement_period: timedelta = timedelta(milliseconds=5)

    #endregion

    #region Initial 
    initial_orientation: np.ndarray
    
    #endregion

    last_accelerometer_update: Union[float, None] = None

    last_gyro_update: Union[float, None] = None

    angular_velocity: np.ndarray

    orientation: np.ndarray

    ground_velocity: np.ndarray

    air_velocity: np.ndarray

    position: np.ndarray


    def __init__(self, accelerometer: PyjiniusAccelerationSensor, gyro: PyjiniusGyroscopeSensor, uuid: UUID, name: str, parent, **kwargs):

        super().__init__(uuid, name, parent, list(), **kwargs)

        self.accelerometer = accelerometer
        self.gyro = gyro

        self.dependencies.append(accelerometer)
        self.dependencies.append(gyro)

        self.position = kwargs.get('initial_position') or np.array([0, 0, 0])
        self.air_velocity = kwargs.get('initial_air_velocity') or np.array([0, 0, 0])
        self.ground_velocity = kwargs.get('initial_ground_velocity') or np.array([0, 0, 0])

        self.angular_velocity = kwargs.get('initial_ground_velocity') or np.array([0, 0, 0])
        self.initial_orientation = np.array([0, 0, 1, 0])
        self.orientation = np.array(self.initial_orientation, copy=True)


    def update_angular_velocity(self):
        current_angular_acc = self.gyro.iteration_angular_acceleration

        if self.last_gyro_update is None or self.gyro.last_update is None:
            self.last_gyro_update = self.gyro.last_update
            return
    
        if current_angular_acc is None:
            return
        
        # Get the time step
        time_delta = self.last_gyro_update - self.gyro.last_update
        
        # Apply angular acceleration changes to angular velocity and orientation
        np_ang_acc = np.array(current_angular_acc, copy=False)*(time_delta/len(current_angular_acc))

        self.angular_velocity += np.sum(np_ang_acc, axis=0)

        angular_velocity_quats = np.append([[0]], np_ang_acc)

        half_delta = time_delta/2

        for v in angular_velocity_quats:
            self.orientation += half_delta * quaternion_multiply(v, self.orientation)

        # Update the time of last update
        self.last_gyro_update = self.gyro.last_update

    def update_velocity(self):
        current_acc = self.accelerometer.iteration_acceleration

        if self.last_accelerometer_update is None or self.accelerometer.last_update is None:
            self.last_accelerometer_update = self.accelerometer.last_update
            return

        if current_acc is None:
            return
        
        # Get the time step
        time_delta = self.last_accelerometer_update - self.accelerometer.last_update

        # Apply air velocity
        self.air_velocity += np.sum(current_acc, axis=0)*time_delta/len(current_acc)

        # Get inertial velocity
        self.ground_velocity = rotate_vector_by_quaternion(self.air_velocity, self.orientation)

        # Update the time of last update
        self.last_gyro_update = self.gyro.last_update

    def update(self, commands: Iterable[Command], now: float, iteration: int) -> Union[None, Collection[Command]]:

        self.update_angular_velocity()
        self.update_velocity()

    def get_measurement_shape(self) -> Collection[Tuple[str, Type]]:
        return [
            ('angular_velocity-x', float),
            ('angular_velocity-y', float),
            ('angular_velocity-z', float),
            ('orientation-w', float),
            ('orientation-x', float),
            ('orientation-y', float),
            ('orientation-z', float),
            ('air_velocity-x', float),
            ('air_velocity-x', float),
            ('air_velocity-x', float),
            ('ground-velocity-x', float),
            ('ground-velocity-y', float),
            ('ground-velocity-z', float),
            ('position-x', float),
            ('position-y', float),
            ('position-z', float),
        ]

    def get_accepted_commands(self) -> Iterable[Type[Command]]:
        return []

    def collect_measurements(self, now: float, iteration: int) -> Union[None, Sequence[Measurements]]:
        return [[
            *self.angular_velocity,
            *self.orientation,
            *self.air_velocity,
            *self.ground_velocity,
            *self.position
        ]]

    def flush(self):
        pass        
