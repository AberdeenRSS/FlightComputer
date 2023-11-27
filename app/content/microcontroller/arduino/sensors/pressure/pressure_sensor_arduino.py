from datetime import timedelta
from typing import Iterable, Tuple, Type, Union
from uuid import UUID

from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.commands.command import Command
from app.content.microcontroller.arduino_serial import ArduinoSerial
from app.content.microcontroller.arduino.sensors.pressure.temperature_arduino import TemperatureSensor
from app.content.microcontroller.arduino.sensors.pressure.pressure_arduino import PressureSensor
from app.content.microcontroller.arduino.sensors.pressure.altitude_arduino import AltitudeSensor
from app.logic.rocket_definition import Part, Rocket

class PressureArduinoSensor(Part):
    type = 'PressureArduinoSensor'

    enabled: bool = True

    min_update_period = timedelta(milliseconds=20)

    min_measurement_period = timedelta(milliseconds=1000)

    sensorsList : list()

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], arduino : ArduinoSerial,
                 temperatureSensor : TemperatureSensor, pressureSensor : PressureSensor,
                 altitudeSensor : AltitudeSensor, start_enabled=True):

        self.enabled = start_enabled

        super().__init__(_id, name, parent, list())  # type: ignore

        partID = 0x53

        self.sensorsList = []
        self.sensorsList.append(temperatureSensor)
        self.sensorsList.append(pressureSensor)
        self.sensorsList.append(altitudeSensor)

        arduino.addCallback(partID, self.set_measurements)


    def set_measurements(self, dataList : list[int]):
        self.sensorsList[0].temperature = dataList[0]
        self.sensorsList[1].pressure = dataList[1]
        self.sensorsList[2].altitude = dataList[2]

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [EnableCommand, DisableCommand]

    def update(self, commands: Iterable[Command], now, iteration):
        for c in commands:

            if isinstance(c, EnableCommand):
                self.enabled = True
                c.state = "success"

            elif isinstance(c, DisableCommand):
                self.enabled = False
                c.state = "success"


    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return []

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[float]]:
        return [[]]

