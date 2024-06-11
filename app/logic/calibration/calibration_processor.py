from abc import ABC, abstractclassmethod
from typing import Collection, Tuple

class CalibrationProcessor3D(ABC):

    @abstractclassmethod
    def add_values(self, values: Collection[Tuple[float, float, float]]):
        pass

    @abstractclassmethod
    def get_correction(self) -> Tuple[float, float, float]:
        raise NotImplementedError()

class SimpleCalibrationProcessor3D(CalibrationProcessor3D):

    def __init__(self) -> None:
        super().__init__()

        self.count = 0
        self.acc: list[float] = [0, 0, 0]

    def add_values(self, values: Collection[Tuple[float, float, float]]):
        self.count += len(values)

        for x, y, z in values:
            self.acc[0] += x
            self.acc[1] += y
            self.acc[2] += z

    def get_correction(self) -> Tuple[float, float, float]:

        if self.count < 1:
            return 0, 0, 0

        return -self.acc[0]/self.count, -self.acc[1]/self.count, -self.acc[2]/self.count