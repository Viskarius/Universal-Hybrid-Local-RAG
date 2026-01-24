from fastapi import APIRouter, File, Request, UploadFile

from app.modules.extraction.service import enqueue_upload

router = APIRouter()


@router.post("/upload", status_code=202)
async def upload_file(request: Request, file: UploadFile = File(...)) -> dict:
    doc_id = await enqueue_upload(
        file,
        request.app.state.settings,
        request.app.state.extraction_queue,
        request.app.state.session_maker,
    )
    return {"id": str(doc_id)}
