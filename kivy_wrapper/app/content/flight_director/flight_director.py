from datetime import datetime, timedelta
from typing import Iterable, Tuple, Type, Union
from uuid import UUID, uuid4

from core.content.flight_director.abort_command import AbortCommand
from core.content.flight_director.arm_director_command import ArmDirectorCommand
from core.content.flight_director.positive_attitude_alanyzer import PositiveAttitudeAnalyzer
from core.content.flight_director.start_countdown_command import StartCountDownCommand
from core.content.general_commands.calibrate import CalibrateZeroCommand
from core.content.microcontroller.arduino.sensors.orientation_arduino import OrientationSensor
from core.content.microcontroller.arduino_serial import ArduinoOverSerial
from core.content.motor_commands.open import IgniteCommand, OpenCommand
from kivy_wrapper.app.content.sensors.android_native.acceleration_pyjinius import PyjiniusAccelerationSensor
from kivy_wrapper.app.content.sensors.android_native.gyroscope_pyjinius import PyjiniusGyroscopeSensor
from kivy_wrapper.app.content.sensors.android_native.inertial_reference_frame import InertialReferenceFrame
from core.content.microcontroller.arduino.parts.igniter import IgniterSensor
from core.content.microcontroller.arduino.parts.servo import ServoSensor
from core.logic.commands.command import Command
from core.logic.commands.command import Command, Command
from core.content.general_commands.enable import DisableCommand, EnableCommand, ResetCommand
from core.logic.commands.command_helper import is_completed_command, is_new_command

from core.logic.rocket_definition import Part, Rocket
from kivy.logger import Logger, LOG_LEVELS



