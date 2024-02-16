

from typing import Tuple

import numpy as np


class IOrientationSensor:

    def get_orientation(self) -> np.ndarray | None:
        '''
        Returns the current orientation or None if unavailable.
        Format: (w, x, y, z)
        '''
        return None