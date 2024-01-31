from asyncio import Future, Task
from datetime import timedelta
from typing import Collection, Iterable, Tuple, Type, Union, cast
from uuid import UUID

from dataclasses import dataclass
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.content.motor_commands.open import OpenCommand, CloseCommand
from app.logic.commands.command import Command
from app.content.microcontroller.arduino_serial import ArduinoSerial
from app.logic.commands.command_helper import is_new_command
from app.logic.rocket_definition import Part, Rocket


class ServoSensor(Part):
    type = 'Servo'

    enabled: bool = True

    min_update_period = timedelta(milliseconds=200)

    min_measurement_period = timedelta(milliseconds=1000)

    arduino: Union[ArduinoSerial, None]

    state: str

    last_ignite_future: Union[Future, None] = None

    last_command: Union[None, Command] = None

    commandList : dict()

    partID : chr

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], arduino_parent: Union[ArduinoSerial, None],start_enabled=True):
        self.arduino = arduino_parent
        self.enabled = start_enabled
        self.state = 'close'
        super().__init__(_id, name, parent, list())  # type: ignore

        self.partID = 1
        self.commandList = { 'Close' : 0, 'Open' : 1 }
        self.arduino.addCallback(self.partID, self.proccessCommand)

    def proccessCommand(self, command : Command):
        command.response_message = 'Servo activated'

        print("ssssssssss")

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [DisableCommand, EnableCommand, OpenCommand, CloseCommand]

    def update(self, commands: Iterable[Command], now, iteration):

        for c in commands:

            if self.arduino is None:
                c.state = 'failed'
                c.response_message = 'No arduino connected'
                continue

            if c.state == 'processing' and self.last_command != c:
                c.state = 'failed'
                c.response_message = 'Another ignite command was send, this command will no longer be processed'
                continue

            if c.state == 'processing':
                print("jas")
                continue



            if isinstance(c, CloseCommand):

                if is_new_command(c):
                    self.last_command = c
                    self.last_ignite_future = self.arduino.send_message(self.partID, self.commandList["Close"])

                    self.arduino.commandProccessingDict[self.last_ignite_future.result()] = c
                    c.state = 'processing'

            elif isinstance(c, OpenCommand):

                if is_new_command(c):
                    self.last_command = c
                    self.last_ignite_future = self.arduino.send_message(self.partID, self.commandList["Open"])

                    self.arduino.commandProccessingDict[self.last_ignite_future.result()] = c
                    c.state = 'processing'


            else:
                c.state = 'failed'  # Part cannot handle this command
                continue


    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', int),
            ('communication_failure', int),
            ('last_packet_index', int)
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[Union[int, int]]]:
        return [[1 if self.enabled else 0, 1 if self.state is 'open' else 0]]

