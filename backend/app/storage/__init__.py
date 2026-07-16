"""
Storage abstraction module.
"""

from app.storage.base import BaseStorage
from app.storage.local import LocalStorage

# Scoped singleton storage engine instance
_storage_engine: BaseStorage | None = None


def get_storage() -> BaseStorage:
    """
    Return the configured singleton storage engine.

    Allows runtime swapping of storage providers (e.g. Local vs Cloud).
    """
    global _storage_engine
    if _storage_engine is None:
        _storage_engine = LocalStorage()
    return _storage_engine


__all__ = ["BaseStorage", "LocalStorage", "get_storage"]
