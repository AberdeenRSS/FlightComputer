from app.content.general_commands.basic_success_response import BasicErrorResponseSchema
from app.logic.rocket_definition import Command



class CalibrateZeroCommand(Command):
    '''
    Calbirates any sensor at it's respective zero position.
    I.e. zeoring a velocity sensor would calibrate it to be at rest
    When this command is issued it is important that the device is in that
    repective zero postion, otherwise the data will get messed up  
    '''

    command_type = 'Calibrate.Zero'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()

    def set_payload(self, payload):
        pass

