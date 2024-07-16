from dataclasses import dataclass, field
from typing import Tuple, Union
from uuid import UUID

from marshmallow import fields

from core.helper.model_helper import make_safe_schema


@dataclass()
class FlightMeasurementCompact: 

    part_id: Union[UUID, None]

    field_names: list[str]

    measurements: list[Tuple[float, list[Union[str, int, float]]]] = field(default_factory=list)


class FlightMeasurementCompactSchema(make_safe_schema(FlightMeasurementCompact)):

    part_id = fields.UUID(allow_none=True)

    field_names = fields.List(fields.String)

    measurements = fields.List(fields.Tuple((fields.Float, fields.List(fields.Raw(allow_none=True)))))