from core.content.general_commands.basic_success_response import BasicErrorResponseSchema
from core.logic.rocket_definition import Command

class AbortCommand(Command):
    '''
    Aborts the launch
    '''

    command_type = 'Control.Abort'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()

    def set_payload(self, payload):
        pass

