"""
Abstract Base Strategy Interface for Image Providers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ImageProvider(ABC):
    """
    Contract that all external educational diagram/image providers must implement.
    """

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Return the unique name of this provider.
        """
        pass

    @abstractmethod
    async def search_images(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search and return standardized candidate image lists.
        Return List of Dicts containing:
            title, url, description, width, height, license, source, thumbnail
        """
        pass
