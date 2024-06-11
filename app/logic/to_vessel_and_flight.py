from typing import Type
from uuid import UUID
from app.logic.rocket_definition import Command
from app.models.command import CommandInfo
from app.models.flight_measurement import FlightMeasurement, FlightMeasurementDescriptor
from app.models.vessel import Vessel
from app.models.vessel_part import VesselPart
from app.models.flight import Flight
from app.logic.rocket_definition import Rocket
from datetime import datetime, timezone
from marshmallow_jsonschema import JSONSchema

def to_vessel_and_flight(rocket: Rocket) -> tuple[Vessel, Flight]:

    vessel = Vessel(_id=rocket.id or UUID(), _version=rocket.version, name=rocket.name, parts=get_all_parts(rocket))

    now = datetime.utcnow()
    now = now.replace(tzinfo=timezone.utc)

    flight = Flight(start=now, _vessel_id=vessel._id, _vessel_version=rocket.version, name=f'FLight at {now.isoformat()}', measured_parts=get_measured_parts(rocket), available_commands=get_commands(rocket))

    return vessel, flight

def get_all_parts(rocket: Rocket) -> list[VesselPart]:
    all_parts = list[VesselPart]()

    for p in rocket.parts:
        all_parts.append(VesselPart(p._id, p.name, p.type, p.virtual, p.parent._id if p.parent is not None else None))
    
    return all_parts

def get_measured_parts(rocket: Rocket) -> dict[str, list[FlightMeasurementDescriptor]]:

    measured_parts = dict[str, list[FlightMeasurementDescriptor]]()

    for p in rocket.parts:

        measurements = list()

        for measurement_name, measurement_type in p.get_measurement_shape():

            m_type = None

            if measurement_type == float:
                m_type = 'float'
            elif measurement_type == str:
                m_type = 'string'
            elif measurement_type == bool:
                m_type = 'boolean'
            elif measurement_type == int:
                m_type = 'int'
            else:
                raise TypeError(f'Type {str(measurement_type)} is not supported as a measurement value')

            measurements.append(FlightMeasurementDescriptor(measurement_name, m_type))
    
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
