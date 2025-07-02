from asyncio import Task
import asyncio


from datetime import timedelta
from logging import _nameToLevel
import threading
from typing import Callable, Iterable, Tuple, Type, Union
from uuid import UUID
from flight_computer.core.logic.rocket_definition import Part, Rocket

class RaspberryI2CInterface(Part):

    type = 'Interface.I2C.Raspberry'

    # Set update to only every 5 seconds as 
    # battery information is low frequency
    min_update_period = timedelta(milliseconds=10)
    min_measurement_period = timedelta(milliseconds=10)

    def __init__(self, _id: UUID, name: str, parent: Union[Part, Rocket, None], tty_port: str, start_enabled = True):

        self.enabled = start_enabled

        self.tty_port = tty_port

        self.port_thread_lock = threading.Lock()

        self.connected = False

        super().__init__(_id, name, parent, list()) # type: ignore

    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        return [
            *super().get_measurement_shape(),
        ]

    def get_accepted_commands(self):
        return [
            *super().get_accepted_commands()
        ]
    
    def get_command_callbacks(self):
        return [
            *super().get_command_callbacks()
        ]
   
    def update(self, now, iteration):
        pass

    async def connect_background(self):

        await asyncio.sleep(0.01) # Make background task

        self.serial_port = serial.Serial(
                self.tty_port
            )

        if self.serial_port.closed:
            self.connected = False
        
        self.connected = True

        if self.serial_port.is_open and (self.read_thread is not None or not self.read_thread.is_alive()):
            self.read_thread = threading.Thread(target = self.read_thread)
            self.read_thread.start()
        

    def read_thread(self):
        try:

            while True:

                if self.serial_port is None:
                    break

                if not self.serial_port.is_open:
                    break

                with self.port_thread_lock:

                    received_msg = None
                    in_waiting = self.serial_port.in_waiting

                    if in_waiting > 0:
                        received_msg = self.serial_port.read(
                            in_waiting
                        )
                    
                self.log(f'Received: {received_msg}')

        except Exception as ex:
            self.log(f'crash read thread {ex}', level = _nameToLevel['ERROR'])
            raise ex
        finally:
            self.connected = False
            self.serial_port = None


import serial
import time

def read_response(ser):
        buffer = ''

        for x in range(0, 1000):
                byte = ser.read().decode('utf-8', errors='ignore')
                buffer += byte

                if '\nOK' in buffer:
                        return True, buffer

                if '\nERROR' in buffer:
                        return False, buffer

        raise Exception('Response not finished after 1000 lines, aborting')


def send_command(ser, command: str):
        cmd = f'{command}\r\n'.encode('utf-8')
        ser.write(cmd)


with serial.Serial("/dev/ttyS0",115200) as ser:

        W_buff = ["AT+CGNSPWR=1\r\n", "AT+CGNSSEQ=\"RMC\"\r\n", "AT+CGNSINF\r\n", "AT+CGNSURC=2\r\n","AT+CGNSTST=1\r\n"]

        # Power up
        ser.write('AT+CGNSPWR=1\r\n'.encode('utf-8'))
        ser.flushInput()

        data = ""
        num = 0

        try:

                send_command(ser, 'AT+CGNSSEQ=\"RMC\"')
                success, buffer = read_response(ser)

                if not success:
                        print(f'Failed sending AT+CGNSSEQ=\"RMC\": {buffer}')
                        exit(1)

                send_command(ser, 'AT+CGNSINF')
                success, buffer = read_response(ser)

                if not success:
                        print(f'Failed sending AT+CGNSINF: {buffer}')
                        exit(1)

                while True:

                        send_command(ser, 'AT+CGNSINF')
                        success, buffer = read_response(ser)

                        if not success:
                                print(f'Failed command AT+CGNSINF with {buffer}')

                        # print('RESP:=------------')
                        # print(buffer)
                        # print('RESP:=------------')
                        # print(buffer)

                        # print(buffer.splitlines()[3])

                        lines = buffer.splitlines()

                        infos = None
                        for l in lines:
                                if l.startswith('+CGNSINF: '):
                                        infos = l[len('+CGNSINF: '):].split(',')

                        if  infos is None:
                                time.sleep(0.5)
                                continue

                        run_status = infos[0]
                        fix_status = infos[1]
                        utc_date = infos[2]

                        lat = infos[3]
                        lon = infos[4]

                        sattelites_in_view = infos[14]
                        sattelites_in_view_GLONASS = infos[16]

                        print(buffer)


                        print(f'Run status: {run_status}; Fix status: {fix_status}; Lat: {lat}; Lon: {lon}; Utc: {utc_date}; Sattelites: {sattelites_in_view}')



                        # print(buffer)
                        time.sleep(0.5)

        except KeyboardInterrupt:
                pass

