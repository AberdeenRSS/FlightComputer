from datetime import timedelta
from app.content.measurement_sinks.api_mesurement_sink import ApiMeasurementSink
from app.content.sensors.random_sensor import RandomSensor
from app.logic.rocket_definition import Rocket
from app.content.sensors.battery_plyer import PlyerBatterySensor
from uuid import UUID

def make_spatula() -> Rocket:
    ''' Makes the spatula rocket '''

    rocket = Rocket('Spatula')

    PlyerBatterySensor(UUID('547a50de-589e-4744-aada-a85bd72deba0'), 'Battery Sensor', rocket)
    rnd = RandomSensor(UUID('ebc108a5-ffc3-44b2-b505-840e732a1519'), 'Random Sensor 2', rocket)
    rnd.min_update_period = timedelta(milliseconds=1)
    rnd.min_measurement_period = timedelta(milliseconds=1)

    ApiMeasurementSink(UUID('fa9eac88-5d2f-41a6-aeab-85c1591433a2'), 'Measurement dispatch', rocket)

    return rocket
