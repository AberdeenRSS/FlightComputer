from abc import ABC
from typing import Union

from app.helper.model_helper import SchemaExt


class CommandBase(ABC):
    ''' Base class for commands. Used to define what the command looks like'''

    command_type: str

    payload_schema: Union[SchemaExt, None]

    response_schema: Union[SchemaExt, None]


class Command(CommandBase):

    state: str = 'new'