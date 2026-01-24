import asyncio
import hashlib
import logging
from pathlib import Path
import uuid

import aiofiles
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db.models import Document
from app.modules.extraction.worker import UploadJob

ALLOWED_EXTENSIONS = {
    "pdf",
    "docx",
    "pptx",
    "md",
    "markdown",
    "html",
    "htm",
    "adoc",
    "asciidoc",
    "png",
    "jpg",
    "jpeg",
    "tiff",
    "tif",
    "bmp",
    "webp",
}


async def enqueue_upload(
    file: UploadFile,
    settings: Settings,
    queue: asyncio.Queue["UploadJob | None"],
    session_maker: async_sessionmaker[AsyncSession],
) -> uuid.UUID:
    logger = logging.getLogger("extraction")
    filename = file.filename or ""
    extension = Path(filename).suffix.lower().lstrip(".")
    if not extension or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    doc_id = uuid.uuid4()
    target_path = settings.upload_dir / f"{doc_id}.{extension}"
    size = 0
    hasher = hashlib.sha256()

    try:
        async with aiofiles.open(target_path, "wb") as out_file:
            while True:
                chunk = await file.read(settings.chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(status_code=413, detail="File too large")
                await out_file.write(chunk)
    except HTTPException:
        target_path.unlink(missing_ok=True)
        raise
    except Exception:
        target_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Failed to save file")
    finally:
        await file.close()

    file_hash = hasher.hexdigest()
    async with session_maker() as session:
        existing_id = await fetch_existing_id(session, file_hash)
        if existing_id:
            logger.info("Duplicate file hash detected for %s", filename)
            target_path.unlink(missing_ok=True)
            return existing_id

    logger.info("Enqueued %s as %s", filename, doc_id)
    await queue.put(UploadJob(doc_id=doc_id, path=target_path, file_hash=file_hash))
    return doc_id


async def fetch_existing_id(
    session: AsyncSession,
    file_hash: str,
) -> uuid.UUID | None:
    result = await session.execute(
        select(Document.id).where(Document.file_hash == file_hash)
    )
    return result.scalar_one_or_none()
