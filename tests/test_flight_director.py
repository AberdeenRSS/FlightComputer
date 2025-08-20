
import time
from typing import cast
from uuid import UUID
from flight_computer.core.content.flight_director.simple_flight_director import SimpleFlightDirector
from flight_computer.core.content.testing.command_tester import CommandTestPart
from flight_computer.core.content.testing.mock_altimeter import MockAltimeter
from flight_computer.core.logic.rocket_definition import Rocket
from tests.helper.offline_env import get_test_vessel_setup
from tests.mock.mock_measurement_sink import MockMeasurementSink



def test_flight_director():


    def make_rocket():

        rocket = Rocket('Test Rocket')


        MockMeasurementSink(UUID('4f4c8577-63a7-4239-8570-2e2dec178d95'), 'Mock sink', rocket)

        altimeter = MockAltimeter(UUID('5b213500-8e8e-4375-bf5d-2dac477db8a4'), 'Mock altimeter', rocket)

        SimpleFlightDirector(UUID('b95dda37-c592-48ac-8658-e053f6d60045'), 'Simple flight director', rocket, altimeter, None, None)

        return rocket

    vessel, flight, executor = get_test_vessel_setup(make_rocket)


    altimeter = cast(MockAltimeter, executor.rocket.part_lookup[UUID('5b213500-8e8e-4375-bf5d-2dac477db8a4')])
    measurement_sink = cast(MockMeasurementSink,  executor.rocket.part_lookup[UUID('4f4c8577-63a7-4239-8570-2e2dec178d95')])
    flight_director = cast(SimpleFlightDirector, executor.rocket.part_lookup[UUID('b95dda37-c592-48ac-8658-e053f6d60045')])

    altimeter.simulate_flight(0, 3, 50, 200, 15, 50)
    flight_director.arm(0, None)

    dt = 0.1
    t = 0
    i = 0 
    while altimeter.in_flight:

        if i > 100000:
            raise Exception(f'reached iteration {i} without landing, something is wrong...')
        
        old_time = t
        t += dt

        executor.control_loop(i, old_time, t)

    assert(flight_director.flight_phase == 6)

    # measurements = measurement_sink.measurement_buffer[0]

    # assert len(measurements[command_test_part]) == 2


