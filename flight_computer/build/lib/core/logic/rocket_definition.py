from typing import Any, Literal, Sequence, Union, cast, Iterable, Tuple, Type, Collection
from datetime import datetime, timedelta
from typing_extensions import Self
from uuid import UUID
from abc import ABC, abstractclassmethod
from marshmallow import Schema

from core.helper.model_helper import SchemaExt
from core.logic.commands.command import Command, Command

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

MeasurementTypes = Union[str, int, float, None]
Measurements = Sequence[MeasurementTypes]

#endregion

    
class Part(ABC):
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
    Time in unix seconds since the parts measurements where returned
    Set by the main execution loop after collect_measurements is called
    '''

    def __init__(self, _id: UUID, name: str, parent: Union[Self, Rocket, None], dependencies: Iterable[Self]):
        '''
        :param dependencies: parts that will be updated before this part
        '''
        self._id = _id
        self.name = name

        self.children = list()
        self.dependencies = list()

        if type(parent) is Rocket:
            self.rocket = parent
            parent.add_part(self) # type: ignore
        elif type(parent) is Part:
            parent.children.append(self) # type: ignore
            self.parent = parent
            parent.rocket.add_part(self) # type: ignore

        self.dependencies.extend(dependencies)

    @abstractclassmethod
    def update(self, commands: Iterable[Command], now: float, iteration: int) -> Union[None, Collection[Command]]:
        """
        Method called per tick on every part to get it's own information updated based
        on real parameters

        commands: All the new commands received
        now: The current times in epoch seconds
        iteration: The index of this iteration, can be used to preform some actions more infrequently
        
        """
        pass

    @abstractclassmethod
    def get_measurement_shape(self) -> Collection[Tuple[str, str]]:
        """Name and struct descriptor of each measured value. See https://docs.python.org/3.5/library/struct.html for struct descriptor instructions"""
        return list[Tuple[str, str]]()

    @abstractclassmethod
    def get_accepted_commands(self) -> Iterable[Type[Command]]:
        '''Commands that can be processed by this part'''
        return []

    @abstractclassmethod
    def collect_measurements(self, now: float, iteration: int) -> Union[None, Sequence[Measurements]]:
        """Should give back all measurements obtained since the last tick"""
        return []

    def flush(self):
        """Method called at the end of each flight tick. This is to release any memory from the last iteration"""
        pass        

    def inflate_measurement(self, measurement: Measurements) -> dict[str, Union[str, int, float]]:
        res = dict[str, Union[str, int, float]]()
        i = 0
        for (key, _) in self.get_measurement_shape():
            if measurement[i] is None:
                continue
            m = measurement[i]
            if m is not None:
                res[key] = m
            i += 1
        
        return res

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
        
