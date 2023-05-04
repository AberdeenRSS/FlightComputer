from dataclasses import dataclass, field
from typing import Any, TypeVar, cast
from uuid import UUID
from marshmallow import Schema, fields, post_load
from app.models.vessel_part import VesselPart
from app.helper.model_helper import SchemaExt, make_safe_schema

from app.models.vessel_part import VesselPartSchema

@dataclass
class Vessel:
    
    _id: UUID
    """
    The id of the vessel (primary identifier)
    """

    _version: int = 0
    """
    The version of this vessel
    This is to track if any of the information about the vessel
    changes. Old versions of the vessel can still be accessed
    to allow old flights to still be valid
    """

    name: str = ''
    """
    Name of the vessel
    """

    parts: list[VesselPart] = field(default_factory=list)
    """
    All the parts (components) of the vessel
    """

class VesselSchema(make_safe_schema(Vessel)):

    _id = fields.UUID(required=True)
    """
    The id of the vessel (primary identifier)
    """

    _version = fields.Int(required=False)
    """
    The version of this vessel
    This is to track if any of the information about the vessel
    changes. Old versions of the vessel can still be accessed
    to allow old flights to still be valid
    """

    name = fields.String(required=True)
    """
    Name of the vessel
    """

    parts = fields.List(fields.Nested(VesselPartSchema), load_default=[], dump_default=[])
    """
    All the parts (components) of the vessel. The parts have hierarchy by linking between each other
    """


