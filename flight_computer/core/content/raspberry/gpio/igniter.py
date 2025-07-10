import asyncio

from datetime import timedelta
from logging import _nameToLevel
from typing import Callable, Iterable, Tuple, Type, Union
from uuid import UUID
from flight_computer.core.logic.rocket_definition import Part, Rocket


class GPIO_Igniter(Part):

    type = 'GPIO.Igniter'

    ignite_duration = 0.2

    current_state = None
    '''None, "Countdown" or "Igniting" '''

    gpio_pin = 1

    # Set update to only every 5 seconds as 
    # battery information is low frequency
    min_update_period = timedelta(milliseconds=10)

    min_measurement_period = timedelta(milliseconds=10)

    setup_task = None

    def __init__(self, _id: UUID, name: str, gpio_pin: int, parent: Union[Part, Rocket, None], start_enabled = True):

        self.enabled = start_enabled

        self.setup_task = asyncio.create_task(self.setup_async())

        self.main_event_loop = asyncio.get_running_loop()

        self.gpio_pin = gpio_pin

        super().__init__(_id, name, parent, list()) # type: ignore

    async def setup_async(self):

        await asyncio.sleep(0.01)

        try:

            import RPi.GPIO as GPIO

            servoPIN = 12
            GPIO.setup(self.gpio_pin, GPIO.OUT)
            GPIO.output(self.gpio_pin, GPIO.LOW)

            return GPIO

        except Exception as e:
            self.log(f'Failed to setup gpio: {str(e)}', _nameToLevel['ERROR'])
            return None


    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            *super().get_measurement_shape(),
            ('igniter_triggered', 1, 'f'),
        ]

    def get_accepted_commands(self):
        return [
            *super().get_accepted_commands(),
            ('ignite', ''),
            ('set_ignite_duration', 'f')
        ]
    
    def get_command_callbacks(self):
        return [
            *super().get_command_callbacks(),
            self.on_ignite,
            self.set_ignite_duration
        ]
    
    def on_ignite(self, timestamp: float):

        self.ignite_task = self.main_event_loop.create_task(self.ignite_async())

    async def ignite_async(self):

        gpio = await self.setup_task

        if gpio is None:
            self.log(f'GPIO unavailable, incapable to triggering igniter', _nameToLevel['ERROR'])
            return
        
        if self.current_state is not None:
            self.log(f'Ignition already in progress', _nameToLevel['WARN'])
            return
        
        self.current_state = 'Igniting'
        gpio.output(self.gpio_pin, gpio.HIGH)
        self.log(f'Ignition triggered for {self.ignite_duration}s')

        await asyncio.sleep(self.ignite_duration)

        gpio.output(self.gpio_pin, gpio.LOW)

        self.current_state = None

    def set_ignite_duration(self, timestamp: float, duration: float):

        self.ignite_duration = duration
   
    def update(self, now, iteration):
        pass
        

