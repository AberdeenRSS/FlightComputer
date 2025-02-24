
import time
from uuid import UUID
from flight_computer.core.content.testing.command_tester import CommandTestPart
from flight_computer.core.logic.rocket_definition import Rocket
from tests.helper.offline_env import get_test_vessel_setup
from tests.mock.mock_measurement_sink import MockMeasurementSink



def test_command_pipeline():


    def make_rocket():

        rocket = Rocket('Test Rocket')

        CommandTestPart(UUID('9b289e2f-19b8-4229-9433-7654bfe7f6ef'), 'Command Test', rocket)

        MockMeasurementSink(UUID('4f4c8577-63a7-4239-8570-2e2dec178d95'), 'Mock sink', rocket)

        return rocket

    vessel, flight, executor = get_test_vessel_setup(make_rocket)

    i = 0
    executor.control_loop(i, 0, 1)

    command_test_part = executor.rocket.part_lookup[UUID('9b289e2f-19b8-4229-9433-7654bfe7f6ef')]

    executor.on_command((command_test_part._index, 1, time.time(), 'Some message'))

    executor.control_loop(i, 0, 3)

    measurement_sink: MockMeasurementSink = executor.rocket.part_lookup[UUID('4f4c8577-63a7-4239-8570-2e2dec178d95')]

    measurements = measurement_sink.measurement_buffer[0]

    assert len(measurements[command_test_part]) == 2


