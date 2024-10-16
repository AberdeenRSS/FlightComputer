from typing import Type
from uuid import UUID
from core.logic.rocket_definition import Command
from core.models.command import CommandInfo
from core.models.flight_measurement import FlightMeasurementDescriptor
from core.models.vessel import Vessel
from core.models.vessel_part import VesselPart
from core.models.flight import Flight
from core.logic.rocket_definition import Rocket
from datetime import UTC, datetime
from marshmallow_jsonschema_3 import JSONSchema

def to_vessel_and_flight(rocket: Rocket) -> tuple[Vessel, Flight]:

    vessel = Vessel(_id=rocket.id or UUID(), _version=rocket.version, name=rocket.name, parts=get_all_parts(rocket))

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

        for measurement_name, measurement_type in p.get_measurement_shape():

            measurements.append(FlightMeasurementDescriptor(measurement_name, measurement_type))
    
        measured_parts[str(p._id)] = measurements

    return measured_parts

def get_commands(rocket: Rocket) -> dict[str, CommandInfo]:

    commands = dict[Type[Command], list[UUID]]()

    res = dict[str, CommandInfo]()

    for p in rocket.parts:
        for c in p.get_accepted_commands():

            if c not in commands:
                commands[c] = list()
            commands[c].append(p._id)

    for command, part_ids in commands.items():

        payload_schema = JSONSchema().dump(command.payload_schema) if command.payload_schema is not None else None
        response_schema = JSONSchema().dump(command.response_schema) if command.response_schema is not None else None

        res[command.command_type] = CommandInfo(supporting_parts=part_ids, payload_schema=payload_schema, response_schema=response_schema) # type: ignore
    
    return res
