# app/utils/object_id.py
from bson import ObjectId
from typing import Any, Optional


class PyObjectId(str):
    """
    Custom type for handling MongoDB ObjectId with Pydantic v2 compatibility.
    Ensures consistent ObjectId handling throughout the application.
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> str:
        """
        Validate and convert input value to a string representation of an ObjectId
        """
        if v is None:
            return None

        if isinstance(v, ObjectId):
            return str(v)

        if isinstance(v, str):
            if ObjectId.is_valid(v):
                return str(v)
            raise ValueError(f"Invalid ObjectId: {v}")

        if isinstance(v, (int, float)):
            raise ValueError(f"Invalid ObjectId type: {type(v)}")

        raise ValueError(f"Invalid ObjectId type: {type(v)}")

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        return {
            "type": "string",
            "description": "ObjectId represented as string"
        }

    @classmethod
    def to_mongo(cls, value: str) -> Optional[ObjectId]:
        """
        Convert string ID to MongoDB ObjectId when needed
        """
        if value is None:
            return None

        if isinstance(value, ObjectId):
            return value

        if ObjectId.is_valid(value):
            return ObjectId(value)

        return None