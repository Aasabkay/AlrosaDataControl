"""Эндпоинты сверки: прогон по загрузкам, отчёт и список ошибок."""

import io

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from starlette import status

from app.api.dependencies import sessionDepends
from app.api.schemas import (ReconciliationInputSchema,
                             ReconciliationOutputSchema)
from app.database.models import ReconciliationRun
from app.database.repositories.reconciliations import (create_run, get_run,
                                                       group_from_db,
                                                       issue_from_db,
                                                       load_batches,
                                                       load_run_assets,
                                                       load_run_issues,
                                                       record_from_db,
                                                       save_run)
from app.database.repositories.rules import load_rules_from_db
from app.pipeline.classifier import classify_issues
from app.pipeline.detectors import run_detectors
from app.pipeline.matcher import match_records
from app.pipeline.report import Report, ReportMeta, build_report, write_report_xlsx
from app.pipeline.runner import PipelineResult

reconciliations_router = APIRouter(prefix="/reconciliations", tags=["Сверка активов"])


@reconciliations_router.post("/", status_code=status.HTTP_201_CREATED,
                             response_model=ReconciliationOutputSchema,
                             summary="Запустить сверку по загрузкам")
async def run_reconciliation(session: sessionDepends,
                             payload: ReconciliationInputSchema):
    # Порядок сохраняем, дубли убираем: сверта по одному и тому же батчу дважды не имеет смысла.
    batch_ids = list(dict.fromkeys(payload.batch_ids))
    batches = await load_batches(session, batch_ids)

    found_ids = {batch.id for batch in batches}
    missing = [batch_id for batch_id in batch_ids if batch_id not in found_ids]
    if missing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Загрузки не найдены: {missing}")

    rules = await load_rules_from_db(session)
    records = [
        record_from_db(record, batch.source.id)
        for batch in batches
        for record in batch.records
    ]
    groups = match_records(records)
    issues = run_detectors(groups, expected_source_ids={batch.source.id for batch in batches})

    record_map = {
        (record.batch_id, record.row_number): record
        for batch in batches
        for record in batch.records
    }

    run = await create_run(session)
    counts = await save_run(session, run, groups, issues, record_map)
    await session.commit()

    return ReconciliationOutputSchema(run_id=run.id, status=run.status, **counts)


async def _load_report(session, run_id: int) -> Report:
    """Общая загрузка прогона: группы и ошибки из БД -> отчёт."""
    run = await get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Сверка с run_id {run_id} не найдена")

    assets = await load_run_assets(session, run_id)
    issues_rows = await load_run_issues(session, run_id)

    source_by_batch = {
        record.batch_id: record.batch.source_id
        for asset in assets
        for record in asset.records
    }
    # У загрузок без принятых записей записей в asset не будет, но ошибки их строк
    # всё равно должны попасть в отчёт — добираем источники по ссылкам ошибок.
    missing_batches = {
        ref.batch_id
        for row in issues_rows
        for ref in row.refs
    } - set(source_by_batch)
    if missing_batches:
        for batch in await load_batches(session, list(missing_batches)):
            source_by_batch[batch.id] = batch.source.id

    groups = [group_from_db(asset) for asset in assets]
    records = [record for group in groups for record in group.records]
    issues = [issue_from_db(row, source_by_batch) for row in issues_rows]

    result = PipelineResult(
        records=records,
        groups=groups,
        issues=classify_issues(issues),
    )
    return build_report(result, ReportMeta(generated_at=run.started_at.date()))


@reconciliations_router.get("/", status_code=status.HTTP_200_OK,
                            summary="Список прогонов сверки (свежие первыми)")
async def list_reconciliations(session: sessionDepends):
    query = select(ReconciliationRun).order_by(ReconciliationRun.id.desc())
    result = await session.execute(query)
    runs = result.scalars().all()
    return [
        {"run_id": run.id, "status": run.status, "started_at": run.started_at}
        for run in runs
    ]


@reconciliations_router.get("/{run_id}/assets/{asset_key}",
                            status_code=status.HTTP_200_OK,
                            summary="Карточка актива: значения по источникам и diff")
async def get_reconciliation_asset(session: sessionDepends,
                                   run_id: int, asset_key: str):
    report = await _load_report(session, run_id)
    asset = next(
        (row for row in report.assets if row.asset_key == asset_key),
        None,
    )
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Актив {asset_key!r} в прогоне {run_id} не найден")

    assets = await load_run_assets(session, run_id)
    ref_to_asset = {
        (record.batch_id, record.row_number): db_asset.asset_key
        for db_asset in assets
        for record in db_asset.records
    }
    issues = [
        issue for issue in report.issues
        if issue.asset_key == asset_key
        or asset_key in {
            ref_to_asset.get((ref.batch_id, ref.row_number))
            for ref in issue.refs
        }
    ]
    return {"asset": asset, "issues": issues}


@reconciliations_router.get("/{run_id}", status_code=status.HTTP_200_OK,
                            response_model=Report,
                            summary="Отчёт по сверке (JSON, как в tools/openapi.json)")
async def get_reconciliation_report(session: sessionDepends, run_id: int):
    return await _load_report(session, run_id)


@reconciliations_router.get("/{run_id}/report", status_code=status.HTTP_200_OK,
                            summary="Отчёт в выбранном формате: json или xlsx")
async def download_reconciliation_report(session: sessionDepends, run_id: int,
                                         format: str = "json"):
    report = await _load_report(session, run_id)

    if format != "xlsx":
        return report

    buffer = io.BytesIO()
    write_report_xlsx(buffer, report)
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="reconciliation_{run_id}.xlsx"'},
    )


@reconciliations_router.get("/{run_id}/assets", status_code=status.HTTP_200_OK,
                            summary="Таблица активов сверки")
async def list_reconciliation_assets(session: sessionDepends, run_id: int):
    report = await _load_report(session, run_id)
    return report.assets


@reconciliations_router.get("/{run_id}/issues", status_code=status.HTTP_200_OK,
                            summary="Ошибки сверки с фильтрами")
async def list_reconciliation_issues(session: sessionDepends, run_id: int,
                                     category: str | None = None,
                                     severity: str | None = None,
                                     code: str | None = None,
                                     field: str | None = None,
                                     asset_key: str | None = None):
    report = await _load_report(session, run_id)
    assets = await load_run_assets(session, run_id)
    ref_to_asset = {
        (record.batch_id, record.row_number): asset.asset_key
        for asset in assets
        for record in asset.records
    }

    def matches(issue) -> bool:
        if category and issue.category.value != category:
            return False
        if severity and issue.severity.value != severity:
            return False
        if code and issue.code.value != code:
            return False
        if field and issue.field != field:
            return False
        if asset_key:
            issue_assets = {
                ref_to_asset.get((ref.batch_id, ref.row_number))
                for ref in issue.refs
            }
            if asset_key not in issue_assets:
                return False
        return True

    return [issue for issue in report.issues if matches(issue)]
