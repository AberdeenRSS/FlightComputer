import json
import time
from typing import Any, Callable, Sequence, Union, Iterable, Tuple, Type, Collection
from datetime import timedelta
from typing_extensions import Self
from uuid import UUID
from abc import ABC, ABCMeta, abstractclassmethod, abstractmethod

from logging import getLogger, _nameToLevel

INFO_LOG_LEVEL = _nameToLevel['INFO']

#Maybe

# PART_CATEGORY_SENSOR = 'SENSOR'
# ''' Meant for any input data, i.e. sensors. sensors will always be called first in the update order'''

# PART_CATEGORY_DIRECTOR = 'DIRECTOR'

# PART_CATEGORY_CONTROL = 'CONTROL'
# ''' 
# Meant for all control parts, i.e. actuators, motors, etc. Control parts will always be called last in the update order so
# that all potential control inputs have already happened
# '''

# part_categories = Literal['SENSOR', 'CONTROL']

#region: Definitions
class Rocket: pass # type: ignore

MeasurementTypes = Union[str, int, float, bytes, None]
Measurements = Sequence[Tuple[int, MeasurementTypes]]
Measurement = Tuple[float, int, Union[MeasurementTypes, Sequence[MeasurementTypes]]]

ShapeDefType = str | Type

BaseShapeType = float | int | bool
ComplexShapeType = str | bytes | BaseShapeType | Iterable[BaseShapeType]

