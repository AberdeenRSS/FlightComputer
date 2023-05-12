

from typing import Tuple
import numpy as np


def quaternion_multiply(quaternion1, quaternion0):
    w0, x0, y0, z0 = quaternion0
    w1, x1, y1, z1 = quaternion1
    return np.array([
        -x1 * x0 - y1 * y0 - z1 * z0 + w1 * w0,
        x1 * w0 + y1 * z0 - z1 * y0 + w1 * x0,
        -x1 * z0 + y1 * w0 + z1 * x0 + w1 * y0,
        x1 * y0 - y1 * x0 + z1 * w0 + w1 * z0
    ])

def rotate_vector_by_quaternion(v, q):
    u = np.array(q[1:4])

    s = q[0]

    return 2.0 * np.dot(u, v) * u  + (s*s - np.dot(u, u)) * v  + 2.0 * s * np.cross(u, v)
