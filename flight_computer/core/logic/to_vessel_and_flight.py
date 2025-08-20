import struct
from typing import Collection, Tuple, Type
from uuid import uuid4
from flight_computer.core.models.command import CommandInfo
from flight_computer.core.models.flight_measurement import FlightMeasurementDescriptor
from flight_computer.core.models.vessel import Vessel
from flight_computer.core.models.vessel_part import VesselPart
from flight_computer.core.models.flight import Flight
from flight_computer.core.logic.rocket_definition import Rocket
from datetime import UTC, datetime

def to_vessel_and_flight(rocket: Rocket) -> tuple[Vessel, Flight]:

    vessel = Vessel(_id=rocket.id or uuid4(), _version=rocket.version, name=rocket.name, parts=get_all_parts(rocket))

    now = datetime.now(UTC)

    flight = Flight(start=now, _vessel_id=vessel._id, _vessel_version=rocket.version, name=f'Flight at {now.isoformat()}', measured_parts=get_measured_parts(rocket), measured_part_ids=get_measured_part_ids(rocket), available_commands=get_commands(rocket))

    return vessel, flight

def get_all_parts(rocket: Rocket) -> list[VesselPart]:
    all_parts = list[VesselPart]()

    for p in rocket.parts:
        all_parts.append(VesselPart(p._id, p.name, p.type, p.virtual, p.parent._id if p.parent is not None else None))
    
    return all_parts

def get_measured_part_ids(rocket: Rocket) -> dict[int, str]:

    return [p._id for p in rocket.parts]

def get_measured_parts(rocket: Rocket) -> dict[str, list[FlightMeasurementDescriptor]]:

    measured_parts = dict[str, list[FlightMeasurementDescriptor]]()

    for p in rocket.parts:

        measurements = list()

        for measurement_name, qos, measurement_type in p.make_measurement_shape():

            measurements.append(FlightMeasurementDescriptor(measurement_name, make_format_descriptor(measurement_type)))
    
        measured_parts[str(p._id)] = measurements

    return measured_parts

def make_format_descriptor(descriptor: Type | str | Collection[Tuple[str, str | Type]], allow_complex: bool = True):


    if descriptor == str:
        return '[str]'

    if isinstance(descriptor, str):
        if descriptor.startswith('{'):
            raise Exception('Invalid format descriptor: currently not supporting json schemas')
        if descriptor.startswith('['):
            descriptor = descriptor[1:-1]
        try:
            struct.calcsize(descriptor)
            return descriptor
        except Exception as e:
            raise Exception('Descriptor is not a valid struct descriptor', e)
    
    if allow_complex and isinstance(descriptor, Collection) and isinstance(descriptor[0], tuple):
        return [make_format_descriptor(d, False) for d in descriptor]

    if isinstance(descriptor, tuple):
        return (descriptor[0], make_format_descriptor(descriptor[1], False))

        
    raise Exception(f'{descriptor} is not supported as a format')



def get_commands(rocket: Rocket) -> dict[str, list[CommandInfo]]:

    commands = dict[str, list[CommandInfo]]()

    for p in rocket.parts:

        cmds = list()

        for name, type in p.make_accepted_commands():

            cmds.append(CommandInfo(name, make_format_descriptor(type)))
    
        commands[str(p._id)] = cmds

    return commands