from asyncio import Task
import asyncio
from smbus3 import SMBus
from datetime import timedelta
from logging import _nameToLevel
from typing import Callable, Iterable, Tuple, Type, Union
from uuid import UUID
from flight_computer.core.logic.rocket_definition import Part, Rocket

class RaspberryI2CInterface(Part):

    type = 'Interface.I2C.Raspberry'

    connect_task: Task | None = None

    i2c_loop_callbacks: set[Callable[[SMBus, float, int], None]] = set()

    i2cbus = None

    cur_retry_delay = None
    '''Current delay before retrying i2c connection'''

    initial_retry_delay = 0.1
    '''Initial retry delay in seconds (increased exponentially)'''

    max_retry_delay = 30
    '''Max retry delay in seconds'''

    # Set update to only every 5 seconds as 
    # battery information is low frequency
    min_update_period = timedelta(milliseconds=10)
    min_measurement_period = timedelta(milliseconds=10)

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], i2c_device_port: int = 1, start_enabled = True):

        self.enabled = start_enabled

        self.i2c_device_port = i2c_device_port

        super().__init__(_id, name, parent, list()) # type: ignore

    def make_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            *super().make_measurement_shape(),
            ('i2c_port', 1, 'i'),
            ('i2c_connected', 1, '?'),
        ]

    def make_accepted_commands(self):
        return [
            *super().make_accepted_commands()
        ]
    
    def make_command_callbacks(self):
        return [
            *super().make_command_callbacks()
        ]
   
    def update(self, now, iteration):

        # Hot path:
        if self.i2cbus is not None:
            for c in self.i2c_loop_callbacks:
                try:
                    c(self.i2cbus, now, iteration)
                except Exception as e:
                    self.log(f'I2C eror: \n {e}', level=_nameToLevel['ERROR'])

            return

        if self.connect_task is None or (self.connect_task.done() and self.i2cbus is None):
            self.connect_task = asyncio.create_task(self.connect())

    async def connect(self):

        self.i2cbus = None

        if self.cur_retry_delay is not None:
            self.log(f'Waiting {self.cur_retry_delay}s before retrying i2c setup')
            await asyncio.sleep(self.cur_retry_delay)
        
        self.log('Creating new smbus hardware interface')

        try:
            self.i2cbus = SMBus(self.i2c_device_port)
            self.cur_retry_delay = None
            self.log(f'Successfully set up smbus hardware interface on device port {self.i2c_device_port}')
            self.submit_measurement_by_name('i2c_port', self.i2c_device_port)
            self.submit_measurement_by_name('i2c_connected', True)

        except Exception as e:
            self.log(f'Failed setting up device i2c: \n {e}', level=_nameToLevel['ERROR'])
            self.submit_measurement_by_name('i2c_connected', False)
            self.i2cbus = None
            if self.cur_retry_delay is None:
                self.cur_retry_delay = self.initial_retry_delay
            else:
                self.cur_retry_delay = self.cur_retry_delay * 2
            
            if self.cur_retry_delay > self.max_retry_delay:
                self.cur_retry_delay = self.max_retry_delay

