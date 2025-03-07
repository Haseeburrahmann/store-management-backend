# app/utils/formatting.py
from typing import Dict, List, Any, Union, Optional
from bson import ObjectId


def format_object_ids(data: Union[Dict[str, Any], List[Dict[str, Any]], None]) -> Union[
    Dict[str, Any], List[Dict[str, Any]], None]:
    """
    Convert ObjectId to strings in a document or list of documents.
    Works recursively for nested dictionaries and lists.
    """
    if data is None:
        return None

    if isinstance(data, list):
        # Format a list of documents
        return [format_object_ids(item) for item in data]
    elif isinstance(data, dict):
        # Format a single document
        result = {}
        for key, value in data.items():
            if isinstance(value, ObjectId):
                # Convert ObjectId to string
                result[key] = str(value)
            elif isinstance(value, (dict, list)):
                # Format nested objects
                result[key] = format_object_ids(value)
            else:
                # Keep other values as-is
                result[key] = value
        return result
    else:
        # Return non-dict/list values as-is
        return data


def ensure_object_id(id_value: Any) -> Optional[ObjectId]:
    """
    Safely convert a string or ObjectId to an ObjectId.
    Returns None if conversion is not possible.
    """
    if id_value is None:
        return None

    if isinstance(id_value, ObjectId):
        return id_value

    if isinstance(id_value, str) and ObjectId.is_valid(id_value):
        return ObjectId(id_value)

    return None


def id_to_str(id_value: Any) -> Optional[str]:
    """
    Convert an ObjectId to string format if it's valid.
    Returns None if the value cannot be converted.
    """
    if id_value is None:
        return None

    if isinstance(id_value, ObjectId):
        return str(id_value)

    if isinstance(id_value, str):
        if ObjectId.is_valid(id_value):
            return id_value
        return None

    return None