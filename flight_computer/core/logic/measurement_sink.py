from typing import Sequence, Union
from typing_extensions import Self
from uuid import UUID
from flight_computer.core.api_client import ApiClient
from flight_computer.core.logic.rocket_definition import Measurements, Part, Rocket

from flight_computer.core.models.flight import Flight
from flight_computer.core.mqtt_client import MqttClient

MeasurementsByPart = dict[Part, tuple[float, float, Sequence[Measurements]]]


class MeasurementSinkBase(Part):
    ''' 
    Abstract base class for different kinds of measurements sink.

    Note: measurement sinks are special parts as they are given all measurements
    of all the other parts to store them, send them away, etc.
    '''

    measurement_buffer: list[MeasurementsByPart]
    '''
    The measurement buffer. It gets appended with all new measurements with
    each iteration of the main flight loop. The part itself is responsible
    to flush the buffer periodically and ensure that it doesn't grow too
    much if the data cannot be cleared in time.

    Warning: The list can be modified, but not individual values, as they
    might be held by other sinks as well
    '''

    def __init__(self, _id: UUID, name: str, parent: Union[Self, Rocket, None], **kwargs):

        if 'dependencies' not in kwargs:
            kwargs['dependencies'] = list()

        super().__init__(_id, name, parent, **kwargs)

        self.measurement_buffer = list()


class ApiMeasurementSinkBase(MeasurementSinkBase):
    api_client: ApiClient

    mqtt_client: MqttClient

    flight: Flight