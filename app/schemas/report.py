from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class ReportType(str, Enum):
    DAILY      = "daily"
    WEEKLY     = "weekly"
    MONTHLY    = "monthly"
    QUARTERLY  = "quarterly"
    ANNUAL     = "annual"
    CUSTOM     = "custom"


class ReportStatus(str, Enum):
    PENDING    = "pending"
    GENERATING = "generating"
    READY      = "ready"
    FAILED     = "failed"


class ReportGenerateRequest(BaseModel):
    report_type: ReportType
    date_from: date
    date_to: date
    biomarker_types: Optional[List[str]] = None   # None = all biomarkers
    patient_user_id: Optional[str] = None         # providers pass this; patients omit


class BiomarkerStat(BaseModel):
    biomarker_type: str
    unit: str
    avg: Optional[float]
    min: Optional[float]
    max: Optional[float]
    latest: Optional[float]
    readings_count: int
    days_in_normal: int
    days_total: int
    trend: str          # "improving" | "declining" | "stable" | "insufficient_data"
    status: str         # "normal" | "borderline" | "abnormal" | "no_data"


class ReportSummary(BaseModel):
    avg_health_score: Optional[float]
    best_score: Optional[float]
    worst_score: Optional[float]
    score_trend: str
    total_readings: int
    biomarker_stats: List[BiomarkerStat]


class ReportResponse(BaseModel):
    id: str
    patient_user_id: str
    report_type: str
    date_from: date
    date_to: date
    biomarker_types: Optional[List[str]]
    status: str
    pdf_url: Optional[str]
    csv_url: Optional[str]
    summary: Optional[Dict[str, Any]]
    generated_at: Optional[datetime]
    created_at: datetime


class ReportListResponse(BaseModel):
    reports: List[ReportResponse]
    total: int
