# app/utils/formatting.py
from typing import Dict, List, Any, Union
from bson import ObjectId


# In app/utils/formatting.py
def format_object_ids(data: Union[Dict[str, Any], List[Dict[str, Any]], None]) -> Union[
    Dict[str, Any], List[Dict[str, Any]], None]:
    """
    Convert ObjectId to strings in a document or list of documents
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