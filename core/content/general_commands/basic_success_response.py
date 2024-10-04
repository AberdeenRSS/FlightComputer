
from dataclasses import dataclass
from typing import Union
from marshmallow import Schema, fields
from core.helper.model_helper import make_safe_schema

@dataclass
class BasicErrorResponse:

    error_msg: Union[str, None] = None

class BasicErrorResponseSchema(make_safe_schema(BasicErrorResponse)):

    error_msg = fields.String(allow_none=True)
