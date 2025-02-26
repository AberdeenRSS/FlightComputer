

import time
from uuid import UUID
from flight_computer.core.content.raspberry.i2c import RaspberryI2CInterface
from flight_computer.core.content.raspberry.i2c_devices.bno055 import BNO055_Raspberry
from flight_computer.core.logic.rocket_definition import Rocket
from tests.helper.offline_env import get_test_vessel_setup
from tests.mock.mock_measurement_sink import MockMeasurementSink


async def test_bno055():


    rocket = Rocket('Test Rocket')

    MockMeasurementSink(UUID('4f4c8577-63a7-4239-8570-2e2dec178d95'), 'Mock sink', rocket)
    i2c = RaspberryI2CInterface(UUID('ef616406-fe02-4282-9f7d-d8238be9e17c'), 'I2C', rocket)
    bno055 = BNO055_Raspberry(UUID('49d9ae27-13a2-4d3a-b751-09fc52b5bd77'), 'Bno055', rocket, i2c)

    def make_rocket():
        return rocket

    vessel, flight, executor = get_test_vessel_setup(make_rocket)

    # Run for 30s
    await executor.run_control_loop(until=time.time() + 30)