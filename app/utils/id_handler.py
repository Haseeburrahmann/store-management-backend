# app/utils/id_handler.py
from typing import Any, Dict, List, Optional, Union, Tuple
from bson import ObjectId
from fastapi import HTTPException, status


class IdHandler:
    """
    Centralized service for handling MongoDB ObjectIds consistently throughout the application.
    """

    @staticmethod
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

    @staticmethod
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
            return [IdHandler.format_object_ids(item) for item in data]
        elif isinstance(data, dict):
            # Format a single document
            result = {}
            for key, value in data.items():
                if isinstance(value, ObjectId):
                    # Convert ObjectId to string
                    result[key] = str(value)
                elif isinstance(value, (dict, list)):
                    # Format nested objects
                    result[key] = IdHandler.format_object_ids(value)
                else:
                    # Keep other values as-is
                    result[key] = value
            return result
        else:
            # Return non-dict/list values as-is
            return data

    @staticmethod
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
            return id_value  # Return as is if it's a string but not a valid ObjectId

        return str(id_value)  # Best effort conversion for other types

    @staticmethod
    async def find_document_by_id(collection, doc_id: str, not_found_msg: str = "Document not found") -> Tuple[
        Any, Any]:
        """
        Standard method to find a document by ID using a consistent lookup strategy.
        Returns a tuple of (document, object_id) if found, or (None, None) if not found.

        This eliminates duplicated lookup code across services.
        """
        # 1. Try with ObjectId
        obj_id = IdHandler.ensure_object_id(doc_id)
        document = None

        if obj_id:
            document = await collection.find_one({"_id": obj_id})
            if document:
                return document, obj_id

        # 2. Try with string ID directly
        document = await collection.find_one({"_id": doc_id})
        if document:
            return document, document["_id"]

        # 3. Try string comparison (limit to reasonable number)
        all_docs = await collection.find().limit(100).to_list(length=100)
        for doc in all_docs:
            if str(doc.get('_id')) == doc_id:
                return doc, doc["_id"]

        # No document found
        return None, None

    @staticmethod
    def raise_if_not_found(document: Any, message: str, status_code: int = status.HTTP_404_NOT_FOUND):
        """
        Helper method to raise HTTPException if document is not found
        """
        if not document:
            raise HTTPException(
                status_code=status_code,
                detail=message
            )
        return document