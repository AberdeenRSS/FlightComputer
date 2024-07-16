from asyncio import Future, Task
from datetime import timedelta
from typing import Collection, Iterable, Tuple, Type, Union, cast
from uuid import UUID

from dataclasses import dataclass
from core.content.general_commands.enable import DisableCommand, EnableCommand
from core.content.microcontroller.arduino_serial_common import ArduinoHwBase
from core.content.motor_commands.open import OpenCommand, CloseCommand
from core.logic.commands.command import Command
from core.content.microcontroller.arduino_serial import ArduinoOverSerial, make_default_command_callback
from core.logic.commands.command_helper import is_new_command
from core.logic.rocket_definition import Part, Rocket


class ServoSensor(Part):
    type = 'Servo'

    enabled: bool = True

    min_update_period = timedelta(milliseconds=50)

    min_measurement_period = timedelta(milliseconds=1000)

    arduino: Union[ArduinoHwBase, None]

    state: str

    commandList: dict = { 'Close' : 0, 'Open' : 1 }

    partID: int = 1

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], arduino_parent: ArduinoHwBase, start_enabled=True):
        self.arduino = arduino_parent
        self.enabled = start_enabled
        self.state = 'close'
        super().__init__(_id, name, parent, list())  # type: ignore


    def proccessCommand(self, command : Command):
        command.response_message = 'Servo activated'

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [DisableCommand, EnableCommand, OpenCommand, CloseCommand]
    
    def make_command_callback(self, c: Command):

        def reset_callback(res: Future[int]):
            exception = res.exception()
            if exception is not None:
                c.state = 'failure'
                c.response_message  = exception.args[0]
                return
            
            c.state = 'success'
        
        return reset_callback

    def update(self, commands: Iterable[Command], now, iteration):

        for c in commands:

            if self.arduino is None:
                c.state = 'failed'
                c.response_message = 'No arduino connected'
                continue

            if isinstance(c, CloseCommand):

                if is_new_command(c):
                    future = self.arduino.serial_adapter.send_message(self.partID, self.commandList["Close"])
                    future.add_done_callback(make_default_command_callback(c))
                    c.state = 'processing'

            elif isinstance(c, OpenCommand):

                if is_new_command(c):
                    future = self.arduino.serial_adapter.send_message(self.partID, self.commandList["Open"])
                    future.add_done_callback(make_default_command_callback(c))
                    c.state = 'processing'

            else:
                c.state = 'failed'  # Part cannot handle this command
                continue


    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', '?'),
            ('communication_failure', '?')
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[Union[int, int]]]:
        return [[self.enabled, self.state == 'failure']]

