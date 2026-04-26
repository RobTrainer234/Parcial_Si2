from __future__ import annotations

import mimetypes
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings


IMAGE_MIME_PREFIX = "image/"
AUDIO_MIME_PREFIX = "audio/"


class StorageError(Exception):
    pass


@dataclass(frozen=True)
class StoredMedia:
    locator: str
    mime_type: str | None
    size_bytes: int
    absolute_path: Path


@dataclass(frozen=True)
class ResolvedMedia:
    locator: str
    mime_type: str | None
    size_bytes: int
    absolute_path: Path
    content_bytes: bytes


class LocalIncidentStorage:
    def __init__(self, media_root: Path) -> None:
        self._media_root = media_root.resolve()

    def _save_file(
        self,
        *,
        relative_dir: Path,
        upload: UploadFile,
    ) -> StoredMedia:
        content_type = upload.content_type or "application/octet-stream"
        destination_dir = (self._media_root / relative_dir).resolve()
        destination_dir.mkdir(parents=True, exist_ok=True)

        extension = Path(upload.filename or "").suffix.lower()
        if not extension:
            guessed_extension = mimetypes.guess_extension(content_type)
            extension = guessed_extension or ""

        filename = f"{uuid4().hex}{extension}"
        absolute_path = destination_dir / filename
        relative_path = absolute_path.relative_to(self._media_root).as_posix()

        try:
            upload.file.seek(0)
            with absolute_path.open("wb") as destination:
                shutil.copyfileobj(upload.file, destination)
        except OSError as exc:
            raise StorageError("File could not be stored.") from exc
        finally:
            upload.file.seek(0)

        try:
            size_bytes = absolute_path.stat().st_size
        except OSError as exc:
            raise StorageError("Stored file could not be inspected.") from exc

        return StoredMedia(
            locator=f"local://{relative_path}",
            mime_type=content_type,
            size_bytes=size_bytes,
            absolute_path=absolute_path,
        )

    def save_incident_file(
        self,
        *,
        incident_id: int,
        folder: str,
        upload: UploadFile,
    ) -> StoredMedia:
        return self._save_file(
            relative_dir=Path("incidentes") / str(incident_id) / folder,
            upload=upload,
        )

    def save_service_file(
        self,
        *,
        service_id: int,
        folder: str,
        upload: UploadFile,
    ) -> StoredMedia:
        return self._save_file(
            relative_dir=Path("servicios") / str(service_id) / folder,
            upload=upload,
        )

    def save_workshop_file(
        self,
        *,
        workshop_id: int,
        folder: str,
        upload: UploadFile,
    ) -> StoredMedia:
        return self._save_file(
            relative_dir=Path("talleres") / str(workshop_id) / folder,
            upload=upload,
        )

    def resolve_locator(self, locator: str) -> Path:
        if not locator.startswith("local://"):
            raise StorageError("Unsupported storage locator.")

        relative_path = locator.removeprefix("local://").lstrip("/")
        absolute_path = (self._media_root / relative_path).resolve()
        try:
            absolute_path.relative_to(self._media_root)
        except ValueError as exc:
            raise StorageError("Storage locator points outside the media root.") from exc
        return absolute_path

    def read_locator(
        self,
        *,
        locator: str,
        mime_type: str | None = None,
    ) -> ResolvedMedia:
        absolute_path = self.resolve_locator(locator)
        if not absolute_path.exists() or not absolute_path.is_file():
            raise StorageError("Stored file was not found.")

        try:
            content_bytes = absolute_path.read_bytes()
            size_bytes = absolute_path.stat().st_size
        except OSError as exc:
            raise StorageError("Stored file could not be read.") from exc

        detected_mime_type = mime_type or mimetypes.guess_type(absolute_path.name)[0]
        return ResolvedMedia(
            locator=locator,
            mime_type=detected_mime_type,
            size_bytes=size_bytes,
            absolute_path=absolute_path,
            content_bytes=content_bytes,
        )

    def delete_many(self, stored_media: list[StoredMedia]) -> None:
        for item in stored_media:
            try:
                if item.absolute_path.exists():
                    item.absolute_path.unlink()
            except OSError:
                continue


def get_triage_storage() -> LocalIncidentStorage:
    settings = get_settings()
    if settings.storage_backend.lower() != "local":
        raise RuntimeError("Only local storage is currently supported.")
    return LocalIncidentStorage(settings.local_media_root)
