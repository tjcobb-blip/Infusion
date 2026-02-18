import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    Numeric,
    Integer,
    Date,
    Enum as SAEnum,
    JSON,
    TypeDecorator,
    CHAR,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


# Cross-database UUID type: uses CHAR(32) so it works on both PostgreSQL and SQLite
class GUID(TypeDecorator):
    """Platform-independent UUID type. Stores as CHAR(32) in SQLite."""

    impl = CHAR(32)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, uuid.UUID):
                return value.hex
            return uuid.UUID(value).hex
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value)
        return value
from app.models.enums import (
    UserRole,
    OrgType,
    CaseStatus,
    TaskType,
    TaskStatus,
    FulfillmentStatus,
)


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return uuid.uuid4()


# ── Organizations ──────────────────────────────────────────────────────────────
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(GUID, primary_key=True, default=new_uuid)
    name = Column(String(255), nullable=False)
    type = Column(SAEnum(OrgType, name="org_type"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    users = relationship("User", back_populates="organization")
    providers = relationship("Provider", back_populates="organization")


# ── Users ──────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=new_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole, name="user_role"), nullable=False)
    org_id = Column(GUID, ForeignKey("organizations.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization", back_populates="users")


# ── Patients ───────────────────────────────────────────────────────────────────
class Patient(Base):
    __tablename__ = "patients"

    id = Column(GUID, primary_key=True, default=new_uuid)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    dob = Column(Date, nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    cases = relationship("Case", back_populates="patient")


# ── Providers ──────────────────────────────────────────────────────────────────
class Provider(Base):
    __tablename__ = "providers"

    id = Column(GUID, primary_key=True, default=new_uuid)
    org_id = Column(GUID, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    npi = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization", back_populates="providers")


# ── Cases (Referrals) ─────────────────────────────────────────────────────────
class Case(Base):
    __tablename__ = "cases"

    id = Column(GUID, primary_key=True, default=new_uuid)
    patient_id = Column(
        GUID, ForeignKey("patients.id"), nullable=True
    )
    provider_org_id = Column(
        GUID, ForeignKey("organizations.id"), nullable=False
    )
    infusion_org_id = Column(
        GUID, ForeignKey("organizations.id"), nullable=True
    )
    status = Column(
        SAEnum(CaseStatus, name="case_status"),
        nullable=False,
        default=CaseStatus.REFERRAL_RECEIVED,
    )
    created_by_user_id = Column(
        GUID, ForeignKey("users.id"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    patient = relationship("Patient", back_populates="cases")
    provider_org = relationship(
        "Organization", foreign_keys=[provider_org_id]
    )
    infusion_org = relationship(
        "Organization", foreign_keys=[infusion_org_id]
    )
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    prescription = relationship(
        "Prescription", back_populates="case", uselist=False
    )
    insurance = relationship("Insurance", back_populates="case", uselist=False)
    documents = relationship("Document", back_populates="case")
    tasks = relationship("Task", back_populates="case")
    timeline_events = relationship(
        "TimelineEvent", back_populates="case", order_by="TimelineEvent.created_at"
    )
    financial_clearance = relationship(
        "FinancialClearance", back_populates="case", uselist=False
    )
    pharmacy_order = relationship(
        "PharmacyOrder", back_populates="case", uselist=False
    )
    schedule = relationship("Schedule", back_populates="case", uselist=False)


# ── Prescriptions ─────────────────────────────────────────────────────────────
class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(GUID, primary_key=True, default=new_uuid)
    case_id = Column(
        GUID, ForeignKey("cases.id"), nullable=False, unique=True
    )
    drug_name = Column(String(255), nullable=True)
    dose = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    route = Column(String(100), nullable=True)
    diagnosis_icd10 = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    case = relationship("Case", back_populates="prescription")


# ── Insurance ─────────────────────────────────────────────────────────────────
class Insurance(Base):
    __tablename__ = "insurance"

    id = Column(GUID, primary_key=True, default=new_uuid)
    case_id = Column(
        GUID, ForeignKey("cases.id"), nullable=False, unique=True
    )
    payer_name = Column(String(255), nullable=True)
    member_id = Column(String(100), nullable=True)
    group_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    case = relationship("Case", back_populates="insurance")


# ── Documents ─────────────────────────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id = Column(GUID, primary_key=True, default=new_uuid)
    case_id = Column(GUID, ForeignKey("cases.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=True)
    storage_url = Column(Text, nullable=True)
    uploaded_by_user_id = Column(
        GUID, ForeignKey("users.id"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), default=utcnow)

    case = relationship("Case", back_populates="documents")
    uploaded_by = relationship("User")


# ── Tasks ─────────────────────────────────────────────────────────────────────
class Task(Base):
    __tablename__ = "tasks"

    id = Column(GUID, primary_key=True, default=new_uuid)
    case_id = Column(GUID, ForeignKey("cases.id"), nullable=False)
    type = Column(SAEnum(TaskType, name="task_type"), nullable=False)
    status = Column(
        SAEnum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.PENDING,
    )
    owner_user_id = Column(
        GUID, ForeignKey("users.id"), nullable=True
    )
    due_at = Column(DateTime(timezone=True), nullable=True)
    payload_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    case = relationship("Case", back_populates="tasks")
    owner = relationship("User")


# ── Timeline Events ──────────────────────────────────────────────────────────
class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(GUID, primary_key=True, default=new_uuid)
    case_id = Column(GUID, ForeignKey("cases.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    actor_user_id = Column(
        GUID, ForeignKey("users.id"), nullable=True
    )
    metadata_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    case = relationship("Case", back_populates="timeline_events")
    actor = relationship("User")


# ── Audit Logs ────────────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(GUID, primary_key=True, default=new_uuid)
    actor_user_id = Column(
        GUID, ForeignKey("users.id"), nullable=True
    )
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(GUID, nullable=True)
    metadata_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    actor = relationship("User")


# ── Financial Clearance (Step 6A) ─────────────────────────────────────────────
class FinancialClearance(Base):
    __tablename__ = "financial_clearances"

    id = Column(GUID, primary_key=True, default=new_uuid)
    case_id = Column(
        GUID, ForeignKey("cases.id"), nullable=False, unique=True
    )
    benefits_verified_at = Column(DateTime(timezone=True), nullable=True)
    cost_estimate_amount = Column(Numeric(10, 2), nullable=True)
    patient_acknowledged_cost = Column(Boolean, default=False)
    assistance_program = Column(String(255), nullable=True)
    cleared_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    case = relationship("Case", back_populates="financial_clearance")


# ── Pharmacy Order (Step 6C) ─────────────────────────────────────────────────
class PharmacyOrder(Base):
    __tablename__ = "pharmacy_orders"

    id = Column(GUID, primary_key=True, default=new_uuid)
    case_id = Column(
        GUID, ForeignKey("cases.id"), nullable=False, unique=True
    )
    pushed_at = Column(DateTime(timezone=True), nullable=True)
    ship_to = Column(Text, nullable=True)
    requested_arrival_date = Column(Date, nullable=True)
    fulfillment_status = Column(
        SAEnum(FulfillmentStatus, name="fulfillment_status"),
        nullable=False,
        default=FulfillmentStatus.NOT_STARTED,
    )
    pharmacy_notes = Column(Text, nullable=True)
    ndc = Column(String(50), nullable=True)
    lot = Column(String(50), nullable=True)
    expiration_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    case = relationship("Case", back_populates="pharmacy_order")


# ── Schedule ──────────────────────────────────────────────────────────────────
class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(GUID, primary_key=True, default=new_uuid)
    case_id = Column(
        GUID, ForeignKey("cases.id"), nullable=False, unique=True
    )
    date_time = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(255), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    case = relationship("Case", back_populates="schedule")
