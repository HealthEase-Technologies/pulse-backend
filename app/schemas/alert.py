from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class AlertType(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    TRIGGERED = "triggered"
    NOTIFIED = "notified"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class AlertHistoryResponse(BaseModel):
    """Single alert history record"""
    id: str
    patient_user_id: str
    biomarker_id: Optional[str] = None
    biomarker_type: str
    value: float
    unit: str
    alert_type: str
    alert_direction: Optional[str] = None
    threshold_source: str
    threshold_value: float
    status: str
    notification_channels: List[str] = []
    notification_attempts: int = 0
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime


class AlertHistoryListResponse(BaseModel):
    """Paginated alert history list"""
    total_count: int
    alerts: List[AlertHistoryResponse]


class UnacknowledgedCountResponse(BaseModel):
    """Count of unacknowledged alerts"""
    count: int


class AlertCheckResult(BaseModel):
    """Result of checking a biomarker value against thresholds"""
    alert_triggered: bool
    alert_type: Optional[str] = None
    alert_direction: Optional[str] = None
    threshold_source: Optional[str] = None
    threshold_value: Optional[float] = None
    alert_id: Optional[str] = None
    cooldown_active: bool = False
