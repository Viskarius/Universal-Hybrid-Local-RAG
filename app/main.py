import asyncio
import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import load_settings
from app.db.session import create_engine, create_session_maker, init_db
from app.modules.extraction import router as extraction_router
from app.modules.extraction.worker import UploadJob, start_workers

settings = load_settings()


def require_api_key(request: Request) -> None:
    if request.method == "OPTIONS":
        return
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


app = FastAPI(dependencies=[Depends(require_api_key)])
app.include_router(extraction_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    engine = create_engine(settings)
    session_maker = create_session_maker(engine)
    await init_db(engine)

    queue: asyncio.Queue[UploadJob | None] = asyncio.Queue()
    worker_tasks = start_workers(queue, session_maker, settings.worker_concurrency)

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_maker = session_maker
    app.state.extraction_queue = queue
    app.state.extraction_workers = worker_tasks


@app.on_event("shutdown")
async def shutdown() -> None:
    for _ in app.state.extraction_workers:
        await app.state.extraction_queue.put(None)
    await asyncio.gather(*app.state.extraction_workers, return_exceptions=True)
    await app.state.engine.dispose()
