from abc import ABC, abstractclassmethod
from datetime import datetime
from typing import Union
from uuid import UUID

from app.helper.model_helper import SchemaExt


class Command(ABC):
    ''' Base class for commands. Used to define what the command looks like'''

    _id: UUID

    command_type: str

    _command_type: str

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

    payload_schema: Union[SchemaExt, None]

    response_message: str = ''

    response_schema: Union[SchemaExt, None]
    
    state: str = 'new'
    '''
    - "new" or "dispatched" or "received" if received from the server
    - "processing" if currently processing this command
    - "success" or "failed" to send back to the server
    '''

    @abstractclassmethod
    def set_payload(self, payload):
        ''' called to deserialize the payload of the command. Payload is deserialized'''
        pass

    def __init__(self) -> None:
        super().__init__()

        self._command_type = self.command_type


class UnknownCommand(Command):

    command_type = 'Unknown'

    payload_schema = None

    response_schema = None

    def set_payload(self, payload):
        pass