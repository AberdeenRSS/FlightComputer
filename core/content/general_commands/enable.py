from app.content.general_commands.basic_success_response import BasicErrorResponseSchema
from app.logic.rocket_definition import Command



class EnableCommand(Command):

    command_type = 'Control.Enable'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()

    def set_payload(self, payload):
        pass


class DisableCommand(Command):

    command_type = 'Control.Disable'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()

    def set_payload(self, payload):
        pass

class ResetCommand(Command):

    command_type = 'Control.Reset'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()

    def set_payload(self, payload):
        pass