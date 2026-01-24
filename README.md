# Uni-RAG: FastAPI + Docling + Next.js

Minimal, production-lean service for document ingestion and Markdown extraction.
FastAPI handles uploads and conversion, Postgres stores Markdown, and a Next.js
client provides a UI and server API for browsing and deleting documents.

## What this service does

1) Accepts a single file via `POST /upload`.
2) Streams it to disk in chunks and computes a SHA-256 file hash.
3) If the file hash already exists, returns the existing document id.
4) Otherwise, queues the file for conversion.
5) Docling converts the document to Markdown.
6) Markdown is normalized, hashed, and stored in Postgres.
7) If content hash already exists, the document is not duplicated.
8) Temporary file is deleted.

## Repo structure

```
app/
  main.py                     # App wiring, startup/shutdown
  core/
    config.py                 # Settings
  db/
    session.py                # Async engine + migrations
    models.py                 # SQLAlchemy models
  modules/
    extraction/
      router.py               # /upload
      service.py              # Upload + file hash + queue
      worker.py               # Docling conversion + content hash

client/
  app/                         # Next.js pages + server API
  components/                  # UI components
  lib/                         # DB connector

postgres/
  init/                        # Extensions + FTS init SQL
```

## Key features

- Async chunked uploads (FastAPI + aiofiles)
- In-process worker queue for concurrent processing
- Docling conversion with Tesseract OCR (rus+eng)
- Deduplication by file hash and by normalized content hash
- Postgres extensions: vector, pg_trgm, unaccent
- Next.js UI with modal Markdown preview and delete actions

## OCR configuration (CPU, Russian)

OCR uses Tesseract CLI with Russian + English languages:

- `TesseractCliOcrOptions(lang=["rus", "eng"])`
- `force_full_page_ocr=True` for scanned PDFs and images
- CPU threads limited to 2 for OCR stages
- Hybrid mode for PDFs: if a text layer exists, Docling uses it instead of OCR

## Deduplication logic

The `documents` table stores both file and content hashes.

- **file_hash**: SHA-256 of the uploaded file bytes
  - Checked on upload; if found, upload returns existing `id` immediately.
- **content_hash**: SHA-256 of normalized Markdown
  - Checked after conversion; duplicates are not saved.

Markdown normalization before hashing and storage:

- Normalize line endings to `\n`
- Trim trailing spaces
- Collapse 3+ blank lines to 2
- Strip leading/trailing whitespace

Important: content-hash dedup happens after the upload response, so the upload
request may still return a new `id`, but storage may be skipped if content is
already present.

## Database schema

```
documents
  id UUID PRIMARY KEY
  content TEXT NOT NULL
  file_hash TEXT UNIQUE NULL
  content_hash TEXT UNIQUE NULL
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
```

## Configuration

Environment variables (see `.env`):

- `API_KEY`: static key for FastAPI (header `X-API-Key`)
- `CORS_ORIGINS`: comma-separated origins for UI
- `DATABASE_URL`: async SQLAlchemy URL
- `POSTGRES_URL`: server-only URL for Next.js
- `UPLOAD_DIR`: temp storage for uploads
- `MAX_UPLOAD_MB`: file size limit
- `WORKER_CONCURRENCY`: number of worker tasks
- `UPLOAD_CHUNK_SIZE`: upload chunk size in bytes
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `NEXT_PUBLIC_API_URL`: FastAPI base URL for the browser
- `NEXT_PUBLIC_API_KEY`: must match `API_KEY`

## Docker services

`docker-compose.yml` runs:

- `api` (FastAPI + Docling)
- `postgres` (pgvector/pg16)
- `client` (Next.js)

Ports:

- `http://localhost:8000` (FastAPI)
- `http://localhost:3000` (Next.js UI)
- `localhost:5432` (Postgres)

## Frontend UI

- `/` landing page
- `/upload` upload form (sends `X-API-Key`)
- `/documents` list with modal Markdown preview and delete action

The UI only calls Next.js server API routes; database credentials never reach
the browser.

## API endpoints

FastAPI:

```
POST /upload
```

Headers:

```
X-API-Key: <API_KEY>
```

Next.js server API:

```
GET /api/documents
GET /api/documents/{id}
DELETE /api/documents/{id}
```

## Running locally

Build + start:

```
docker compose up --build -d
```

Upload via curl:

```
curl -H "X-API-Key: local-dev-key" \
  -F "file=@/path/to/file.pdf" \
  http://localhost:8000/upload
```

Open UI:

```
http://localhost:3000
```

## Logs and debugging

Follow logs:

```
docker compose logs -f api
```

Key log events:

- `extraction: Enqueued ...`
- `worker: Processing ...`
- `worker: Initializing Docling converters`
- `worker: Stored ...`

## Postgres extensions and FTS

On first init (see `postgres/init/001_extensions.sql`):

- `vector`
- `pg_trgm`
- `unaccent`
- `default_text_search_config = russian`

If you changed init scripts and already have volumes:

```
docker compose down -v
docker compose up --build -d
```

## Known limitations

- Content dedup happens after conversion; upload response may return an id that
  is not stored if content is duplicated.
- OCR quality depends on scan quality; Tesseract is CPU-friendly but slower.
- The in-process queue is volatile and not persisted across restarts.

## Performance, limits, and load

### Default limits

- Maximum upload size: `MAX_UPLOAD_MB` (default 100 MB)
- Upload chunk size: `UPLOAD_CHUNK_SIZE` (default 1 MB)
- Worker concurrency: `WORKER_CONCURRENCY` (default 2)
- OCR CPU threads: 2 (hard-coded in `worker.py`)

### Throughput characteristics

- Upload is async and chunked, so it scales well with multiple clients.
- CPU is the main bottleneck for OCR and PDF parsing.
- OCR speed depends heavily on document quality and resolution.
- First conversion is slower due to Docling model warm-up.

### Queue behavior

- The queue is in-memory (`asyncio.Queue`), so it grows until workers catch up.
- If workers are slower than uploads, files accumulate in `UPLOAD_DIR`.
- On restart, queued jobs are lost but uploaded files remain on disk.

### Memory usage

- Docling loads OCR models in-process and keeps them cached.
- Two worker tasks share the same converters, but each conversion holds its
  own document in memory while processing.
- Large PDFs with many pages can spike memory usage.

### Disk usage

- Each upload is stored in `UPLOAD_DIR` until conversion completes.
- If conversion fails, the file is still removed in the `finally` block.
- Ensure enough disk for concurrent uploads + ongoing conversions.

### Database load

- Inserts are single-row writes with unique indexes on `file_hash` and
  `content_hash`.
- Dedup queries are single-column lookups, which are fast with indexes.
- Large Markdown content can increase storage and I/O pressure.

### Practical tuning

- Increase `WORKER_CONCURRENCY` only if CPU has headroom.
- Increase `UPLOAD_CHUNK_SIZE` for faster disk writes on large files.
- Keep `MAX_UPLOAD_MB` reasonable for your memory and disk constraints.
- Consider moving to Redis/RabbitMQ if you need durable queues.

### Recommended baseline for CPU-only

- 2-4 CPU cores, 4-8 GB RAM for light loads.
- 8+ CPU cores, 16+ GB RAM for heavy OCR batches.

### Load testing notes

- Use real scanned PDFs for OCR tests.
- Measure time-to-Markdown and database insert latency.
- Monitor `/tmp/uploads` growth during stress tests.
