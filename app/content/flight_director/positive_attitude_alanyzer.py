# from asyncio import Future, Task
# from datetime import timedelta
# import struct
# from typing import Collection, Iterable, Tuple, Type, Union, cast
# from uuid import UUID

# from scipy.spatial.transform import Rotation

# from dataclasses import dataclass
# from app.content.common_sensor_interfaces.orientation_sensor import IOrientationSensor
# from app.content.general_commands.enable import DisableCommand, EnableCommand
# from app.logic.commands.command import Command
# from app.content.microcontroller.arduino_serial import ArduinoOverSerial
# from app.logic.rocket_definition import Part, Rocket

# class PositiveAttitudeAnalyzer(Part):
#     type = 'Analyzer.Attitude.Absolute'

#     enabled: bool = True

#     min_update_period = timedelta(milliseconds=20)

#     min_measurement_period = timedelta(milliseconds=50)

#     orientation_sensor: IOrientationSensor

#     pointing_up: int
#     '''
#     1 -> pointing up
#     0 -> unknown/in between (depends on dead zones defined)
#     -1 -> pointing down
#     '''

#     def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], orientation_sensor: IOrientationSensor):

#         self.orientation_sensor = orientation_sensor

#         super().__init__(_id, name, parent, [orientation_sensor])   # type: ignore

#     def get_accepted_commands(self) -> list[Type[Command]]:
#         return []

#     def update(self, commands: Iterable[Command], now, iteration):

#         orientation = self.orientation_sensor.get_orientation()

#         if orientation is None:
#             self.pointing_up = 0
#             return

#         r = Rotation.from_quat([orientation[1], orientation[2], orientation[3], orientation[0]]) #Order needs to be swapped as scipy quaternions are x, y, z, w

#         up_vector = [0, 0, 1]

#         pointing_vector = r.apply(up_vector)

#         self.pointing_up = 1 if pointing_vector[2] > 0 else -1
        


#     def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
#         return [
#             ('pointing_up', int)
#         ]

#     def collect_measurements(self, now, iteration) -> Iterable[Iterable[float]]:
#         return [[self.pointing_up]]

