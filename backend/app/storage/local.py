"""
Local filesystem storage engine.
"""

import asyncio
import os
from collections.abc import AsyncGenerator
from pathlib import Path

from app.core.config import settings
from app.exceptions.custom import ValidationError
from app.storage.base import BaseStorage


class LocalStorage(BaseStorage):
    """
    Local filesystem implementation of ``BaseStorage``.

    Protects against path traversal attacks by resolving and sandboxing all targets.
    Executes standard I/O in worker threads to prevent event loop CPU blocks.
    """

    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = Path(base_dir or settings.upload_dir).resolve()

    def _resolve_and_verify_path(self, relative_path: str) -> Path:
        """
        Verify relative path resides strictly inside the base uploads directory.

        :raises ValidationError: Path traversal attempt or invalid destination.
        """
        try:
            # Join and resolve path
            target = self.base_dir.joinpath(relative_path).resolve()
            # Ensure target is relative to the root base directory
            if not target.is_relative_to(self.base_dir):
                raise ValidationError("Path traversal attack detected: Access denied.")
            return target
        except Exception as e:
            raise ValidationError(f"Invalid storage path: {str(e)}")

    async def upload(self, file_content: bytes, storage_path: str) -> None:
        target = self._resolve_and_verify_path(storage_path)

        def _write():
            os.makedirs(target.parent, exist_ok=True)
            with open(target, "wb") as f:
                f.write(file_content)

        await asyncio.to_thread(_write)

    async def download(self, storage_path: str) -> bytes:
        target = self._resolve_and_verify_path(storage_path)

        if not target.exists() or not target.is_file():
            raise ValidationError("Target file does not exist in local storage.")

        def _read() -> bytes:
            with open(target, "rb") as f:
                return f.read()

        return await asyncio.to_thread(_read)

    async def download_stream(self, storage_path: str) -> AsyncGenerator[bytes, None]:
        target = self._resolve_and_verify_path(storage_path)

        if not target.exists() or not target.is_file():
            raise ValidationError("Target file does not exist in local storage.")

        # Read in 64KB chunks to optimize memory footprint for large files
        chunk_size = 64 * 1024

        def _read_chunk(file_handle) -> bytes:
            return file_handle.read(chunk_size)

        # Open file in thread pool or use standard file generator
        # Note: Generator needs to yield chunks cleanly
        with open(target, "rb") as f:
            while True:
                chunk = await asyncio.to_thread(_read_chunk, f)
                if not chunk:
                    break
                yield chunk

    async def delete(self, storage_path: str) -> None:
        target = self._resolve_and_verify_path(storage_path)

        def _remove():
            if target.exists() and target.is_file():
                os.remove(target)
                # Cleanup empty parent directories recursively up to root base_dir
                parent = target.parent
                while parent != self.base_dir:
                    try:
                        if not os.listdir(parent):
                            os.rmdir(parent)
                        else:
                            break
                    except Exception:
                        break
                    parent = parent.parent

        await asyncio.to_thread(_remove)

    async def exists(self, storage_path: str) -> bool:
        target = self._resolve_and_verify_path(storage_path)
        return await asyncio.to_thread(target.exists)
