"""
Base repository pattern implementation for MongoDB collections.
"""
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException, status

from app.utils.id_handler import IdHandler
from app.utils.datetime_handler import DateTimeHandler


class BaseRepository:
    """
    Base repository class that implements standard CRUD operations for MongoDB collections.
    Handles ID conversions, formatting, and standard error patterns.
    """

    def __init__(self, collection):
        """
        Initialize repository with MongoDB collection.

        Args:
            collection: Motor AsyncIOMotorCollection instance
        """
        self.collection = collection

    async def find_by_id(self, id_value: Any) -> Optional[Dict[str, Any]]:
        """
        Find a document by ID with consistent ID handling.

        Args:
            id_value: ID to look for (string or ObjectId)

        Returns:
            Document dict with formatted IDs or None if not found
        """
        document, _ = await IdHandler.find_document_by_id(self.collection, id_value)
        if document:
            return IdHandler.format_object_ids(document)
        return None

    async def find_many(self,
                        query: Dict[str, Any] = None,
                        skip: int = 0,
                        limit: int = 100,
                        sort_by: str = None,
                        sort_desc: bool = False) -> List[Dict[str, Any]]:
        """
        Find documents matching query with pagination.

        Args:
            query: MongoDB query dictionary
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort_by: Field to sort by
            sort_desc: If True, sort in descending order

        Returns:
            List of documents with formatted IDs
        """
        if query is None:
            query = {}

        # Create cursor
        cursor = self.collection.find(query).skip(skip).limit(limit)

        # Apply sorting if specified
        if sort_by:
            direction = -1 if sort_desc else 1
            cursor = cursor.sort(sort_by, direction)

        # Execute query and format results
        documents = await cursor.to_list(length=limit)
        return IdHandler.format_object_ids(documents)

    async def count(self, query: Dict[str, Any] = None) -> int:
        """
        Count documents matching query.

        Args:
            query: MongoDB query dictionary

        Returns:
            Count of matching documents
        """
        if query is None:
            query = {}
        return await self.collection.count_documents(query)

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new document.

        Args:
            data: Document data

        Returns:
            Created document with formatted IDs

        Raises:
            HTTPException: If creation fails
        """
        try:
            # Set default timestamps
            if "created_at" not in data:
                data["created_at"] = DateTimeHandler.get_current_datetime()
            if "updated_at" not in data:
                data["updated_at"] = DateTimeHandler.get_current_datetime()

            # Insert document
            result = await self.collection.insert_one(data)

            # Return the created document
            created_doc = await self.find_by_id(result.inserted_id)
            if not created_doc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Document was created but could not be retrieved"
                )

            return created_doc
        except Exception as e:
            # Handle duplicate key error
            if "duplicate key error" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A document with this ID already exists"
                )
            # Re-raise other exceptions
            raise

    async def update(self, id_value: Any, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a document by ID.

        Args:
            id_value: ID of document to update
            data: New field values

        Returns:
            Updated document with formatted IDs or None if not found
        """
        # Find the document first to make sure it exists
        document, doc_id = await IdHandler.find_document_by_id(self.collection, id_value)
        if not document:
            return None

        # Prepare update data
        update_data = {k: v for k, v in data.items() if k != "_id"}
        update_data["updated_at"] = DateTimeHandler.get_current_datetime()

        # Perform update
        await self.collection.update_one(
            {"_id": doc_id},
            {"$set": update_data}
        )

        # Return updated document
        updated_doc = await self.find_by_id(id_value)
        return updated_doc

    async def delete(self, id_value: Any) -> bool:
        """
        Delete a document by ID.

        Args:
            id_value: ID of document to delete

        Returns:
            True if document was deleted, False if not found
        """
        # Find the document first to make sure it exists
        document, doc_id = await IdHandler.find_document_by_id(self.collection, id_value)
        if not document:
            return False

        # Perform delete
        result = await self.collection.delete_one({"_id": doc_id})
        return result.deleted_count > 0

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a single document matching query.

        Args:
            query: MongoDB query dictionary

        Returns:
            Document dict with formatted IDs or None if not found
        """
        document = await self.collection.find_one(query)
        if document:
            return IdHandler.format_object_ids(document)
        return None