"""
ID Handler module for consistent MongoDB ObjectId handling throughout the application.
"""
from typing import Any, Dict, List, Optional, Union, Tuple
from bson import ObjectId
from fastapi import HTTPException, status

class IdHandler:
    """
    Centralized service for handling MongoDB ObjectIds consistently throughout the application.
    Provides methods for conversion, validation, and standardized document lookup.
    """

    @staticmethod
    def ensure_object_id(id_value: Any) -> Optional[ObjectId]:
        """
        Safely convert a string or ObjectId to an ObjectId.
        Returns None if conversion is not possible.

        Args:
            id_value: Value to convert to ObjectId (string or ObjectId)

        Returns:
            ObjectId or None if conversion failed
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

        Args:
            data: MongoDB document or list of documents

        Returns:
            Document(s) with ObjectIds converted to strings
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
        Convert an ID (ObjectId or string) to string format.
        Returns None if the value cannot be converted.

        Args:
            id_value: Value to convert to string

        Returns:
            String representation of ID or None
        """
        if id_value is None:
            return None

        if isinstance(id_value, ObjectId):
            return str(id_value)

        if isinstance(id_value, str):
            return id_value

        # Best effort conversion for other types
        try:
            return str(id_value)
        except Exception:
            return None

    @staticmethod
    async def find_document_by_id(collection, doc_id: str, not_found_msg: str = "Document not found") -> Tuple[
        Any, Any]:
        """
        Standard method to find a document by ID using a consistent lookup strategy.
        Returns a tuple of (document, object_id) if found, or (None, None) if not found.

        Args:
            collection: MongoDB collection to query
            doc_id: ID to look for
            not_found_msg: Custom message for not found case

        Returns:
            Tuple of (document, id_used_for_lookup)
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

        Args:
            document: Document to check
            message: Error message if document is None
            status_code: HTTP status code to use

        Returns:
            The document if found

        Raises:
            HTTPException if document is None
        """
        if not document:
            raise HTTPException(
                status_code=status_code,
                detail=message
            )
        return document

    @staticmethod
    def generate_id() -> str:
        """
        Generate a new ObjectId as string

        Returns:
            String representation of a new ObjectId
        """
        return str(ObjectId())