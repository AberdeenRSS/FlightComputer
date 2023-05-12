import json
import time
from unittest import TestCase, main
import uuid

from app.content.sensors.android_native.acceleration_pyjinius import PyjiniusAccelerationSensor
from app.content.sensors.android_native.gyroscope_pyjinius import PyjiniusGyroscopeSensor
from app.content.sensors.android_native.inertial_reference_frame import InertialReferenceFrame

class TestInertialReferenceFrame(TestCase):

    def test_calculation(self):

        acc = PyjiniusAccelerationSensor(uuid.uuid4(), 'Dummy Accelerometer', None, True)
        gyro = PyjiniusGyroscopeSensor(uuid.uuid4(), 'Dummy Gryo', None, True)

        inertial_frame = InertialReferenceFrame(acc, gyro, uuid.uuid4(), 'Inertial frame', None)

        # 1. Set acceleration data on each low level sensor
        now = time.time()
        acc.last_update = now
        acc.last_measurement = now
        acc.iteration_acceleration = [ (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0) ]

        gyro.last_update = now
        gyro.last_measurement = now
        gyro.iteration_angular_acceleration = [ (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0) ]

        inertial_frame.update([], now, 1)

        # Advance time by one second
        now += 1

        acc.last_update = now
        acc.last_measurement = now
        acc.iteration_acceleration = [ (0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 0) ]

        gyro.last_update = now
        gyro.last_measurement = now
        gyro.iteration_angular_acceleration = [ (0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 0) ]

        inertial_frame.update([], now, 2)

        assert inertial_frame.air_velocity is not None
        assert inertial_frame.angular_velocity is not None

        serialized_air_velocity = json.dumps([*inertial_frame.air_velocity])
        serialized_ground_velocity = json.dumps([*inertial_frame.ground_velocity])
        serialized_position = json.dumps([*inertial_frame.position])
        serialized_angular_velocity = json.dumps([*inertial_frame.angular_velocity])
        serialized_orientation = json.dumps([*inertial_frame.orientation])


if __name__ == '__main__':
    main()