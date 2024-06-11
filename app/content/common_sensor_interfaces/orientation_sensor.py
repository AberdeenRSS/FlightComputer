

from typing import Tuple



class IOrientationSensor:

    def get_orientation(self) -> Tuple[float, float, float, float] | None:
        '''
        Returns the current orientation or None if unavailable.
        Format: (w, x, y, z)
        '''
        return None