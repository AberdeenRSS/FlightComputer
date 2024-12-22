from core.content.general_commands.basic_success_response import BasicErrorResponseSchema
from core.logic.rocket_definition import Command



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

class SetPreparationPhaseCommand(Command):

    command_type = 'Control.SetPreparationPhase'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()

    def set_payload(self, payload):
        pass

class SetIgnitionPhaseCommand(Command):

    command_type = 'Control.SetIgnitionPhasePhase'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()

    def set_payload(self, payload):
        pass

class SetLiftoffPhaseCommand(Command):

    command_type = 'Control.SetLiftoffPhase'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()

    def set_payload(self, payload):
        pass

class SetRecoveryPhaseCommand(Command):

    command_type = 'Control.SetRecoveryPhase'

    payload_schema = None

    response_schema = BasicErrorResponseSchema()

    def set_payload(self, payload):
        pass