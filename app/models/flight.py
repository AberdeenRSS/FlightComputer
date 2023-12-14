from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Union
from uuid import UUID, uuid4
from marshmallow import Schema, fields
from app.models.flight_measurement import FlightMeasurementDescriptor
from app.models.command import CommandInfo, CommandInfoSchema
from app.models.flight_measurement import FlightMeasurementDescriptorSchema
from app.helper.model_helper import make_safe_schema

FLIGHT_DEFAULT_HEAD_TIME = timedelta(minutes=2)
"""
A flight that is still ongoing gets this amount of time
added to its end time from utcnow by default
"""

FLIGHT_MINIMUM_HEAD_TIME = timedelta(minutes=1)
"""
This is the minimum time the end of a flight can be ahead,
before it needs to be extended
"""

@dataclass
class Flight:

    start: datetime
    """
    When the flight started
    """

    _id: UUID = uuid4()
    """
    The id of the flight. (Primary identifier)
    """

    _vessel_id: UUID = UUID(int=0)
    """
    The id of the vessel that is performing this flight
    """

    _vessel_version: int = 0
    """
    The version of the vessel this flight was based on
    This is important if the vessel gets modified later to make
    sure all the flight information can still be matched up accordingly
    """

    name: str = ""

    end: Union[datetime, None] = None
    """
    When the flight ended
    """

    measured_parts: dict[str, list[FlightMeasurementDescriptor]] = field(default_factory=dict)
    """
    The list of vessel parts that have measurements for and how those measurements will look like
    """

    available_commands: dict[str, CommandInfo] = field(default_factory=dict)
    """
    List of available commands and their json schemas. The keys have to be the part the command is issued to
    """

    permissions: dict[str, str] = field(default_factory=dict)
    """
    User id permission pairs of who has what permission on the vessel
    """

    no_auth_permission: Union[None, str] = 'owner'
    """
    The permission everyone has regardless of if they are logged in or not
    """

class FlightSchema(make_safe_schema(Flight)):

    _id = fields.UUID(required = False)
    """
    The id of the flight. (Primary identifier)
    """

    _vessel_id = fields.UUID(required = False)
    """
    The id of the vessel that is performing this flight
    """

    _vessel_version = fields.Int(required = False)
    """
    The version of the vessel this flight was based on
    This is important if the vessel gets modified later to make
    sure all the flight information can still be matched up accordingly
    """

    name = fields.Str()

    start = fields.AwareDateTime(required = True, default_timezone=timezone.utc, )
    """
    When the flight started
    """

    end = fields.AwareDateTime(allow_none = True, default_timezone=timezone.utc)
    """
    When the flight ended
    """

    measured_parts = fields.Dict(keys= fields.Str(), values= fields.List(fields.Nested(FlightMeasurementDescriptorSchema)))
    """
    The list of vessel parts that have measurements for and how those measurements will look like
    """

    available_commands = fields.Dict(keys= fields.Str(), values= fields.Nested(CommandInfoSchema))
    """
    List of available commands and their json schemas. The keys have to be the part the command is issued to
    """

    permissions = fields.Dict(keys=fields.String(), values=fields.String())
    """
    User id permission pairs of who has what permission on the vessel
    """

    no_auth_permission = fields.String()
    """
    The permission everyone has regardless of if they are logged in or not
    """
