from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
from datetime import date
import io

from app.schemas.report import (
    ReportGenerateRequest, ReportResponse, ReportListResponse
)
from app.services.report_service import ReportService
from app.utils.s3 import S3Service
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/reports", tags=["Health Reports"])


def _patient_id_for_request(body_patient_id: Optional[str], current_user: dict) -> str:
    """
    If the current user is a provider and passes patient_user_id, use that.
    Otherwise use the current user's own ID.
    """
    db_user = current_user["db_user"]
    role    = db_user.get("role", "patient")
    if role == "provider" and body_patient_id:
        return body_patient_id
    return db_user["id"]


# ── Generate report ─────────────────────────────────────────────────────────
@router.post("", response_model=ReportResponse, status_code=202)
async def generate_report(
    body: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Kick off async report generation. Returns immediately with status=pending.
    Poll GET /reports/{id} or GET /reports to check when status=ready.
    """
    patient_user_id = _patient_id_for_request(body.patient_user_id, current_user)

    report = await ReportService.create_report(
        patient_user_id=patient_user_id,
        report_type=body.report_type,
        date_from=body.date_from,
        date_to=body.date_to,
        biomarker_types=body.biomarker_types,
    )

    background_tasks.add_task(
        ReportService.generate_report,
        report_id=report["id"],
        patient_user_id=patient_user_id,
    )

    return report


# ── List reports ────────────────────────────────────────────────────────────
@router.get("", response_model=ReportListResponse)
async def list_reports(
    patient_user_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """Get all reports for a patient (providers may pass ?patient_user_id=...)."""
    pid    = _patient_id_for_request(patient_user_id, current_user)
    items  = await ReportService.list_reports(pid, limit=limit)
    return {"reports": items, "total": len(items)}


# ── Preview (in-app recharts data) — MUST be before /{report_id} ────────────
@router.get("/preview/data")
async def preview_data(
    date_from: date = Query(...),
    date_to:   date = Query(...),
    biomarker_types: Optional[str] = Query(None, description="Comma-separated list"),
    patient_user_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Return JSON time-series + stats for in-app recharts display.
    No PDF/CSV generation — instant response.
    """
    pid = _patient_id_for_request(patient_user_id, current_user)
    bt_list: Optional[List[str]] = None
    if biomarker_types:
        bt_list = [b.strip() for b in biomarker_types.split(",") if b.strip()]

    return await ReportService.get_preview_data(
        patient_user_id=pid,
        date_from=date_from,
        date_to=date_to,
        biomarker_types=bt_list,
    )


# ── Get single report ───────────────────────────────────────────────────────
@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    patient_user_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    pid    = _patient_id_for_request(patient_user_id, current_user)
    report = await ReportService.get_report(report_id, pid)
    if not report:
        raise HTTPException(404, "Report not found")
    return report


# ── Download PDF ────────────────────────────────────────────────────────────
@router.get("/{report_id}/download/pdf")
async def download_pdf(
    report_id: str,
    patient_user_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    pid    = _patient_id_for_request(patient_user_id, current_user)
    report = await ReportService.get_report(report_id, pid)
    if not report:
        raise HTTPException(404, "Report not found")
    if report["status"] != "ready" or not report.get("pdf_url"):
        raise HTTPException(400, "PDF not ready yet")

    s3  = S3Service()
    url = s3.generate_presigned_url(report["pdf_url"])
    return {"url": url}


# ── Download CSV ────────────────────────────────────────────────────────────
@router.get("/{report_id}/download/csv")
async def download_csv(
    report_id: str,
    patient_user_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    pid    = _patient_id_for_request(patient_user_id, current_user)
    report = await ReportService.get_report(report_id, pid)
    if not report:
        raise HTTPException(404, "Report not found")
    if report["status"] != "ready" or not report.get("csv_url"):
        raise HTTPException(400, "CSV not ready yet")

    s3  = S3Service()
    url = s3.generate_presigned_url(report["csv_url"])
    return {"url": url}
