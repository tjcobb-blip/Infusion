from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.models.enums import (
    UserRole,
    OrgType,
    CaseStatus,
    TaskType,
    TaskStatus,
    FulfillmentStatus,
    WelcomeCallOutcome,
)


# ── Auth ──────────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: UserRole
    org_id: UUID


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    role: UserRole
    org_id: UUID

    class Config:
        from_attributes = True


# ── Organization ──────────────────────────────────────────────────────────────
class OrgResponse(BaseModel):
    id: UUID
    name: str
    type: OrgType

    class Config:
        from_attributes = True


# ── Patient ───────────────────────────────────────────────────────────────────
class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    dob: date | None = None
    phone: str | None = None
    email: str | None = None


class PatientResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    dob: date | None = None
    phone: str | None = None
    email: str | None = None

    class Config:
        from_attributes = True


# ── Prescription ──────────────────────────────────────────────────────────────
class PrescriptionUpdate(BaseModel):
    drug_name: str | None = None
    dose: str | None = None
    frequency: str | None = None
    route: str | None = None
    diagnosis_icd10: str | None = None


class PrescriptionResponse(BaseModel):
    id: UUID
    case_id: UUID
    drug_name: str | None = None
    dose: str | None = None
    frequency: str | None = None
    route: str | None = None
    diagnosis_icd10: str | None = None

    class Config:
        from_attributes = True


# ── Insurance ─────────────────────────────────────────────────────────────────
class InsuranceUpdate(BaseModel):
    payer_name: str | None = None
    member_id: str | None = None
    group_id: str | None = None


class InsuranceResponse(BaseModel):
    id: UUID
    case_id: UUID
    payer_name: str | None = None
    member_id: str | None = None
    group_id: str | None = None

    class Config:
        from_attributes = True


# ── Case ──────────────────────────────────────────────────────────────────────
class CaseCreate(BaseModel):
    patient: PatientCreate | None = None
    patient_id: UUID | None = None


class CaseStatusUpdate(BaseModel):
    new_status: CaseStatus


class AssignInfusionOrg(BaseModel):
    infusion_org_id: UUID


class CaseSummaryResponse(BaseModel):
    id: UUID
    status: CaseStatus
    provider_org_id: UUID
    infusion_org_id: UUID | None = None
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    patient: PatientResponse | None = None

    class Config:
        from_attributes = True


class CaseDetailResponse(BaseModel):
    id: UUID
    status: CaseStatus
    provider_org_id: UUID
    infusion_org_id: UUID | None = None
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    patient: PatientResponse | None = None
    prescription: PrescriptionResponse | None = None
    insurance: InsuranceResponse | None = None

    class Config:
        from_attributes = True


# ── Document ──────────────────────────────────────────────────────────────────
class DocumentResponse(BaseModel):
    id: UUID
    case_id: UUID
    file_name: str
    file_type: str | None = None
    storage_url: str | None = None
    uploaded_by_user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ── Task ──────────────────────────────────────────────────────────────────────
class TaskCreate(BaseModel):
    type: TaskType
    owner_user_id: UUID | None = None
    due_at: datetime | None = None
    payload_json: dict | None = None


class TaskUpdate(BaseModel):
    status: TaskStatus | None = None
    owner_user_id: UUID | None = None
    payload_json: dict | None = None


class TaskResponse(BaseModel):
    id: UUID
    case_id: UUID
    type: TaskType
    status: TaskStatus
    owner_user_id: UUID | None = None
    due_at: datetime | None = None
    payload_json: dict | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# ── Timeline ─────────────────────────────────────────────────────────────────
class TimelineEventResponse(BaseModel):
    id: UUID
    case_id: UUID
    event_type: str
    actor_user_id: UUID | None = None
    metadata_json: dict | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Schedule ──────────────────────────────────────────────────────────────────
class ScheduleCreate(BaseModel):
    date_time: datetime
    location: str | None = None
    duration_minutes: int | None = None


class ScheduleResponse(BaseModel):
    id: UUID
    case_id: UUID
    date_time: datetime
    location: str | None = None
    duration_minutes: int | None = None

    class Config:
        from_attributes = True


# ── Financial Clearance ──────────────────────────────────────────────────────
class FinancialClearanceUpdate(BaseModel):
    benefits_verified_at: datetime | None = None
    cost_estimate_amount: Decimal | None = None
    patient_acknowledged_cost: bool | None = None
    assistance_program: str | None = None
    cleared_at: datetime | None = None


class FinancialClearanceResponse(BaseModel):
    id: UUID
    case_id: UUID
    benefits_verified_at: datetime | None = None
    cost_estimate_amount: Decimal | None = None
    patient_acknowledged_cost: bool = False
    assistance_program: str | None = None
    cleared_at: datetime | None = None

    class Config:
        from_attributes = True


# ── Pharmacy Order ───────────────────────────────────────────────────────────
class PharmacyPushCreate(BaseModel):
    pharmacy_notes: str | None = None
    ship_to: str | None = None
    requested_arrival_date: date | None = None


class PharmacyOrderUpdate(BaseModel):
    fulfillment_status: FulfillmentStatus | None = None
    ndc: str | None = None
    lot: str | None = None
    expiration_date: date | None = None


class PharmacyOrderResponse(BaseModel):
    id: UUID
    case_id: UUID
    pushed_at: datetime | None = None
    ship_to: str | None = None
    requested_arrival_date: date | None = None
    fulfillment_status: FulfillmentStatus
    pharmacy_notes: str | None = None
    ndc: str | None = None
    lot: str | None = None
    expiration_date: date | None = None

    class Config:
        from_attributes = True


# ── Blockers ─────────────────────────────────────────────────────────────────
class BlockerResponse(BaseModel):
    type: str
    message: str
    fields: list[str] | None = None
