from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import strftime
from typing import Type, Union
import uuid
from marshmallow import Schema, fields, validate
from app.helper.model_helper import make_safe_schema

@dataclass
class FlightMeasurementSeriesIdentifier:
    
    _flight_id: uuid.UUID

    _vessel_part_id: uuid.UUID

class FlightMeasurementSeriesIdentifierSchema(make_safe_schema(FlightMeasurementSeriesIdentifier)):
    """
    Identifies which time series the measurement belongs to
    """

    _flight_id = fields.UUID(required = True)

    _vessel_part_id = fields.UUID(required = True)

@dataclass
class FlightMeasurementDescriptor:
    """
    Describes a field in the measured data
    """

    name: str

    type: str
    """The type of the that measurement. Can be a "string", "int" or a "float" """

class FlightMeasurementDescriptorSchema(make_safe_schema(FlightMeasurementDescriptor)):
    """
    Describes a field in the measured data
    """

    name = fields.String()

    type = fields.String(validate= validate.Regexp(r"(string)|(int)|(float)"))
    """The type of the that measurement. Can be a "string", "int" or a "float" """

@dataclass
class FlightMeasurement:
    """A single measurement relayed back by the model
    """
    
    _datetime: datetime
    """The datetime the measurement is for (primary index)"""

    measured_values: dict[str, Union[str, int, float]] = field(default_factory=dict)
    """The measured values themselves"""

    _id: Union[uuid.UUID, None] = None

    part_id: Union[uuid.UUID, None] = None
    """Optional part id. Used to send the part over the network, not committed to database"""

class FlightMeasurementSchema(make_safe_schema(FlightMeasurement)):
    """A single measurement relayed back by the model
    """

    _id = fields.String()

    _datetime = fields.AwareDateTime(required = True, default_timezone=timezone.utc)
    """The datetime the measurement is for (primary index)"""

    measured_values = fields.Dict(keys = fields.Str(), values = fields.Raw())
    """The measured values themselves"""

    part_id = fields.UUID(optional=True, allow_none=True)
    """Optional part id. Used to send the part over the network, not committed to database"""

class FlightMeasurementAggregatedSchema(Schema):
    """A single measurement relayed back by the model
    """

    _id = fields.Raw()

    start_date = fields.AwareDateTime(required = True, default_timezone=timezone.utc)
    """The datetime the range starts"""

    end_date = fields.AwareDateTime(required = True, default_timezone=timezone.utc)
    """The datetime the range starts"""

    measured_values = fields.Raw()
    """The measured values themselves"""

    flight_id = fields.UUID(optional=True, allow_none=True)

    part_id = fields.UUID(optional=True, allow_none=True)
    """Optional part id. Used to send the part over the network, not committed to database"""

def getConcreteMeasuredValuesType(schemas: list[FlightMeasurementDescriptor]):
    """
    Creates a new marshmallow definition according to the past schemas.
    This definition will have the measurement name as the property key
    and the value as the passed type
    """

    res_types = dict()

    for schema in schemas:
        if schema.type == 'string':
            res_types[schema.name] = fields.String(required=False, allow_none=True)
        elif schema.type == 'int':
            res_types[schema.name] = fields.Int(required=False, allow_none=True)
        elif schema.type == 'float':
            res_types[schema.name] = fields.Float(required=False, allow_none=True)
        else:
            raise NotImplementedError(f'Schema type {schema.type} not supported')
        
    # Create a new type with a random uuid as it's name
    # Have it inherit from the schema class and implement the
    # previously created fields
    return type(str(uuid.uuid4()).upper(), (Schema, ), res_types)

def getConcreteMeasurementSchema(schema: list[FlightMeasurementDescriptor]) -> Type[FlightMeasurementSchema]:
    """
    Creates a new FlightMeasurement schema based on the requested properties.
    Replaces the `FlightMeasurement.measured_values` with a nested schema
    which has the correct keys and value types for validation
    """
    return type(str(uuid.uuid4()).upper(), (FlightMeasurementSchema, ), dict( measured_values = fields.Nested(getConcreteMeasuredValuesType(schema)) ))
    


