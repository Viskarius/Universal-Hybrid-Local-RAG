from dataclasses import dataclass
import os
from pathlib import Path

BYTES_IN_MB = 1024 * 1024


@dataclass(frozen=True)
class Settings:
    database_url: str
    api_key: str
    upload_dir: Path
    max_upload_bytes: int
    worker_concurrency: int
    chunk_size: int
    cors_origins: list[str]


def load_settings() -> Settings:
    max_mb = int(os.getenv("MAX_UPLOAD_MB", "100"))
    origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    cors_origins = [item.strip() for item in origins.split(",") if item.strip()]
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL", "postgresql+asyncpg://app:app@postgres:5432/app"
        ),
        api_key=os.getenv("API_KEY", "local-dev-key"),
        upload_dir=Path(os.getenv("UPLOAD_DIR", "/tmp/uploads")),
        max_upload_bytes=max_mb * BYTES_IN_MB,
        worker_concurrency=int(os.getenv("WORKER_CONCURRENCY", "2")),
        chunk_size=int(os.getenv("UPLOAD_CHUNK_SIZE", str(BYTES_IN_MB))),
        cors_origins=cors_origins,
    )
