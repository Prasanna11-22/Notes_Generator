"""
Storage abstraction base class.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class BaseStorage(ABC):
    """
    Abstract Base Class for file storage engines.

    Allows swapping between Local Filesystem, AWS S3, MinIO, or Google Cloud Storage.
    """

    @abstractmethod
    async def upload(self, file_content: bytes, storage_path: str) -> None:
        """
        Upload binary file content to the target storage path.

        :param file_content: Raw bytes of the file.
        :param storage_path: Relative destination storage path.
        """
        pass

    @abstractmethod
    async def download(self, storage_path: str) -> bytes:
        """
        Download raw binary file content from storage.

        :param storage_path: Source path inside storage.
        :returns: File content as bytes.
        """
        pass

    @abstractmethod
    async def download_stream(self, storage_path: str) -> AsyncGenerator[bytes, None]:
        """
        Yield file content in binary chunks for memory-efficient downloads.

        :param storage_path: Source path inside storage.
        :yields: File content chunk bytes.
        """
        # Yield statement is needed in abstract generator to mark it as generator type
        if False:
            yield b""

    @abstractmethod
    async def delete(self, storage_path: str) -> None:
        """
        Physically delete the file from storage if it exists.

        :param storage_path: Path of the file to remove.
        """
        pass

    @abstractmethod
    async def exists(self, storage_path: str) -> bool:
        """
        Check if the file physically exists at the storage path.

        :param storage_path: Target path to verify.
        :returns: True if the file exists, False otherwise.
        """
        pass
