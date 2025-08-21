from typing import Any, Callable, Collection, Iterable, Tuple, Type
from typing_extensions import Self
from uuid import UUID
import RPi.GPIO as GPIO
import time
from flight_computer.core.logic.rocket_definition import Part, Rocket


def get_pwm(angle):
    return (angle/18.0) + 2.5


class Servo(Part):

    close_angle: float = 20

    open_angle: float = 60

    current_angle = close_angle

    def __init__(self, _id: UUID, name: str, parent: Self | None, pin: int):
        super().__init__(_id, name, parent, [])

        self.servo_pin = pin

        self.servo = None

    def update(self, now: float, iteration: int) -> None:

        if self.servo is None:
            p = GPIO.PWM(self.servo_pin, 50) # GPIO 17 for PWM with 50Hz
            p.start(get_pwm(self.current_angle)) # Initialization
            self.servo = p
            self.log(f'Setup servo on pin {self.servo_pin}')
            return
        
        self.servo.ChangeDutyCycle(get_pwm(self.current_angle))
    
    def make_accepted_commands(self) -> Collection[Tuple[str, Type | str | list[Tuple[str, str]]]]:
        return [
            *super().make_accepted_commands(),
            ('activate', ''),
            ('open', ''),
            ('close', '')
        ]
    
    def make_command_callbacks(self) -> Iterable[Callable[[float, Any], None]]:
        return [
            *super().make_command_callbacks(),
            self.open,
            self.open,
            self.close
        ]

        
    def open(self, t: float, _):

        self.open_angle = self.open_angle
        
    def close(self, t: float, _):

        self.current_angle = self.close_angle