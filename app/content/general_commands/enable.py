from app.content.general_commands.basic_success_response import BasicErrorResponseSchema
from app.logic.rocket_definition import CommandBase



class EnableCommand(CommandBase):

    command_type = 'Control.Enable'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()


class DisableCommand(CommandBase):

    command_type = 'Control.Disable'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()