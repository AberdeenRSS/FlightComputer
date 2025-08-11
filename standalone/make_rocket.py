
from flight_computer.core.content.measurement_sinks.file_measurement_sink import FileMeasurementSink
from flight_computer.core.content.measurement_sinks.mqtt_measurement_sink import MqttMeasurementSink
from flight_computer.core.content.raspberry.i2c import RaspberryI2CInterface
from flight_computer.core.content.raspberry.i2c_devices.bmp390 import BMP390_Raspberry
from flight_computer.core.content.raspberry.i2c_devices.bno055 import BNO055_Raspberry
from flight_computer.core.content.sensors.plyer.framerate import FramerateSensor, FramerateSensor
from flight_computer.core.content.sensors.plyer.battery_plyer import PlyerBatterySensor, PlyerBatterySensor
from flight_computer.core.content.testing.command_tester import CommandTestPart
from flight_computer.core.logic.rocket_definition import Rocket

# frocorepp.ui.part_ui import PartUi

from uuid import UUID

def make_rocket(name = 'New rocket') -> Rocket:
    ''' Makes the spatula rocket '''

    rocket = Rocket(name)

    # Computer status parts
    FramerateSensor(UUID('8d45c8e7-7ae2-4496-a5e0-047a631ef17c'), 'Framerate', rocket)
    measurement_sink = MqttMeasurementSink(UUID('fa9eac88-5d2f-41a6-aeab-85c1591433a2'), 'Measurement dispatch', rocket)
    file_sink = FileMeasurementSink(UUID('80262be7-2396-4d30-8091-7060ccaa6842'), 'File measurement sink', rocket)

    # File sink has to be made working with standalone
    # file_sink = FileMeasurementSink(UUID('ebcf7ca3-9757-42f8-b972-af769e5d0d75'), 'Measurement File Storage', rocket)

    # # Plyer sensors
    PlyerBatterySensor(UUID('547a50de-589e-4744-aada-a85bd72deba0'), 'Battery Sensor', rocket)

    CommandTestPart(UUID('de6e93c0-eaf4-496f-913a-4cbbd89c1c7a'), 'Command tester', rocket)

    i2c = RaspberryI2CInterface(UUID('ef616406-fe02-4282-9f7d-d8238be9e17c'), 'I2C', rocket, 3)
    bno055 = BNO055_Raspberry(UUID('49d9ae27-13a2-4d3a-b751-09fc52b5bd77'), 'Bno055', rocket, i2c)
    bmp390 = BMP390_Raspberry(UUID('6181a2c8-994a-419e-84fb-44bfd5ab6516'), 'Bmp390', rocket, i2c)

    # PlyerAccelerationSensor(UUID('5cefc100-3e52-401c-9dfc-e6331355eb55'), 'Accelerometer', rocket)
    # PlyerTemperatureSensor(UUID('db5f474d-2b83-4d38-b438-f94a21510c1e'), 'Temperature', rocket)
    # PlyerGyroscopeSensor(UUID('a2197a9f-37e9-46f4-ac19-32d3ea153d92'), 'Gyroscope', rocket)
    # PlyerBarometerSensor(UUID('d7a8e2e0-4e8f-4cfa-8921-d299d28b8182'), 'Barometer', rocket)
    # PlyerGravitySensor(UUID('cde714a2-2179-4b0d-964d-f1af4696bf2e'), 'Gravity', rocket)
    # PlyerLightSensor(UUID('1ae63061-2763-4374-80fd-8328ab8c30ef'), 'Light', rocket)
    # PlyerSpatialOrientationSensor(UUID('01219fb4-4f2f-42d8-a910-6aae01eee1c7'), 'Spatial Orientation', rocket)

    # PlyerGPSSensor(UUID('2a3de588-a4a3-46e1-b94b-fd17ad75b06a'), 'GPS', rocket)
  
    # # Serial communication
    # Arduino parts
    # arduino_serial = ArduinoOverSerial(UUID('cd170fff-0138-4820-8e97-969eb3f2f287'), 'Serial Port', rocket)
    # arduino_serial = ArduinoOverBluetooth(UUID('10b87ad8-497a-4d9f-8944-4499856a35e4'), 'Serial Port', rocket)

    # parachute = ServoSensor(UUID('9f86acb1-9795-46fc-b083-e6451f214d1f'), 'Servo', rocket, arduino_serial)
    # igniter = IgniterSensor(UUID('f309669d-6bd7-4ee3-90a5-45a0e1bdd60e'), 'Igniter', rocket, arduino_serial, parachute)

    # Arduino sensorsd
    # orientation = OrientationSensor(UUID('158314cc-6d1f-11ee-b962-0242ac120002'), 'Orientation', rocket, arduino_serial)
    # pressure = PressureArduinoSensor(UUID('6277bf09-36ba-4e41-861f-df6169d83f5f'), 'Pressure', rocket, arduino_serial)

    # altitude = BarometricAltitudeSensor(UUID('a7fc0eae-3e6d-4775-af07-d8ad7d871311'), 'Barometric Altitude', rocket, pressure, pressure)

    # Pressure arduino sensor
    # temperature = TemperatureSensor(UUID('ac93964a-6bb0-11ee-b962-0242ac120002'), 'Temperature', rocket)
    # pressure = PressureSensor(UUID('eedd649e-78c7-11ee-b962-0242ac120002'), 'Pressure', rocket)
    # altitude = AltitudeSensor(UUID('f526cb42-78c7-11ee-b962-0242ac120002'), 'Altitude', rocket)
    # pressureArduino = PressureArduinoSensor(UUID('8ed5e972-8cb3-11ee-b9d1-0242ac120002'), 'Pressure Sensor', rocket,
    #                                         arduino_serial, temperature, pressure, altitude)

    # attitude_smartphone = PositiveAttitudeAnalyzer(UUID('cc53cfb9-05bd-4ca7-bba5-202039636b48'), 'Attitude Analyzer Smartphone', rocket, inertialFrame)
    # attitude_external = PositiveAttitudeAnalyzer(UUID('b0a3acb6-9374-482f-a1c4-4411c995a13e'), 'Attitude Analyzer External', rocket, orientation)

    return rocket
