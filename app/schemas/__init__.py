"""
Pydantic schemas for request/response validation
"""

# User schemas
from app.schemas.user import (
    UserRole,
    UserRegister,
    UserResponse,
    UserCreate
)

# Provider schemas
from app.schemas.provider import (
    LicenseUploadResponse,
    ProviderProfileResponse
)

# Patient schemas
from app.schemas.patient import (
    EmergencyContact,
    HealthGoal,
    PatientProfileResponse,
    PatientOnboardingData,
    PatientOnboardingResponse,
    PatientProfileUpdate,
    OnboardingStatusResponse
)

# Goal schemas
from app.schemas.goal import (
    GoalStatus,
    GoalFrequency,
    GoalCompletionCreate,
    GoalCompletionResponse,
    MarkGoalRequest,
    UnmarkGoalRequest,
    GoalStatsResponse,
    InitializeDailyGoalsResponse,
    MarkMissedGoalsResponse
)

# Admin schemas
from app.schemas.admin import (
    LicenseStatus,
    AdminAction,
    AdminAuditLogResponse,
    ProviderListResponse,
    UpdateLicenseStatusRequest,
    UpdateLicenseStatusResponse,
    ProviderUpdateRequest,
    UserWithRoleResponse,
    LicenseUrlResponse,
    DeleteProviderResponse
)

# Patient-Provider Connection schemas
from app.schemas.connection import (
    ConnectionStatus,
    PatientProviderConnectionCreate,
    PatientProviderConnectionResponse,
    PatientProviderConnectionWithDetails,
    UpdateConnectionStatusRequest,
    ConnectionStatusResponse,
    DisconnectProviderResponse
)

# Device schemas
from app.schemas.device import (
    DeviceType,
    DeviceStatus,
    DeviceTypeInfo,
    ConnectDeviceRequest,
    DeviceResponse,
    DeviceWithTypeInfo,
    DisconnectDeviceResponse,
    SimulateDeviceDataRequest,
    SimulateDeviceDataResponse
)

# Biomarker schemas
from app.schemas.biomarker import (
    BiomarkerType,
    BiomarkerSource,
    BiomarkerRangeResponse,
    InsertBiomarkerRequest,
    BiomarkerResponse,
    LatestBiomarkerReading,
    BiomarkerDashboardSummary
)

__all__ = [
    # User
    "UserRole",
    "UserRegister",
    "UserResponse",
    "UserCreate",
    # Provider
    "LicenseUploadResponse",
    "ProviderProfileResponse",
    # Patient
    "EmergencyContact",
    "HealthGoal",
    "PatientProfileResponse",
    "PatientOnboardingData",
    "PatientOnboardingResponse",
    "PatientProfileUpdate",
    "OnboardingStatusResponse",
    # Goal
    "GoalStatus",
    "GoalFrequency",
    "GoalCompletionCreate",
    "GoalCompletionResponse",
    "MarkGoalRequest",
    "UnmarkGoalRequest",
    "GoalStatsResponse",
    "InitializeDailyGoalsResponse",
    "MarkMissedGoalsResponse",
    # Admin
    "LicenseStatus",
    "AdminAction",
    "AdminAuditLogResponse",
    "ProviderListResponse",
    "UpdateLicenseStatusRequest",
    "UpdateLicenseStatusResponse",
    "ProviderUpdateRequest",
    "UserWithRoleResponse",
    "LicenseUrlResponse",
    "DeleteProviderResponse",
    # Connection
    "ConnectionStatus",
    "PatientProviderConnectionCreate",
    "PatientProviderConnectionResponse",
    "PatientProviderConnectionWithDetails",
    "UpdateConnectionStatusRequest",
    "ConnectionStatusResponse",
    "DisconnectProviderResponse",
    # Device
    "DeviceType",
    "DeviceStatus",
    "DeviceTypeInfo",
    "ConnectDeviceRequest",
    "DeviceResponse",
    "DeviceWithTypeInfo",
    "DisconnectDeviceResponse",
    "SimulateDeviceDataRequest",
    "SimulateDeviceDataResponse",
    # Biomarker
    "BiomarkerType",
    "BiomarkerSource",
    "BiomarkerRangeResponse",
    "InsertBiomarkerRequest",
    "BiomarkerResponse",
    "LatestBiomarkerReading",
    "BiomarkerDashboardSummary",
]
