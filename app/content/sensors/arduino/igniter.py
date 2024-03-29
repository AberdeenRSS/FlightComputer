from asyncio import Future, Task
from datetime import timedelta
from typing import Collection, Iterable, Tuple, Type, Union, cast
from uuid import UUID

from dataclasses import dataclass
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.content.motor_commands.open import OpenCommand, CloseCommand, IgniteCommand
from app.content.sensors.arduino.servo import ServoSensor
from app.logic.commands.command import Command, Command
from app.content.general_commands.enable import DisableCommand, EnableCommand, ResetCommand
from app.content.microcontroller.arduino_serial import ArduinoSerial
from app.logic.commands.command_helper import is_new_command
from app.logic.rocket_definition import Part, Rocket

from kivy.utils import platform


class IgniterSensor(Part):
    type = 'Igniter'

    enabled: bool = True

    min_update_period = timedelta(milliseconds=20)

    min_measurement_period = timedelta(milliseconds=1000)

    arduino: Union[ArduinoSerial, None]

    last_ignite_future: Union[Future, None] = None

    last_command: Union[None, Command] = None

    last_ignited: Union[float, None] = None

    parachute_triggered = False

    deploy_parachute_delay = 35

    state: str

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], arduino_parent: Union[ArduinoSerial, None], parachute: ServoSensor, start_enabled=True):
        self.arduino = arduino_parent
        
        self.enabled = start_enabled
        self.state = 'ready'
        self.parachute = parachute
        super().__init__(_id, name, parent, list())  # type: ignore


    def get_accepted_commands(self) -> list[Type[Command]]:
        return [IgniteCommand]

    def update(self, commands: Iterable[Command], now, iteration):
        for c in commands:
            if isinstance(c, IgniteCommand):

                if self.arduino is None:
                    c.state = 'failed'
                    c.response_message = 'No arduino connected'
                    continue

                if is_new_command(c):
                    self.last_command = c
                    self.last_ignite_future = self.arduino.send_message(0x02, 0x01)
                    self.last_ignited = now
                    self.parachute_triggered = False
                    c.state = 'processing'

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
                    c.response_message = 'Igniter triggered'

            else:
                c.state = 'failed'  # Part cannot handle this command
                continue

        if self.arduino is not None and self.last_ignited is not None and not self.parachute_triggered and (now - self.last_ignited) >= self.deploy_parachute_delay:

            self.parachute_triggered = True
            self.arduino.send_message(0x01, 0x04)


    # def add_command_to_queue(command_code: int, payload):

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', int),
            ('Ignited', int),
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[Union[int, int]]]:
        return [[1 if self.enabled else 0, 1 if self.state is 'ignited' else 0]]
