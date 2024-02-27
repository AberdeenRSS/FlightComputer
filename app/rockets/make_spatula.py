# from app.content.measurement_sinks.api_measurement_sink_ui import ApiMeasurementSinkUI
# from app.content.flight_director.positive_attitude_alanyzer import PositiveAttitudeAnalyzer
from app.content.flight_director.flight_director import FlightDirector
from app.content.flight_director.positive_attitude_alanyzer import PositiveAttitudeAnalyzer
from app.content.measurement_sinks.api_measurement_sink import ApiMeasurementSink
from app.content.measurement_sinks.file_measurement_sink import FileMeasurementSink
from app.content.microcontroller.arduino_over_bluetooth import ArduinoOverBluetooth
from app.content.microcontroller.arduino_serial import ArduinoOverSerial
from app.content.microcontroller.arduino_serial_monitor_ui import ArduinoSerialMonitorUI
from app.content.microcontroller.arduino_serial_select_ui import ArduinoSerialSelectUI
from app.content.sensors.android_native.gyroscope_pyjinius import PyjiniusGyroscopeSensor
from app.content.sensors.android_native.inertial_reference_frame import InertialReferenceFrame
from app.content.sensors.android_native.acceleration_pyjinius import PyjiniusAccelerationSensor

from app.content.sensors.plyer.framerate import FramerateSensor

from app.content.sensors.plyer.gps_plyer import PlyerGPSSensor
from app.content.sensors.plyer.battery_plyer import PlyerBatterySensor

from app.content.microcontroller.arduino.parts.servo import ServoSensor
from app.content.microcontroller.arduino.parts.igniter import IgniterSensor

from app.content.microcontroller.arduino.sensors.pressure.temperature_arduino import TemperatureSensor
from app.content.microcontroller.arduino.sensors.pressure.pressure_arduino import PressureSensor
from app.content.microcontroller.arduino.sensors.pressure.altitude_arduino import AltitudeSensor
from app.content.microcontroller.arduino.sensors.pressure.pressure_sensor_arduino import PressureArduinoSensor
from app.content.microcontroller.arduino.sensors.orientation_arduino import OrientationSensor
from app.content.sensors.plyer.gravity_plyer import PlyerGravitySensor
from app.content.testing.periodic_tester import PeriodicTester

from app.flight_config import FlightConfig
from app.logic.rocket_definition import Rocket

# from app.ui.part_ui import PartUi

from uuid import UUID

def make_spatula() -> FlightConfig:
    ''' Makes the spatula rocket '''

    rocket = Rocket('Fayre Demo')

    # Computer status parts
    FramerateSensor(UUID('8d45c8e7-7ae2-4496-a5e0-047a631ef17c'), 'Framerate', rocket)
    measurement_sink = ApiMeasurementSink(UUID('fa9eac88-5d2f-41a6-aeab-85c1591433a2'), 'Measurement dispatch', rocket)
    FileMeasurementSink(UUID('ebcf7ca3-9757-42f8-b972-af769e5d0d75'), 'Measurement File Storage', rocket)

    # # Plyer sensors
    PlyerBatterySensor(UUID('547a50de-589e-4744-aada-a85bd72deba0'), 'Battery Sensor', rocket)
    # PlyerAccelerationSensor(UUID('5cefc100-3e52-401c-9dfc-e6331355eb55'), 'Accelerometer', rocket)
    # PlyerTemperatureSensor(UUID('db5f474d-2b83-4d38-b438-f94a21510c1e'), 'Temperature', rocket)
    # PlyerGyroscopeSensor(UUID('a2197a9f-37e9-46f4-ac19-32d3ea153d92'), 'Gyroscope', rocket)
    # PlyerBarometerSensor(UUID('d7a8e2e0-4e8f-4cfa-8921-d299d28b8182'), 'Barometer', rocket)
    PlyerGravitySensor(UUID('cde714a2-2179-4b0d-964d-f1af4696bf2e'), 'Gravity', rocket)
    # PlyerLightSensor(UUID('1ae63061-2763-4374-80fd-8328ab8c30ef'), 'Light', rocket)
    # PlyerSpatialOrientationSensor(UUID('01219fb4-4f2f-42d8-a910-6aae01eee1c7'), 'Spatial Orientation', rocket)

    PlyerGPSSensor(UUID('2a3de588-a4a3-46e1-b94b-fd17ad75b06a'), 'GPS', rocket)

    # Native sensors
    acc = PyjiniusAccelerationSensor(UUID('d91eed66-d699-4816-892d-3e99282966ab'), 'Accelerometer', rocket)
    gyro = PyjiniusGyroscopeSensor(UUID('5159e64a-0f55-4a8c-8d24-596a0118e0be'), 'Gyroscope', rocket)
    inertialFrame = InertialReferenceFrame(acc, gyro, UUID('27f5d5e0-5fa9-4ae1-88af-8477d80960d7'), 'Intertial Reference Frame', rocket)

    # # Serial communication
    # Arduino parts
    arduino_serial = ArduinoOverSerial(UUID('cd170fff-0138-4820-8e97-969eb3f2f287'), 'Serial Port', rocket)
    # arduino_serial = ArduinoOverBluetooth(UUID('10b87ad8-497a-4d9f-8944-4499856a35e4'), 'Serial Port', rocket)

    parachute = ServoSensor(UUID('9f86acb1-9795-46fc-b083-e6451f214d1f'), 'Servo', rocket, arduino_serial)
    igniter = IgniterSensor(UUID('f309669d-6bd7-4ee3-90a5-45a0e1bdd60e'), 'Igniter', rocket, arduino_serial, parachute)

    # Arduino sensorsd
    orientation = OrientationSensor(UUID('158314cc-6d1f-11ee-b962-0242ac120002'), 'Orientation', rocket, arduino_serial)
    pressure = PressureArduinoSensor(UUID('6277bf09-36ba-4e41-861f-df6169d83f5f'), 'Pressure', rocket, arduino_serial)

    # Pressure arduino sensor
    # temperature = TemperatureSensor(UUID('ac93964a-6bb0-11ee-b962-0242ac120002'), 'Temperature', rocket)
    # pressure = PressureSensor(UUID('eedd649e-78c7-11ee-b962-0242ac120002'), 'Pressure', rocket)
    # altitude = AltitudeSensor(UUID('f526cb42-78c7-11ee-b962-0242ac120002'), 'Altitude', rocket)
    # pressureArduino = PressureArduinoSensor(UUID('8ed5e972-8cb3-11ee-b9d1-0242ac120002'), 'Pressure Sensor', rocket,
    #                                         arduino_serial, temperature, pressure, altitude)

    attitude_smartphone = PositiveAttitudeAnalyzer(UUID('cc53cfb9-05bd-4ca7-bba5-202039636b48'), 'Attitude Analyzer Smartphone', rocket, inertialFrame)
    attitude_external = PositiveAttitudeAnalyzer(UUID('b0a3acb6-9374-482f-a1c4-4411c995a13e'), 'Attitude Analyzer External', rocket, orientation)

    # FlightDirector(UUID('37155a2c-c51d-41b7-9dae-67d640d8c284'), 'Flight Director', rocket, arduino_serial, igniter, parachute, acc, gyro, inertialFrame, orientation, attitude_smartphone, attitude_external)
    PeriodicTester(UUID('4f4534de-3a53-44ae-ada5-b7a0b0636e13'), 'Periodic HW tester', rocket, parachute, igniter)

    return FlightConfig(rocket, [ArduinoSerialSelectUI(arduino_serial)], True)
    # return FlightConfig(rocket, [], True)
