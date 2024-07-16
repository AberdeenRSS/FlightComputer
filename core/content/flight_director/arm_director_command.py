from app.content.general_commands.basic_success_response import BasicErrorResponseSchema
from app.logic.rocket_definition import Command

class ArmDirectorCommand(Command):
    '''
    Arms the part
    '''

    command_type = 'Control.Arm'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()

    def set_payload(self, payload):
        pass

