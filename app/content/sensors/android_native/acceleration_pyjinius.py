from time import sleep
from datetime import timedelta
from typing import Iterable, Tuple, Type, Union, cast
from typing_extensions import Self
from uuid import UUID
from app.content.general_commands.calibrate import CalibrateZeroCommand
from app.logic.calibration.calibration_processor import CalibrationProcessor3D, SimpleCalibrationProcessor3D
from app.logic.commands.command import Command
from app.content.general_commands.enable import DisableCommand, EnableCommand
from app.logic.rocket_definition import Command, Part, Rocket
from kivy.utils import platform

if platform == 'android':
    # from android.permissions import request_permissions, Permission
    from jnius import autoclass


class PyjiniusAccelerationSensor(Part):

    #region Config

    type = 'Sensor.Acceleration'

    min_update_period = timedelta(milliseconds=10)

    min_measurement_period = timedelta(milliseconds=10)

    status_data_rate = 1_000

    calibration_duration = 5
    ''' Calibration duraiton in seconds '''

    #endregion

    #region Status

    enabled: bool = True

    sensor_failed: bool = False

    last_calibrated: Union[float, None] = None
    ''' Unix datetime when the last sensor calibration started '''

    calibration_command: Union[CalibrateZeroCommand, None] = None

    correction = [0, 0, 0]
    ''' Correction value form calibration process'''

    #endregion 

    #region Sensor Data

    calibration_proccessor: Union[CalibrationProcessor3D, None] = None

    acceleration: Union[None, Tuple[float, float, float]]

    accuracy: Union[int, None] = None

    iteration_acceleration: Union[None, list[Tuple[float, float, float]]] = None

    iteration_accuracy: Union[int, None] = None

    #endregion

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled
        self.try_enable(self.enabled)

        super().__init__(_id, name, parent, list()) # type: ignore

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [EnableCommand, DisableCommand, CalibrateZeroCommand]
    
    def try_enable(self, enable: bool) -> bool:
        try:
            self.hardware = autoclass('org.rss.Accelerometer')
            self.hardware.accelerometerEnable(enable)
        except Exception as e:
            self.sensor_failed = True
            print(f'Plyer gravity sensor failed: {e}')
            return False
    
        return True
    
    def process_calibration(self, command: CalibrateZeroCommand, now: float):
        
        # New calibration command
        if self.calibration_command is None or self.calibration_command != command:
            # Set the old one to failed if ther was one currently being processed
            if self.calibration_command is not None:
                self.calibration_command.state = 'failed'
                self.calibration_command.response_message = 'Calibration was aborted as another calibration command was received'
            self.calibration_command = command
            self.last_calibrated = now
            self.calibration_proccessor = SimpleCalibrationProcessor3D()
            command.state = 'processing'
            return

        # Still processing the calibration request (need to collect data for longer)
        if self.last_calibrated is not None and now < self.last_calibrated + self.calibration_duration:
            return

        if self.calibration_proccessor:
            self.correction = self.calibration_proccessor.get_correction()

        del self.calibration_proccessor
        del self.calibration_command

        command.state = 'success'
        command.response_message = f'Successfully calbirated sensor. Calibraiton values: {self.correction}'
   
    def update(self, commands: Iterable[Command], now, iteration):
        
        for c in commands:
            if isinstance(c, EnableCommand):
                success = self.try_enable(True)
                c.state = 'success' if success else 'failed'
                c.response_message = 'Successfully enabled accelerometer' if success else 'Accelerometer unavailable'
                if success:
                    self.enabled = True
            elif isinstance(c, DisableCommand):
                success = self.try_enable(False)
                c.state = 'success' if success else 'failed'
                c.response_message = 'Successfully disabled accelerometer' if success else 'Failed disabling accelerometer'
                if success: 
                    self.enabled = False
            elif isinstance(c, CalibrateZeroCommand):
                self.process_calibration(c, now)
            else:
                c.state = 'failed' # Part cannot handle this command
                c.response_message = f'Cannot process commands of type {c.command_type}'
                continue
            
        if self.enabled and not self.sensor_failed:
            try:    
                last_events = self.hardware.lastEvents
                self.hardware.flush()
                last_accuracy = self.hardware.lastAccuracy
                if len(last_events) > 0:
                    self.iteration_acceleration = [x.values for x in last_events]
                    # If calibrating add the calibration values
                    # Do this before the old calibration is applied to make sure
                    # that it is a fresh calbiration
                    if self.calibration_proccessor is not None:
                        self.calibration_proccessor.add_values(self.iteration_acceleration)
                    for v in self.iteration_acceleration:
                        v[0] += self.correction[0] # type: ignore
                        v[1] += self.correction[1] # type: ignore
                        v[2] += self.correction[2] # type: ignore
                    self.acceleration = self.iteration_acceleration[-1]
                if last_accuracy:
                    self.accuracy = self.iteration_accuracy = last_accuracy
            except Exception as e:
                print(f'Plyer gravity sensor failed: {e}')
                self.sensor_failed = True
        else:
            self.iteration_acceleration = self.acceleration = None
            self.iteration_accuracy = self.accuracy = None
            
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            ('enabled', int),
            ('sensor_failed', int),
            ('calibrating', int),
            ('accuracy', int),
            ('acceleration-x', float),
            ('acceleration-y', float),
            ('acceleration-z', float),
            ('correction-x', float),
            ('correction-y', float),
            ('correction-z', float),
        ]

    def collect_measurements(self, now, iteration) -> Union[None, Iterable[Iterable[Union[str, float, int, None]]]]:

        if iteration % self.status_data_rate > 0 and self.iteration_acceleration is None and self.iteration_accuracy is None:
            return
        
        if self.iteration_acceleration is not None:
            res = [[
                None,
                None,
                None,
                None,
                acc[0],
                acc[1],
                acc[2],
                None,
                None,
                None,
            ] for acc in self.iteration_acceleration]
            res[0][0] = 1 if self.enabled else 0
            res[0][1] = 1 if self.sensor_failed else 0
            res[0][2] = 1 if self.calibration_command is not None else 0
            res[0][3] = self.iteration_accuracy
            res[0][7] = self.correction[0]
            res[0][8] = self.correction[1]
            res[0][9] = self.correction[2]
            return res

        return [[1 if self.enabled else 0, 1 if self.sensor_failed else 0, 1 if self.calibration_command is not None else 0, self.iteration_accuracy, None, None, None, None, None, None]]
    
    
    def flush(self):

        self.iteration_acceleration = None
        self.iteration_accuracy = None
        
