from app.content.general_commands.basic_success_response import BasicErrorResponseSchema
from app.logic.rocket_definition import Command

class StartCountDownCommand(Command):
    '''
    Starts the countdown for the launch
    '''

    command_type = 'Control.Start_Countdown'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()

    def set_payload(self, payload):
        pass

