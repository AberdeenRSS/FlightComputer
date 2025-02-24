from logging import _nameToLevel, getLogger
import os
from typing import Callable

from flight_computer.core.flight_executer import FlightExecuter
from flight_computer.core.helper.global_data_dir import set_user_data_dir
from flight_computer.core.logic.rocket_definition import Rocket
from flight_computer.core.logic.to_vessel_and_flight import to_vessel_and_flight

def get_test_vessel_setup(vessel_creation_method: Callable[..., Rocket]):

    cur_dir = os.path.dirname(os.path.realpath(__file__))

    set_user_data_dir(f'{cur_dir}/logs')
    getLogger().setLevel(_nameToLevel['INFO'])

    rocket = vessel_creation_method()

    vessel, flight = to_vessel_and_flight(rocket)

    executor = FlightExecuter(rocket, flight, None, None)

    return vessel, flight, executor

