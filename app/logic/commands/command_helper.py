from typing import Union
from app.helper.model_helper import make_safe_schema
from app.logic.commands.command import Command, Command, UnknownCommand
from app.logic.rocket_definition import Rocket
from app.models.command import Command as CommandModel, CommandSchema
from marshmallow import fields


def gather_known_commands(rocket: Rocket):
    res = dict[str, type[Command]]()

    for p in rocket.parts:
        for c in p.get_accepted_commands():
            res[c.command_type] = c
    
    return res

def make_command_schemas(known_commands: dict[str, type[Command]]):

    res = dict[str, CommandSchema]()

    for key, command in known_commands.items():

        class SpecificCommandSchema(CommandSchema, make_safe_schema(command)):

            command_payload = fields.Nested(command.payload_schema) if command.payload_schema is not None else fields.Raw(allow_none=True)

            response = fields.Nested(command.response_schema) if command.response_schema is not None else fields.Raw(allow_none=True)

        res[key] = SpecificCommandSchema()

    return res

def deserialize_command(known_commands: dict[str, type[Command]], model: CommandModel) -> Command:

    constructor = known_commands.get(model._command_type) or UnknownCommand

    command = constructor()

    command._id = model._id
    command.state = model.state
    command._part_id = model._part_id
    command.create_time = model.create_time
    command.dispatch_time = model.dispatch_time
    command.receive_time = model.receive_time
    command.complete_time = model.complete_time

    if constructor.payload_schema is not None and model.command_payload is not None:
        command.set_payload(constructor.payload_schema.load(model.command_payload))

    return command
