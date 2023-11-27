from asyncio import Future
from datetime import timedelta
from typing import Iterable, Tuple, Type, Union
from uuid import UUID

from app.content.motor_commands.open import IgniteCommand
from app.content.microcontroller.arduino.parts.servo import ServoSensor
from app.logic.commands.command import Command
from app.content.microcontroller.arduino_serial import ArduinoSerial
from app.logic.rocket_definition import Part, Rocket


class IgniterSensor(Part):
    type = 'Igniter'

    enabled: bool = True

    min_update_period = timedelta(milliseconds=100)

    min_measurement_period = timedelta(milliseconds=1000)

    arduino: Union[ArduinoSerial, None]

    last_ignite_future: Union[Future, None] = None

    last_command: Union[None, Command] = None

    last_ignited: Union[float, None] = None

    parachute_triggered = False

    deploy_parachute_delay = 35

    state: str

    commandList : dict()

    commandProccessingDict : dict()

    partID : chr

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], arduino_parent: Union[ArduinoSerial, None], parachute: ServoSensor, start_enabled=True):
        self.arduino = arduino_parent
        self.enabled = start_enabled
        self.state = 'ready'
        self.parachute = parachute
        super().__init__(_id, name, parent, list())  # type: ignore

        self.partID = 2
        self.commandList = { 'Ignite' : 0 }

        self.commandProccessingDict = dict()
        self.arduino.addCallback(self.partID, self.proccessCommand)

    def proccessCommand(self, index : int, result : int):
        print(index, result)
        command = self.commandProccessingDict[index]
        if result == 0:
            command.state = 'success'
            command.response_message = 'Ignited'

            self.arduino.launchPhase = 'LiftOff'
        else:
            command.state = 'failed'
            command.response_message = self.arduino.errorMessageDict[result]

        self.commandProccessingDict.pop(index)

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [IgniteCommand]

    def update(self, commands: Iterable[Command], now, iteration):
        for c in commands:
            if isinstance(c, IgniteCommand):

                if self.arduino is None:
                    c.state = 'failed'
                    c.response_message = 'No arduino connected'
                    continue

                if c.state == 'received':
                    self.last_command = c
                    self.last_ignite_future = self.arduino.send_message(self.partID, self.commandList['Ignite'])
                    self.last_ignited = now
                    self.parachute_triggered = False

                    self.commandProccessingDict[self.last_ignite_future.result()] = c
                    c.state = 'processing'


                if c.state == 'processing' and self.last_command != c:
                    c.state = 'failed'
                    c.response_message = 'Another ignite command was send, this command will no longer be processed'
                    continue



            else:
                c.state = 'failed'  # Part cannot handle this command
                continue

        if self.arduino is not None and self.last_ignited is not None and not self.parachute_triggered and (now - self.last_ignited) >= self.deploy_parachute_delay:

            self.parachute_triggered = True
            self.arduino.send_message(self.parachute.partID, self.parachute.commandList['Open'])


    # def add_command_to_queue(command_code: int, payload):

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', int),
            ('Ignited', int),
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[Union[int, int]]]:
        return [[1 if self.enabled else 0, 1 if self.state is 'ignited' else 0]]
