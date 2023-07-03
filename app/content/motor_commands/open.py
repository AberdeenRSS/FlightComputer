from app.content.general_commands.basic_success_response import BasicErrorResponseSchema
from app.logic.rocket_definition import Command



class OpenCommand(Command):

    command_type = 'Control.Open'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()

    def set_payload(self, payload):
        pass


class CloseCommand(Command):

    command_type = 'Control.Close'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()

    def set_payload(self, payload):
        pass

class IgniteCommand(Command):

    command_type = 'Control.Ignite'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()

    def set_payload(self, payload):
        pass