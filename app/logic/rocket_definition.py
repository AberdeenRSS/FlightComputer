
from typing import Any, Literal, Union, cast, Iterable, Tuple, Type
from datetime import datetime
from typing_extensions import Self
from uuid import UUID
from abc import ABC, abstractclassmethod
from marshmallow import Schema

from app.helper.model_helper import SchemaExt
from app.logic.commands.command import Command, CommandBase

#Maybe

# PART_CATEGORY_SENSOR = 'SENSOR'
# ''' Meant for any input data, i.e. sensors. Sensors will always be called first in the update order'''

# PART_CATEGORY_DIRECTOR = 'DIRECTOR'

# PART_CATEGORY_CONTROL = 'CONTROL'
# ''' 
# Meant for all control parts, i.e. actuators, motors, etc. Control parts will always be called last in the update order so
# that all potential control inputs have already happened
# '''

# part_categories = Literal['SENSOR', 'CONTROL']

#region: Definitions
class Rocket: pass # type: ignore

#endregion


    
class Part(ABC):
    """ Base class for all parts. Inherit to define a specific part"""

    _id: UUID

    type: str

    virtual: bool = False

    name: str

    rocket: Rocket

    children: list[Self] = list()

    parent: Union[Self, None] = None

    dependencies: list[Self] = list()


    def __init__(self, _id: UUID, name: str, parent: Union[Self, Rocket, None], dependencies: Iterable[Self]):
        '''
        :param dependencies: Parts that will be updated before this part
        '''
        self._id = _id
        self.name = name

        if type(parent) is Rocket:
            self.rocket = parent
            parent.add_part(self) # type: ignore
        elif type(parent) is Part:
            parent.children.append(self) # type: ignore
            self.parent = parent
            parent.rocket.add_part(self) # type: ignore

        self.dependencies.extend(dependencies)

    @abstractclassmethod
    def update(self, commands: Iterable[Command]):
        """Method called per tick on every part to get it's own information updated based
        on real parameters"""
        pass

    @abstractclassmethod
    def get_measurement_shape(self) -> Iterable[Tuple[str, Type]]:
        """Name and type of the measurement values of this part"""
        return []

    @abstractclassmethod
    def get_accepted_commands(self) -> Iterable[Type[CommandBase]]:
        '''Commands that can be processed by this part'''
        return []

    @abstractclassmethod
    def collect_measurements(self) -> Iterable[Iterable[Union[str, float, int, None]]]:
        """Should give back all measurements obtained since the last tick"""
        return []

    def flush(self):
        """Method called at the end of each flight tick. This is to release any memory from the last iteration"""
        pass        

    def inflate_measurement(self, measurement: Iterable[Union[str, float, int, None]]) -> dict[str, Union[str, float, int]]:
        res = dict()
        m = list(measurement)
        i = 0
        for k in self.get_measurement_shape():
            res[k] = m[i]
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
        self.part_lookup[part._id] = part
        
