from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Union
from uuid import UUID
from marshmallow import Schema, fields, validate
from core.helper.json_schema_field import JSON_Schema_Field
from core.helper.model_helper import make_safe_schema

@dataclass
class Command:
    """
    Commands are issued to vessels to make them perform and action
    The vessel's computer has to retrieve them and report if they where
    completed successfully
    """

    _id: UUID
    """
    The id of the command itself. This is to identify the command. Every new subsequent
    command needs a new id to distinguish it
    """

    _command_type: str
    """The code that identifies the command, i.e. what action should be performed"""

    create_time: datetime
    """Time at which the command was created"""

    _part_id: Union[UUID, None] = None
    """
    The id of the part that the command is for (Optional if the command is for the entire vessel)
    """

    dispatch_time: Union[datetime, None] = None
    """
    Time at which the command was dispatched to the vessel
    If not set, the command was not yet dispatched
    """

    receive_time: Union[datetime, None] = None
    """
    Time at which the command was received by the vessel
    If not set, the command was not yet received by the vessel
    """

    complete_time: Union[datetime, None] = None
    """
    Time at which the vessel confirmed the successful or unsuccessful execution of the command
    If not set, the command was yet completed or it failed
    """

    state: str = "new"
    """The state the command is in as known by the server"""

    command_payload: Union[None, Any] = None
    """The payload data of the command. Can be any arbitrary additional data specifying what exactly should happen"""

    response_message: str = ''
    """Free text for a response message. Meant for human readable information"""

    response: Union[None, Any] = None
    """
    Response by the vessel, detailing how the command was processed
    If the the command failed, this should contain the reason why
    """

class CommandSchema(make_safe_schema(Command)):
    """
    Commands are issued to vessels to make them perform and action
    The vessel's computer has to retrieve them and report if they where
    completed successfully
    """

    _id = fields.UUID(required = True)
    """
    The id of the command itself. This is to identify the command. Every new subsequent
    command needs a new id to distinguish it
    """
    
    _command_type = fields.String(required = True)
    """The code that identifies the command, i.e. what action should be performed"""

    create_time = fields.DateTime(required = True, format='iso')
    """Time at which the command was created"""

    _part_id = fields.UUID(allow_none=True)
    """
    The id of the part that the command is for (Optional if the command is for the entire vessel)
    """

    dispatch_time = fields.DateTime(allow_none=True)
    """
    Time at which the command was dispatched to the vessel
    If not set, the command was not yet dispatched
    """

    receive_time = fields.DateTime(allow_none=True)
    """
    Time at which the command was received by the vessel
    If not set, the command was not yet received by the vessel
    """

    complete_time = fields.DateTime(allow_none=True)
    """
    Time at which the vessel confirmed the successful or unsuccessful execution of the command
    If not set, the command was yet completed or it failed
    """

    state = fields.String(required = True, validate= validate.Regexp(r"(new)|(dispatched)|(received)|(success)|(failed)"))
    """The state the command is in as known by the server"""

    command_payload = fields.Raw(allow_none=True)
    """The payload data of the command. Can be any arbitrary additional data specifying what exactly should happen"""
    
    response_message = fields.String()
    """Free text for a response message. Meant for human readable information"""

    response = fields.Raw(allow_none=True)
    """
    Response by the vessel, detailing how the command was processed
    If the the command failed, this should contain the reason why
    """

@dataclass
class CommandInfo:
    """Info on th shape of commands"""

    supported_on_vehicle_level: bool = False
    """This command can be dispatched for the entire vessel without specifying a part"""

    supporting_parts: list[UUID] = field(default_factory=list)
    """All parts that can used for this command"""

    payload_schema: Union[None, dict[str, Any]] = field(default_factory=lambda: None)

    response_schema: Union[None, dict[str, Any]] = field(default_factory=lambda: None)


class CommandInfoSchema(make_safe_schema(CommandInfo)):
    """Info on th shape of commands"""

    supported_on_vehicle_level = fields.Boolean()
    """This command can be dispatched for the entire vessel without specifying a part"""

    supporting_parts = fields.List(fields.UUID)
    """All parts that can receive this command"""

    payload_schema = JSON_Schema_Field(allow_none=True)

    response_schema = JSON_Schema_Field(allow_none=True)
