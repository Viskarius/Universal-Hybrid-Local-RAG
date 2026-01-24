import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path
import uuid

import pypdfium2 as pdfium
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions,
    TableStructureOptions,
    TesseractCliOcrOptions,
)
from docling.document_converter import (
    DocumentConverter,
    ImageFormatOption,
    PdfFormatOption,
    WordFormatOption,
)
from docling.pipeline.simple_pipeline import SimplePipeline
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import Document

CONVERTER_CACHE: tuple[DocumentConverter, DocumentConverter] | None = None


@dataclass(frozen=True)
class UploadJob:
    doc_id: uuid.UUID
    path: Path
    file_hash: str


def start_workers(
    queue: asyncio.Queue["UploadJob | None"],
    session_maker: async_sessionmaker[AsyncSession],
    worker_count: int,
) -> list[asyncio.Task]:
    tasks = []
    for idx in range(worker_count):
        task = asyncio.create_task(
            worker_loop(f"worker-{idx + 1}", queue, session_maker)
        )
        tasks.append(task)
    return tasks


async def worker_loop(
    name: str,
    queue: asyncio.Queue["UploadJob | None"],
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    logger = logging.getLogger("worker")
    logger.info("%s ready", name)
    while True:
        job = await queue.get()
        if job is None:
            queue.task_done()
            logger.info("%s stopped", name)
            break

        try:
            logger.info("Processing %s (%s)", job.doc_id, job.path.name)
            markdown = await asyncio.to_thread(
                convert_to_markdown, job.path
            )
            normalized = normalize_markdown(markdown)
            content_hash = hash_text(normalized)
            async with session_maker() as session:
                existing_id = await fetch_existing_content_id(session, content_hash)
                if existing_id:
                    logger.info(
                        "Duplicate content detected for %s (existing %s)",
                        job.path.name,
                        existing_id,
                    )
                    continue
                session.add(
                    Document(
                        id=job.doc_id,
                        content=normalized,
                        file_hash=job.file_hash,
                        content_hash=content_hash,
                    )
                )
                try:
                    await session.commit()
                    logger.info("Stored %s", job.doc_id)
                except IntegrityError:
                    await session.rollback()
                    logger.info("Integrity conflict for %s", job.doc_id)
        except Exception:
            logger.exception("Failed to process %s", job.path)
        finally:
            try:
                job.path.unlink(missing_ok=True)
            except FileNotFoundError:
                pass
            queue.task_done()


def build_pipeline_options(
    *,
    force_full_page_ocr: bool,
    force_backend_text: bool,
) -> PdfPipelineOptions:
    accelerator_options = AcceleratorOptions(
        num_threads=2,
        device=AcceleratorDevice.CPU,
    )
    ocr_options = TesseractCliOcrOptions(
        force_full_page_ocr=force_full_page_ocr,
        lang=["rus", "eng"],
    )

    pipeline_options = PdfPipelineOptions()
    pipeline_options.accelerator_options = accelerator_options
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.force_backend_text = force_backend_text
    pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=True
    )
    pipeline_options.ocr_options = ocr_options
    return pipeline_options


def build_converter(
    *,
    force_full_page_ocr: bool,
    force_backend_text: bool,
) -> DocumentConverter:
    pipeline_options = build_pipeline_options(
        force_full_page_ocr=force_full_page_ocr,
        force_backend_text=force_backend_text,
    )
    return DocumentConverter(
        allowed_formats=[
            InputFormat.PDF,
            InputFormat.IMAGE,
            InputFormat.DOCX,
            InputFormat.PPTX,
            InputFormat.HTML,
            InputFormat.ASCIIDOC,
            InputFormat.MD,
        ],
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=StandardPdfPipeline,
                backend=PyPdfiumDocumentBackend,
                pipeline_options=pipeline_options,
            ),
            InputFormat.IMAGE: ImageFormatOption(
                pipeline_options=pipeline_options,
            ),
            InputFormat.DOCX: WordFormatOption(
                pipeline_cls=SimplePipeline,
            ),
        },
    )


def convert_to_markdown(path: Path) -> str:
    converter_full, converter_hybrid = get_converters()
    converter = select_converter(path, converter_full, converter_hybrid)
    doc = converter.convert(str(path)).document
    return doc.export_to_markdown()


def get_converters() -> tuple[DocumentConverter, DocumentConverter]:
    global CONVERTER_CACHE
    if CONVERTER_CACHE is None:
        logger = logging.getLogger("worker")
        logger.info("Initializing Docling converters")
        full = build_converter(force_full_page_ocr=True, force_backend_text=False)
        hybrid = build_converter(force_full_page_ocr=False, force_backend_text=True)
        CONVERTER_CACHE = (full, hybrid)
    return CONVERTER_CACHE


def select_converter(
    path: Path,
    converter_full: DocumentConverter,
    converter_hybrid: DocumentConverter,
) -> DocumentConverter:
    logger = logging.getLogger("worker")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        has_text = pdf_has_text_layer(path)
        logger.info("PDF text layer detected: %s", "yes" if has_text else "no")
        if has_text:
            return converter_hybrid
        return converter_full

    if suffix in IMAGE_EXTENSIONS:
        logger.info("Image OCR forced full-page")
        return converter_full

    return converter_hybrid


IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".tif",
    ".bmp",
    ".webp",
}


def pdf_has_text_layer(path: Path, max_pages: int = 2) -> bool:
    try:
        doc = pdfium.PdfDocument(str(path))
    except Exception:
        return False

    try:
        page_count = len(doc)
        for index in range(min(page_count, max_pages)):
            page = doc.get_page(index)
            text_page = None
            try:
                text_page = page.get_textpage()
                count = None
                if hasattr(text_page, "count_chars"):
                    count = text_page.count_chars()
                else:
                    text = text_page.get_text_range()
                    count = len(text.strip())
                if count:
                    return True
            finally:
                if text_page is not None and hasattr(text_page, "close"):
                    text_page.close()
                if hasattr(page, "close"):
                    page.close()
    finally:
        if hasattr(doc, "close"):
            doc.close()
    return False


async def fetch_existing_content_id(
    session: AsyncSession,
    content_hash: str,
) -> uuid.UUID | None:
    result = await session.execute(
        select(Document.id).where(Document.content_hash == content_hash)
    )
    return result.scalar_one_or_none()


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_markdown(markdown: str) -> str:
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
