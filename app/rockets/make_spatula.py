from datetime import timedelta
from typing import Iterable, Tuple

from app.content.measurement_sinks.api_measurement_sink_ui import ApiMeasurementSinkUI
from app.content.measurement_sinks.api_measurement_sink import ApiMeasurementSink
from app.content.microcontroller.arduino_serial import ArduinoSerial
from app.content.microcontroller.arduino_serial_select_ui import ArduinoSerialSelectUI
from app.content.sensors.acceleration_plyer import PlyerAccelerationSensor
from app.content.sensors.gps_plyer import PlyerGPSSensor
from app.content.sensors.temperature_plyer import PlyerTemperatureSensor
from app.content.sensors.barometer_plyer import PlyerBarometerSensor
from app.content.sensors.gyroscope_plyer import PlyerGyroscopeSensor 
from app.content.sensors.light_plyer import PlyerLightSensor 
from app.content.sensors.gravity_plyer import PlyerGravitySensor
from app.content.sensors.spatial_orientation_plyer import PlyerSpatialOrientationSensor
from app.flight_config import FlightConfig 
from app.logic.rocket_definition import Rocket
from app.content.sensors.battery_plyer import PlyerBatterySensor
from uuid import UUID

from app.ui.part_ui import PartUi

def make_spatula() -> FlightConfig:
    ''' Makes the spatula rocket '''

    rocket = Rocket('Spatula')

    PlyerBatterySensor(UUID('547a50de-589e-4744-aada-a85bd72deba0'), 'Battery Sensor', rocket)
    # PlyerAccelerationSensor(UUID('5cefc100-3e52-401c-9dfc-e6331355eb55'), 'Accelerometer', rocket)
    # PlyerTemperatureSensor(UUID('db5f474d-2b83-4d38-b438-f94a21510c1e'), 'Temperature', rocket)
    # PlyerGyroscopeSensor(UUID('a2197a9f-37e9-46f4-ac19-32d3ea153d92'), 'Gyroscope', rocket)
    # PlyerBarometerSensor(UUID('d7a8e2e0-4e8f-4cfa-8921-d299d28b8182'), 'Barometer', rocket)
    # PlyerGravitySensor(UUID('cde714a2-2179-4b0d-964d-f1af4696bf2e'), 'Gravity', rocket)
    PlyerLightSensor(UUID('1ae63061-2763-4374-80fd-8328ab8c30ef'), 'Light', rocket)
    PlyerSpatialOrientationSensor(UUID('01219fb4-4f2f-42d8-a910-6aae01eee1c7'), 'Spatial Orientation', rocket)
    PlyerGPSSensor(UUID('2a3de588-a4a3-46e1-b94b-fd17ad75b06a'), 'GPS', rocket)


    # rnd = RandomSensor(UUID('ebc108a5-ffc3-44b2-b505-840e732a1519'), 'Random Sensor 2', rocket)
    # rnd.min_update_period = timedelta(milliseconds=1)
    # rnd.min_measurement_period = timedelta(milliseconds=1)

    arduino_serial = ArduinoSerial(UUID('cd170fff-0138-4820-8e97-969eb3f2f287'), 'Serial Port', rocket)

    measurement_sink = ApiMeasurementSink(UUID('fa9eac88-5d2f-41a6-aeab-85c1591433a2'), 'Measurement dispatch', rocket)

    return FlightConfig(rocket, [ApiMeasurementSinkUI(measurement_sink), ArduinoSerialSelectUI(arduino_serial)], True)
