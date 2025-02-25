from dataclasses import dataclass
from datetime import datetime
from typing import Any, Union
from marshmallow import fields
from flight_computer.core.helper.model_helper import make_safe_schema

@dataclass
class Command:
    """
    Commands are issued to vessels to make them perform and action. They are fire
    and forget. If a response is required a task should be used
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

    command_payload: Union[None, Any] = None
    """The payload data of the command. Can be any arbitrary additional data specifying what exactly should happen"""


class CommandSchema(make_safe_schema(Command)):
    """
    Commands are issued to vessels to make them perform and action
    The vessel's computer has to retrieve them and report if they where
    completed successfully
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
   
    command_payload = fields.Raw(allow_none=True)
    """The payload data of the command. Can be any arbitrary additional data specifying what exactly should happen"""
  

@dataclass
class CommandInfo:
    """Info on th shape of commands"""

    name: str

    payload_schema: None | str | list[tuple[str, str]]

class CommandInfoSchema(make_safe_schema(CommandInfo)):
    """Info on th shape of commands"""

    name = fields.String(required=True)

    payload_schema = fields.Raw(required=False)
