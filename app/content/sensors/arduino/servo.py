from asyncio import Future, Task
from datetime import timedelta
from typing import Collection, Iterable, Tuple, Type, Union, cast
from uuid import UUID

from dataclasses import dataclass
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.content.motor_commands.open import OpenCommand, CloseCommand, IgniteCommand
from app.logic.commands.command import Command, Command
from app.content.general_commands.enable import DisableCommand, EnableCommand, ResetCommand
from app.content.microcontroller.arduino_serial import ArduinoSerial
from app.logic.rocket_definition import Part, Rocket

from kivy.utils import platform


class ServoSensor(Part):
    type = 'Servo'

    enabled: bool = True

    min_update_period = timedelta(milliseconds=20)

    min_measurement_period = timedelta(milliseconds=1000)

    arduino: Union[ArduinoSerial, None]

    state: str

    last_ignite_future: Union[Future, None] = None

    last_command: Union[None, Command] = None

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], arduino_parent: Union[ArduinoSerial, None],start_enabled=True):
        self.arduino = arduino_parent
        self.enabled = start_enabled
        self.state = 'close'
        super().__init__(_id, name, parent, list())  # type: ignore


    def get_accepted_commands(self) -> list[Type[Command]]:
        return [OpenCommand, CloseCommand]

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

            if c.state == 'processing' and self.last_ignite_future is not None and self.last_ignite_future.done():
                exception = self.last_ignite_future.exception()
                if exception is not None:
                    c.state = 'failed'
                    c.response_message = exception.args[0]
                    continue
                c.state = 'success'
                c.response_message = 'Servo actuated'

            if isinstance(c, CloseCommand):

                if c.state == 'received':
                    self.last_command = c
                    self.last_ignite_future = self.arduino.send_message(0x01, 0x03)
                    c.state = 'processing'

            elif isinstance(c, OpenCommand):

                if c.state == 'received':
                    self.last_command = c
                    self.last_ignite_future = self.arduino.send_message(0x01, 0x04)
                    c.state = 'processing'

            else:
                c.state = 'failed'  # Part cannot handle this command
                continue

    # def add_command_to_queue(command_code: int, payload):

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', int),
            ('communication_failure', int),
            ('last_packet_index', int)
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[Union[int, int]]]:
        return [[1 if self.enabled else 0, 1 if self.state is 'open' else 0]]

