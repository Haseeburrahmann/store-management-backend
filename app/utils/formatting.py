# app/utils/formatting.py
from typing import Dict, List, Any, Union, Optional
from bson import ObjectId
from app.utils.id_handler import IdHandler


# Redefine to use the centralized handler but maintain backwards compatibility
def format_object_ids(data: Union[Dict[str, Any], List[Dict[str, Any]], None]) -> Union[
    Dict[str, Any], List[Dict[str, Any]], None]:
    """
    Convert ObjectId to strings in a document or list of documents.
    Works recursively for nested dictionaries and lists.

    This function now uses the centralized IdHandler for consistency.
    """
    return IdHandler.format_object_ids(data)


def ensure_object_id(id_value: Any) -> Optional[ObjectId]:
    """
    Safely convert a string or ObjectId to an ObjectId.
    Returns None if conversion is not possible.

    This function now uses the centralized IdHandler for consistency.
    """
    return IdHandler.ensure_object_id(id_value)


def id_to_str(id_value: Any) -> Optional[str]:
    """
    Convert an ObjectId to string format if it's valid.
    Returns None if the value cannot be converted.

    This function now uses the centralized IdHandler for consistency.
    """
    return IdHandler.id_to_str(id_value)