#endregion

    
class Part(metaclass=ABCMeta):
    """ Base class for all parts. Inherit to define a specific part"""

    _id: UUID

    _index: int

    type: str

    virtual: bool = False

    name: str

    rocket: Rocket

    children: list[Self]

    parent: Union[Self, None] = None

    dependencies: list[Self] 

    enabled: bool = True

    _last_enable_command: float = 0

    start_enabled: bool = True

    min_update_period: timedelta = timedelta(milliseconds=100)
    '''
    The minimum period with which the update method is called. Default is 100ms. Set to higher values for
    low priority parts that don't have to be evaluated as often. If the main loop runs less frequent
    than this min period, the part will be called for every iteration
    '''

    min_measurement_period: timedelta = timedelta(milliseconds=100)
    '''
    The minimum period with which the update method is called. Default is 100ms. Set to higher values for
    low priority parts that don't have to be evaluated as often. If the main loop runs less frequent
    than this min period, the part will be called for every iteration
    '''

    last_update: Union[None, float] = None
    '''
    Time in unix seconds since the part was last updated
    Set by the main execution loop after update is called
    '''

    last_measurement: Union[None, float] = None
    '''
    Time in unix seconds since the parts measurement buffer was last swapped
    Set by the main execution loop
    '''

    _measurement_buffer: list[Measurement] = None
    '''
    Measurements are buffered here between collection by the the main loop
    '''

    _measurement_shape: list[Tuple[str, int, Type | str | list[Tuple[str, Type | str]]]]

    @property
    def measurement_shape(self):
        return self._measurement_shape
    
    _measurement_index_lookup: dict[str, int]

    @property
    def measurement_index_lookup(self):
        return self._measurement_index_lookup 
    
    _accepted_commands: list[Tuple[str, Union[Type, str, list[Tuple[str, str]]]]]       

    @property
    def accepted_command(self):
        return self._accepted_commands
    
    _command_index_lookup: dict[str, int]

    @property
    def command_index_lookup(self):
        return self._command_index_lookup

    _command_callbacks: list[Callable[[float, Any], None]]

    @property
    def command_callbacks(self):
        return self._command_callbacks

    def __init__(self, _id: UUID, name: str, parent: Union[Self, Rocket, None], dependencies: Iterable[Self]):
        '''
        :param dependencies: parts that will be updated before this part
        '''
        self._id = _id
        self.name = name

        self._measurement_shape = list(self.make_measurement_shape())
        self._accepted_commands = list(self.make_accepted_commands())
        self._command_callbacks = list(self.make_command_callbacks())

        self._measurement_index_lookup = dict((m[0], i) for i, m in enumerate(self.measurement_shape))
        self._command_index_lookup = dict((m[0], i) for i, m in enumerate(self.accepted_command))

        self.children = list()
        self.dependencies = list()
        self.logger = getLogger(f'p_{name}')

        self._measurement_buffer = list()

        self.enabled = self.start_enabled

        if isinstance(parent, Rocket):
            self.rocket = parent
            parent.add_part(self) # type: ignore
        elif isinstance(parent, Part):
            parent.children.append(self) # type: ignore
            self.parent = parent
            parent.rocket.add_part(self) # type: ignore

        self.dependencies.extend(dependencies)

    def update(self, now: float, iteration: int) -> None:
        """
        Method called per tick on every part to get it's own information updated based
        on real parameters

        commands: All the new commands received
        now: The current times in epoch seconds
        iteration: The index of this iteration, can be used to preform some actions more infrequently
        
        """
        pass

    def make_measurement_shape(self) -> Collection[Tuple[str, int, Type | str | list[Tuple[str, Type | str]]]]:
        """
        List of measurements that can be returned by this part. The measurements will be indexed by the order they are in this
        list. I.e. the first entry will be measurement of type 0, etc. If the order is changed external api providing readings
        for this part might break.

        You need to give each measurement:
         - a name (unique), 
         - a Quality of Service (QoS) level. Use 0 if you are not sure: https://www.hivemq.com/blog/mqtt-essentials-part-6-mqtt-quality-of-service-levels/
         - a type (see below)

        Each measurement can either be one single type of raw data using `str` or `bytes` or it can be a combination of values using
        defined by https://docs.python.org/3.5/library/struct.html. The struct format is ammended by two things:
         1. No endianes order allowed (always set to network by the system)
         2. Use brackets around a struct type to signify that it will be an array of this type e.g. `[?]` for an array of bools.
        A list of tuples with the name of the sub-element and one of the above listed descriptors is also allowed

        By default this reuturns:
          - 0: Enabled measurement with QoS 1 and type `bool`
          - 1: Log meassage with QoS 0 and type `str`

        It is recomended to keep these for standardization, however if you need to you may overwrite these.

        To combine your measurements with the defaults use:
        ```
            return [
                *super.make_measurement_shape(),
                ('your-measurement-1', 0, [('x', 'd'), ('y', 'd')]) # measurement of QoS 0 with two double values x and y
            ]
        ```
        """

        return [
            ('enabled', 1, '?'),
            ('log', 0, [('level', 'h'), ('msg', str)]),
            ('config', 1, self.make_config_shape())
            ]

    def make_accepted_commands(self) -> Collection[Tuple[str, Union[Type, str, list[Tuple[str, str]]]]]:
        """
        List of commands accepted by this part. The command will be indexed by the order they are in this
        list. I.e. the first entry will be command of type 0, etc. If the order is changed external APIs using
        these indecies might break (it is heavily encoureged to use the command name instead for this reason)

        You need to give each command:
         - a name (unique), 
         - a type (see below)

       Each command can either be one single type of raw data using `str` or `bytes` or it can be a combination of values using
        defined by https://docs.python.org/3.5/library/struct.html. The struct format is ammended by two things:
         1. No endianes order allowed (always set to network by the system)
         2. Use brackets around a struct type to signify that it will be an array of this type e.g. `[?]` for an array of bools.
        A list of tuples with the name of the sub-element and one of the above listed descriptors is also allowed

        By default this reuturns:
          - 0:   Enable command with a bool payload
          - 1:   Prints the config as a log statement
          - 2-?: Auto generated configure commands

        It is recomended to keep these for standardization, however you may overwrite them

        To combine your commands with the defaults use:
        ```
            return [
                *super.make_accepted_commands(),
                ('your-command-1', str) # command with a string payload
            ]
        ```
        """        

        configure_commands = [(f'configure_{x[0]}', x[1]) for x in self.make_config_shape()]

        return [
            ('enable', '?'),
            ('print_config', ''),
            *configure_commands
        ]
    
    def make_command_callbacks(self) -> Iterable[Callable[[float, Any], None]]:
        '''
        Provide callbacks for the commands defined in `make_accepted_commands`
        
        Methods need to accept a time and the payload for the command:

        ```
            def enable(self, time: float, payload: Any):
                ...
        ```

        Extend the default callbacks like this:
        ```
        return [
            *super().make_command_callbacks(),
            self.your_command_callback
        ]
        '''
        
        configure_callbacks = [self.make_configure_command(x[0]) for x in self.make_config_shape()]
        
        return [
            self.enable,
            self.print_config,
            *configure_callbacks
        ]
    
    def make_config_shape(self) -> list[Tuple[str, str | Type]]:
        '''
        Method returning the shape of this parts' configuration.
        The shape is defined in a similar format to make_measurement_shape (this is because the configuration becomes one of
        the measurements that can be taken). The format needs to be of type `list[(str, str | Type)]`

        An example configuration could look like this:

        ```
            return [
                *super().get_config_shape(), # Don't forget to include the bath config using super()
                ('some_float_config_value', 'f'),
                ('some_vector_config_value', 'fff') #3d vector made out of 3 floats
            ]
        ```

        By default this returns:

        ```
             return [
                ('start_enabled', '?'),
                ('min_update_period', 'f'),
                ('min_measurement_period', 'f')
            ]
        ```

        '''
    
        return [
           ('start_enabled', '?'),
           ('min_update_period', 'f'),
           ('min_measurement_period', 'f')
        ]

    def dump_config(self) -> dict[str, ComplexShapeType]:
        '''
        Needs to return a config as laid out by `make_config_shape` as a dictionary
        of config key name mapped to the value. Don't forget to extend
        your config with the base definition:

        ```
        return {
            **super().dump_config(),
            'your_config_parameter': self.some_property
        }
        ```

        As an example the default method looks like this:
        
        ```
        return {
            'start_enabled': self.start_enabled,
            'min_update_period': self.min_update_period.total_seconds(),
            'min_measurement_period': self.min_measurement_period.total_seconds()
        }
        ```

        '''

        return {
            'start_enabled': self.start_enabled,
            'min_update_period': self.min_update_period.total_seconds(),
            'min_measurement_period': self.min_measurement_period.total_seconds()
        }
    
    def load_config(self, config: dict[str, ComplexShapeType]):
        '''
        Counterpart to `dump_config()`
        
        Don't forget to call the base definition:
        ```
        super().read_config(config)
        ```

        Note: make sure to check if the key is in the config with
        ```
        if 'config_key' in config:
            self.parameter = config['config_key']

        ```
        '''

        if 'start_enabled' in config:
            self.start_enabled = bool(config['start_enabled'])
        if 'min_update_period' in config:
            self.min_update_period = timedelta(seconds=float(config['min_update_period'])) # type: ignore
        if 'min_update_period' in config:
            self.min_update_period = timedelta(seconds=float(config['min_update_period'])) # type: ignore

    def collect_measurements(self, now: float, iteration: int):
        """Method called before measurement buffer is swapped. I.e. last chance to submit measurements this iteration"""
        return 

    def flush(self):
        """Method called at the end of each flight tick. This is to release any memory from the last iteration"""
        pass        

    def inflate_measurement(self, measurement: Measurements) -> dict[str, Union[str, int, float]]:
        res = dict[str, Union[str, int, float]]()
        i = 0
        for (key, _) in self.make_measurement_shape():
            if measurement[i] is None:
                continue
            m = measurement[i]
            if m is not None:
                res[key] = m
            i += 1
        
        return res

    def enable(self, timestamp: float, enable: bool):

        # Prevent out of order commands
        if timestamp <= self._last_enable_command:
            return
        
        self._last_enable_command = timestamp

        self.enabled = enable

        self.submit_measurement_by_name('enable', enable, time.time())

    def print_config(self, timestamp: float, _):
        '''Prints the config as a log message'''

        self.log(json.dumps(self.dump_config()))

    def make_configure_command(self, config_parameter_name: str):

        def configure_parameter(timestamp: float, *values):
            if len(values) > 1:
                self.load_config({config_parameter_name: values})
            else:
                self.load_config({config_parameter_name: values[0]}) # type: ignore

        return configure_parameter

    def log(self, msg: str, level: int = INFO_LOG_LEVEL, datetime: float | None = None):
        self.logger.log(level, msg)

        # Emit measurement as 
        if level >= INFO_LOG_LEVEL:
            self.submit_measurement_raw([datetime or time.time(), 1, (level, msg)])

    def submit_measurement_raw(self, measruement: Measurement):
        self._measurement_buffer.append(measruement)

    def submit_measurement(self, measurement_index: int, measurement: MeasurementTypes | Sequence[MeasurementTypes], datetime: float | None = None ):
        self.submit_measurement_raw((datetime or time.time(), measurement_index, measurement))

    def submit_measurement_by_name(self, measurement_name: str, measurement: MeasurementTypes | Sequence[MeasurementTypes], datetime: float | None = None):
        '''Uses `measurement_index_lookup` and is therefore slower. Consider using `submit_measurement` for high performance cases'''
        self.submit_measurement_raw((datetime or time.time(), self.measurement_index_lookup[measurement_name], measurement))

class Rocket:
    """ Class representing the rocket """

    name: str

    version: int = 0

    parts = list[Part]()

    id: Union[None, UUID] = None

    part_lookup = dict[UUID, Part]()
    
    def __init__(self, name: str):
        self.name = name

    def add_part(self, part: Part):
        self.parts.append(part)
        part._index = len(self.parts) - 1
        self.part_lookup[part._id] = part
        
