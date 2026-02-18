"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enums
    org_type = sa.Enum("PROVIDER_ORG", "INFUSION_ORG", name="org_type")
    user_role = sa.Enum("PROVIDER", "INFUSION_ADMIN", name="user_role")
    case_status = sa.Enum(
        "REFERRAL_RECEIVED",
        "CLINICAL_COMPLETENESS_CHECK",
        "BENEFITS_INVESTIGATION",
        "PRIOR_AUTH_SUBMITTED",
        "PRIOR_AUTH_APPROVED",
        "FINANCIAL_COUNSELING_PENDING",
        "FINANCIAL_CLEARED",
        "WELCOME_CALL_PENDING",
        "WELCOME_CALL_COMPLETED",
        "SCHEDULING_READY",
        "SCHEDULED",
        "PHARMACY_PUSH_PENDING",
        "PHARMACY_PUSHED",
        "DRUG_FULFILLMENT_IN_PROGRESS",
        "DRUG_READY",
        "INFUSION_COMPLETED",
        "ON_THERAPY",
        "DISCONTINUED",
        name="case_status",
    )
    task_type = sa.Enum(
        "CLINICAL_REVIEW",
        "BENEFITS_INVESTIGATION",
        "PRIOR_AUTH",
        "FINANCIAL_COUNSELING",
        "WELCOME_CALL",
        "SCHEDULING",
        "PHARMACY_PUSH",
        "DOCUMENT_REQUEST",
        "GENERAL",
        name="task_type",
    )
    task_status = sa.Enum(
        "PENDING", "IN_PROGRESS", "DONE", "CANCELLED", name="task_status"
    )
    fulfillment_status = sa.Enum(
        "NOT_STARTED", "IN_PROGRESS", "READY", "SHIPPED", "RECEIVED",
        name="fulfillment_status",
    )

    # Organizations
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", org_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # Patients
    op.create_table(
        "patients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("first_name", sa.String(255), nullable=False),
        sa.Column("last_name", sa.String(255), nullable=False),
        sa.Column("dob", sa.Date, nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Providers
    op.create_table(
        "providers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("npi", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Cases
    op.create_table(
        "cases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("provider_org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("infusion_org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("status", case_status, nullable=False, server_default="REFERRAL_RECEIVED"),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Prescriptions
    op.create_table(
        "prescriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False, unique=True),
        sa.Column("drug_name", sa.String(255), nullable=True),
        sa.Column("dose", sa.String(100), nullable=True),
        sa.Column("frequency", sa.String(100), nullable=True),
        sa.Column("route", sa.String(100), nullable=True),
        sa.Column("diagnosis_icd10", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Insurance
    op.create_table(
        "insurance",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False, unique=True),
        sa.Column("payer_name", sa.String(255), nullable=True),
        sa.Column("member_id", sa.String(100), nullable=True),
        sa.Column("group_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Documents
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=True),
        sa.Column("storage_url", sa.Text, nullable=True),
        sa.Column("uploaded_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Tasks
    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("type", task_type, nullable=False),
        sa.Column("status", task_status, nullable=False, server_default="PENDING"),
        sa.Column("owner_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_json", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Timeline events
    op.create_table(
        "timeline_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("metadata_json", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Audit logs
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("metadata_json", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Financial clearances
    op.create_table(
        "financial_clearances",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False, unique=True),
        sa.Column("benefits_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cost_estimate_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("patient_acknowledged_cost", sa.Boolean, default=False),
        sa.Column("assistance_program", sa.String(255), nullable=True),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Pharmacy orders
    op.create_table(
        "pharmacy_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False, unique=True),
        sa.Column("pushed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ship_to", sa.Text, nullable=True),
        sa.Column("requested_arrival_date", sa.Date, nullable=True),
        sa.Column("fulfillment_status", fulfillment_status, nullable=False, server_default="NOT_STARTED"),
        sa.Column("pharmacy_notes", sa.Text, nullable=True),
        sa.Column("ndc", sa.String(50), nullable=True),
        sa.Column("lot", sa.String(50), nullable=True),
        sa.Column("expiration_date", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Schedules
    op.create_table(
        "schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False, unique=True),
        sa.Column("date_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("duration_minutes", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("schedules")
    op.drop_table("pharmacy_orders")
    op.drop_table("financial_clearances")
    op.drop_table("audit_logs")
    op.drop_table("timeline_events")
    op.drop_table("tasks")
    op.drop_table("documents")
    op.drop_table("insurance")
    op.drop_table("prescriptions")
    op.drop_table("cases")
    op.drop_table("providers")
    op.drop_table("patients")
    op.drop_table("users")
    op.drop_table("organizations")
    sa.Enum(name="fulfillment_status").drop(op.get_bind())
    sa.Enum(name="task_status").drop(op.get_bind())
    sa.Enum(name="task_type").drop(op.get_bind())
    sa.Enum(name="case_status").drop(op.get_bind())
    sa.Enum(name="user_role").drop(op.get_bind())
    sa.Enum(name="org_type").drop(op.get_bind())