class FlightDirector(Part):

    type = 'FlightDirector'

    enabled: bool = True

    connected: bool = False

    min_update_period = timedelta(milliseconds=10)

    min_measurement_period = timedelta(milliseconds=100)

    state: str = 'Idle'

    calibrating: bool = False

    calibrated: bool = False

    current_calibrate_base_sensor_commands: Union[None, list[CalibrateZeroCommand]] = None

    calibrate_inertial_frame_command: Union[None, CalibrateZeroCommand] = None

    initial_countdown = 15

    countdown: Union[None, float] = None

    countdown_start_time: float = 0

    launch_time: float = 0

    deploy_parachute_command: Union[OpenCommand, None] = None

    deploy_parachute_delay = 22

    deploy_parachute_countdown: Union[None, float] = None

    orientation: OrientationSensor
    
    attitude_smartphone: PositiveAttitudeAnalyzer
    
    attitude_external: PositiveAttitudeAnalyzer

    def __init__(self, _id: UUID, name: str, rocket: Rocket, arduino: ArduinoOverSerial, igniter: IgniterSensor, parachute: ServoSensor, acc: PyjiniusAccelerationSensor, gryo: PyjiniusGyroscopeSensor, inertialFrame: InertialReferenceFrame, orientation: OrientationSensor, attitude_smartphone: PositiveAttitudeAnalyzer, attitude_external: PositiveAttitudeAnalyzer):

        super().__init__(_id, name, rocket, [arduino, igniter, parachute, acc, gryo, inertialFrame]) # type: ignore

        self.arduino = arduino
        self.parachute = parachute
        self.igniter = igniter
        self.acc = acc
        self.gyro = gryo
        self.inertialFrame = inertialFrame
        self.orientation = orientation
        self.attitude_smartphone = attitude_smartphone
        self.attitude_external = attitude_external

    def get_accepted_commands(self) -> list[Type[Command]]:
        return [CalibrateZeroCommand, ArmDirectorCommand, StartCountDownCommand, AbortCommand]
    
    def run_calibrate(self, c: CalibrateZeroCommand, now) -> Iterable[Command]:

        if self.state != 'Idle':
            c.state = 'failed'
            c.response_message = 'Can only calibrate in idle mode'
            return []

        if c.state == 'received' and self.calibrating:
            c.state = 'failed'
            c.response_message = 'Already calibrating'
            return []
        
        if is_new_command(c):
            Logger.info(f'FLIGHT_DIRECTOR: starting calibration')

            self.calibrate_inertial_frame_command = None
            c.state = 'processing'

            calibrate_acc = CalibrateZeroCommand()
            calibrate_acc._id = uuid4()
            calibrate_acc.create_time = datetime.utcnow()
            calibrate_acc._part_id = self.acc._id

            calibrate_gyro = CalibrateZeroCommand()
            calibrate_gyro._id = uuid4()
            calibrate_gyro.create_time = datetime.utcnow()
            calibrate_gyro._part_id = self.gyro._id

            calibrate_orientation = CalibrateZeroCommand()
            calibrate_orientation._id = uuid4()
            calibrate_orientation.create_time = datetime.utcnow()
            calibrate_orientation._part_id = self.orientation._id

            self.current_calibrate_base_sensor_commands = [calibrate_acc, calibrate_gyro, calibrate_orientation]
            return [calibrate_acc, calibrate_gyro, calibrate_orientation]
        
        if c.state == 'processing':
            if self.current_calibrate_base_sensor_commands is None:
                c.state = 'failed'
                return []
            
            any_incomplete = False

            for base_cal in self.current_calibrate_base_sensor_commands:
                if base_cal.state == 'failed':
                    c.state = 'failed'
                    c.response_message = 'Failure to calibrate one of the parts'
                    return []
                
                if not is_completed_command(base_cal):
                    any_incomplete = True
                
            if not any_incomplete:

                if self.calibrate_inertial_frame_command is None:
                    calibrate_inertial = CalibrateZeroCommand()
                    calibrate_inertial._id = uuid4()
                    calibrate_inertial.create_time = datetime.utcnow()
                    calibrate_inertial._part_id = self.inertialFrame._id

                    self.calibrate_inertial_frame_command = calibrate_inertial
                    return [calibrate_inertial]
                
                if self.calibrate_inertial_frame_command.state == 'failed':
                    c.state = 'failed'
                    c.response_message = 'Failure to calibrate intertial frame'
                    return []
                
                if self.calibrate_inertial_frame_command.state == 'success':
                    c.state = 'success'
                    self.calibrated = True
                    return []
                
            if now > c.create_time.timestamp() + 30:
                c.state = 'failed'
                c.response_message = 'calibartion timeout'
                return []
            
            return []
                
        c.state = 'failed'
        c.response_message = 'Unknown error'
                
    def run_arm(self, c: ArmDirectorCommand, now: float):

        if self.state != 'Idle':
            c.state = 'failed'
            c.response_message = 'Can only arm director if previously in idle'
            return
        
        if not self.calibrated:
            c.state = 'failed'
            c.response_message = 'sensors not yet calibrated'
            return
        
        if not self.arduino.connected:
            c.state = 'failed'
            c.response_message = 'Arduino not connected'
            return
        
        external_data_age = self.attitude_external.get_data_age()
        smartphone_data_age = self.attitude_smartphone.get_data_age()

        if external_data_age is None or now > (external_data_age + 3):
            c.state = 'failed'
            c.response_message = 'No recent data from external attitude'
            return
        
        if smartphone_data_age is None or now > (smartphone_data_age + 3):
            c.state = 'failed'
            c.response_message = 'No recent data from smartphone attitude'
            return

        c.state = 'success'
        self.state = 'Armed'

    def run_countdown(self, c: StartCountDownCommand, now: float) -> Iterable[Command]:

        if self.state != 'Armed' and c.state != 'processing':
            c.state = 'failed'
            c.response_message = 'Can only start countdown director if armed'
            return []
        
        if self.state == 'Idle':
            c.state = 'failed'
            c.response_message = 'Countdown aborted'
        
        if c.state == 'received':
            self.state = 'countdown'
            c.state = 'processing'
            self.countdown = self.initial_countdown
            self.countdown_start_time = now
            return []

        if c.state == 'processing':

            self.countdown = self.initial_countdown - (now - self.countdown_start_time)

            if self.countdown > 0:
                return []

            c.state = 'success'
            self.state = 'flight'
            
            ignite_command = IgniteCommand()
            ignite_command._id = uuid4()
            ignite_command.create_time = datetime.utcnow()
            ignite_command._part_id = self.igniter._id

            self.launch_time = now
            self.deploy_parachute_command = None

            return [ignite_command]
        
        c.state = 'failed'
        c.response_message = 'Unknown error'
        return []
        
    def run_abort(self, c: AbortCommand):

        self.state = 'Idle'
        c.state = 'success'

        deploy_command = OpenCommand()
        deploy_command._id = uuid4()
        deploy_command.create_time = datetime.utcnow()
        deploy_command._part_id = self.parachute._id

        self.deploy_parachute_command = deploy_command

        return deploy_command

    def send_deploy_parachute(self):
        if self.deploy_parachute_command is None or self.deploy_parachute_command.state == 'failed':
            deploy_command = OpenCommand()
            deploy_command._id = uuid4()
            deploy_command.create_time = datetime.utcnow()
            deploy_command._part_id = self.parachute._id

            self.deploy_parachute_command = deploy_command

            return deploy_command

        return None    
                
    def update(self, commands: Iterable[Command], now: float, iteration):

        new_commands = list()

        for c in commands:
            
            if isinstance(c, CalibrateZeroCommand):
                new_commands.extend(self.run_calibrate(c, now))
                continue

            if isinstance(c, ArmDirectorCommand):
                self.run_arm(c, now)
                continue

            if isinstance(c, StartCountDownCommand):
                new_commands.extend(self.run_countdown(c, now))
                continue

            if isinstance(c, AbortCommand):
                new_commands.append(self.run_abort(c))

        # Deploy the parachute after a certain time during the flight
        if self.state == 'flight':
            self.deploy_parachute_countdown = self.deploy_parachute_delay - (now - self.launch_time)

            external_data_age = self.attitude_external.get_data_age()
            external_attitude = self.attitude_external.pointing_up

            smartphone_data_age = self.attitude_smartphone.get_data_age()
            smartphone_attitude = self.attitude_smartphone.pointing_up
            
            # Use external attitude if data is good
            if external_data_age is not None and now < (external_data_age + 3) and external_attitude is not None:
                
                if external_attitude < 0:
                    new_command = self.send_deploy_parachute()
                    if new_command is not None:
                        new_commands.append(new_command)
            
            # # Use smartphone attitude if data is good
            # elif smartphone_data_age is not None and now < (smartphone_data_age + 3) and smartphone_attitude is not None:
                
            #     if smartphone_attitude < 0:
            #         new_command = self.send_deploy_parachute()
            #         if new_command is not None:
            #             new_commands.append(new_command)

            if self.deploy_parachute_countdown <= 0:

                new_command = self.send_deploy_parachute()
                if new_command is not None:
                    new_commands.append(new_command)

        return new_commands


    def get_measurement_shape(self) -> Iterable[Tuple[str, str]]:
        return [
            ('state', '16s'),
            ('calibrated', '?'),
            ('countdown', 'f'),
            ('parachute_countdown', 'f')
        ]

    def collect_measurements(self, now, iteration) -> Iterable[Iterable[Union[str, float, int]]]:


        return [[self.state, self.calibrated, self.countdown or 0, self.deploy_parachute_countdown or 0]]
    
