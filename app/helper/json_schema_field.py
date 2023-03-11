import json
from typing import cast
from marshmallow import fields, ValidationError
from jsonschema import Validator

class JSON_Schema_Field(fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):

        if type(value) is not dict:
            try:
                value = json.loads(value)
            except:
                ValidationError('Invalid json')

        Validator.check_schema(cast(dict, value))

        return value
