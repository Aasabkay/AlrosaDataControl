import os
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, UploadFile, HTTPException
from fastapi.params import Form
from starlette import status

from app.api.dependencies import sessionDepends
from app.api.schemas import ImportOutputSchema, GetImportsBatchSchema, GetImportsLogsSchema, GetImportsIssuesSchema
from app.config import UPLOAD_DIR
from app.database.repositories.imports import list_sources, create_batch, save_import, get_batch, get_import_log, \
    get_batch_issues, list_batches
from app.database.repositories.rules import load_rules_from_db
from app.pipeline.parser import parse_file

imports_router = APIRouter(prefix="/imports",
    tags=["Загрузка, взаимодействие с загруженными файлами"])

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
MAX_SIZE = 100 * 1024 * 1024

@imports_router.post("/", summary="Загрузить файл", status_code=status.HTTP_201_CREATED)
async def import_file(session: sessionDepends , file: UploadFile, source_id: int = Form(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Недопустимое расширение {ext!r}. Разрешены: {sorted(ALLOWED_EXTENSIONS)}"
        )

    sources = await list_sources(session)
    source_ids = [s.id for s in sources]

    if source_id not in source_ids:
        raise HTTPException(status_code=404, detail=f"Источника с ID: {source_id} не существует")

    original_name = file.filename or "unnamed"
    stored_name = f"{uuid.uuid4().hex}{ext}"

    batch = await create_batch(session, source_id, original_name, stored_name)

    upload_dir = Path(UPLOAD_DIR or "uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / stored_name

    size = 0
    async with aiofiles.open(path, "wb") as f:
        while chunk := await file.read(1024*1024):
            size += len(chunk)

            if size > MAX_SIZE:
                await f.close()
                os.remove(path)
                raise HTTPException(status_code=413, detail="Файл больше 100 МБ")

            await f.write(chunk)

    rules = await load_rules_from_db(session)
    result = parse_file(path, source_id, batch.id, rules)

    counts = await save_import(session, batch.id, path, result)
    await session.commit()

    return ImportOutputSchema(batch_id=batch.id,
                              filename=original_name,
                              rows_total=counts["rows_total"],
                              records_accepted=counts["records_accepted"],
                              issues_count=counts["issues_count"])

def _batch_schema(batch) -> GetImportsBatchSchema:
    accepted = sum(1 for row in batch.raw_rows if row.status == "accepted")

    return GetImportsBatchSchema(id=batch.id,
                                 source_id=batch.source_id,
                                 filename=batch.filename,
                                 file_uuid=batch.file_uuid,
                                 uploaded_at=batch.uploaded_at,
                                 rows_total=len(batch.raw_rows),
                                 accepted=accepted,
                                 rejected=len(batch.raw_rows) - accepted)


@imports_router.get("/", summary="Список загрузок (свежие первыми)", status_code=status.HTTP_200_OK)
async def get_import_batches(session: sessionDepends) -> list[GetImportsBatchSchema]:
    batches = await list_batches(session)

    return [_batch_schema(batch) for batch in batches]

@imports_router.get("/{batch_id}", summary="Сводка по загрузке", status_code=status.HTTP_200_OK)
async def get_import_batch(session: sessionDepends, batch_id: int) -> GetImportsBatchSchema:
    batch = await get_batch(session, batch_id)

    if batch is None:
        raise HTTPException(status_code=404, detail=f"Файл с batch_id: {batch_id} не найден")

    return _batch_schema(batch)

@imports_router.get("/{batch_id}/log", summary="Журнал загрузки", status_code=status.HTTP_200_OK)
async def get_batch_log(session: sessionDepends, batch_id: int) -> list[GetImportsLogsSchema]:
    log = await get_import_log(session, batch_id)

    results = []
    for row in log:
        data = GetImportsLogsSchema(row_number=row.row_number,
                             cells=row.cells,
                             status=row.status,
                             reject_reason=row.reject_reason if row.reject_reason else "")
        results.append(data)

    return results

@imports_router.get("/{batch_id}/issues", summary="Журнал ошибок", status_code=status.HTTP_200_OK)
async def get_import_batch_issues(session: sessionDepends, batch_id: int) -> list[GetImportsIssuesSchema]:
    issues = await get_batch_issues(session, batch_id)

    results = []
    for issue in issues:
        data = GetImportsIssuesSchema(code=issue.code,
                                      severity=issue.severity,
                                      message=issue.message,
                                      refs=issue.refs)
        results.append(data)

    return results
