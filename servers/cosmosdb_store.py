"""
Azure Cosmos DB Store for py-key-value AsyncKeyValue protocol.

This module provides a Cosmos DB implementation of the AsyncKeyValue protocol,
suitable for use with FastMCP's OAuth proxy client storage.

Based on the proposal in https://github.com/strawgate/py-key-value/issues/44
"""

import logging
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any, SupportsFloat

from azure.cosmos.aio import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError

logger = logging.getLogger(__name__)


class ManagedEntry:
    """A managed entry with value and expiration tracking."""

    def __init__(
        self,
        value: dict[str, Any],
        created_at: datetime | None = None,
        expires_at: datetime | None = None,
    ):
        self.value = value
        self.created_at = created_at or datetime.now(timezone.utc)
        self.expires_at = expires_at

    @property
    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def ttl_seconds(self) -> float | None:
        """Get remaining TTL in seconds, or None if no expiration."""
        if self.expires_at is None:
            return None
        remaining = (self.expires_at - datetime.now(timezone.utc)).total_seconds()
        return max(0.0, remaining)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for storage."""
        return {
            "value": self.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ManagedEntry":
        """Deserialize from dictionary."""
        created_at = None
        expires_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"])
        return cls(
            value=data.get("value", {}),
            created_at=created_at,
            expires_at=expires_at,
        )


class CosmosDBStore:
    """
    Azure Cosmos DB implementation of the AsyncKeyValue protocol.

    This store uses Cosmos DB's NoSQL API to store key-value pairs.
    Documents are stored with:
    - id: The key
    - collection: Partition key for logical grouping
    - value: The stored value (as JSON)
    - created_at: Creation timestamp
    - expires_at: Expiration timestamp (optional)
    - ttl: Cosmos DB native TTL in seconds (optional)

    Usage:
        from azure.cosmos.aio import CosmosClient
        from azure.identity.aio import DefaultAzureCredential

        credential = DefaultAzureCredential()
        cosmos_client = CosmosClient(url="https://...", credential=credential)
        container = cosmos_client.get_database_client("mydb").get_container_client("oauth-clients")

        store = CosmosDBStore(container=container)

        # Use with FastMCP OAuth proxy
        auth = AzureProvider(
            client_id="...",
            client_secret="...",
            client_storage=store,
        )
    """

    def __init__(
        self,
        container: ContainerProxy,
        default_collection: str = "default",
    ):
        """
        Initialize the Cosmos DB store.

        Args:
            container: An Azure Cosmos DB container proxy (async).
            default_collection: Default collection/partition key to use.
        """
        self._container = container
        self.default_collection = default_collection

    def _make_document_id(self, collection: str, key: str) -> str:
        """Create a unique document ID from collection and key."""
        # Use a compound key to ensure uniqueness across collections
        return f"{collection}:{key}"

    async def get(
        self,
        key: str,
        *,
        collection: str | None = None,
    ) -> dict[str, Any] | None:
        """Retrieve a value by key from the specified collection."""
        collection = collection or self.default_collection
        doc_id = self._make_document_id(collection, key)

        try:
            item = await self._container.read_item(item=doc_id, partition_key=collection)
            entry = ManagedEntry.from_dict(item.get("entry", {}))

            if entry.is_expired:
                # Clean up expired entry
                await self.delete(key=key, collection=collection)
                return None

            return dict(entry.value)
        except CosmosResourceNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error reading from Cosmos DB: {e}")
            return None

    async def get_many(self, keys: Sequence[str], *, collection: str | None = None) -> list[dict[str, Any] | None]:
        """Retrieve multiple values by key from the specified collection."""
        return [await self.get(key=key, collection=collection) for key in keys]

    async def ttl(self, key: str, *, collection: str | None = None) -> tuple[dict[str, Any] | None, float | None]:
        """Retrieve the value and TTL information for a key."""
        collection = collection or self.default_collection
        doc_id = self._make_document_id(collection, key)

        try:
            item = await self._container.read_item(item=doc_id, partition_key=collection)
            entry = ManagedEntry.from_dict(item.get("entry", {}))

            if entry.is_expired:
                await self.delete(key=key, collection=collection)
                return (None, None)

            return (dict(entry.value), entry.ttl_seconds)
        except CosmosResourceNotFoundError:
            return (None, None)
        except Exception as e:
            logger.error(f"Error reading TTL from Cosmos DB: {e}")
            return (None, None)

    async def ttl_many(
        self, keys: Sequence[str], *, collection: str | None = None
    ) -> list[tuple[dict[str, Any] | None, float | None]]:
        """Retrieve multiple values and TTL information by key."""
        return [await self.ttl(key=key, collection=collection) for key in keys]

    async def put(
        self,
        key: str,
        value: Mapping[str, Any],
        *,
        collection: str | None = None,
        ttl: SupportsFloat | None = None,
    ) -> None:
        """Store a key-value pair in the specified collection with optional TTL."""
        collection = collection or self.default_collection
        doc_id = self._make_document_id(collection, key)

        now = datetime.now(timezone.utc)
        expires_at = None
        cosmos_ttl = None

        if ttl is not None:
            ttl_seconds = float(ttl)
            if ttl_seconds > 0:
                expires_at = now + timedelta(seconds=ttl_seconds)
                cosmos_ttl = int(ttl_seconds)

        entry = ManagedEntry(
            value=dict(value),
            created_at=now,
            expires_at=expires_at,
        )

        document = {
            "id": doc_id,
            "collection": collection,
            "key": key,
            "entry": entry.to_dict(),
        }

        # Add Cosmos DB native TTL if specified
        if cosmos_ttl is not None:
            document["ttl"] = cosmos_ttl

        try:
            await self._container.upsert_item(body=document)
        except Exception as e:
            logger.error(f"Error writing to Cosmos DB: {e}")
            raise

    async def put_many(
        self,
        keys: Sequence[str],
        values: Sequence[Mapping[str, Any]],
        *,
        collection: str | None = None,
        ttl: SupportsFloat | None = None,
    ) -> None:
        """Store multiple key-value pairs in the specified collection."""
        if len(keys) != len(values):
            raise ValueError("Number of keys must match number of values")

        for key, value in zip(keys, values):
            await self.put(key=key, value=value, collection=collection, ttl=ttl)

    async def delete(self, key: str, *, collection: str | None = None) -> bool:
        """Delete a key-value pair from the specified collection."""
        collection = collection or self.default_collection
        doc_id = self._make_document_id(collection, key)

        try:
            await self._container.delete_item(item=doc_id, partition_key=collection)
            return True
        except CosmosResourceNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error deleting from Cosmos DB: {e}")
            return False

    async def delete_many(self, keys: Sequence[str], *, collection: str | None = None) -> int:
        """Delete multiple key-value pairs from the specified collection."""
        deleted_count = 0
        for key in keys:
            if await self.delete(key=key, collection=collection):
                deleted_count += 1
        return deleted_count
