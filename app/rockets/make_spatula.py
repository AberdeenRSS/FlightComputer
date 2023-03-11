from app.logic.rocket_definition import Rocket
from app.content.sensors.battery_plyer import PlyerBatterySensor
from uuid import UUID

def make_spatula() -> Rocket:
    ''' Makes the spatula rocket '''

    rocket = Rocket('Spatula')

    PlyerBatterySensor(UUID('547a50de-589e-4744-aada-a85bd72deba0'), 'Battery Sensor', rocket)

    return rocket
