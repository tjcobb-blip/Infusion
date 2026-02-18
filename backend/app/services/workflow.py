"""
Workflow state machine for case status transitions.
Enforces allowed transitions and prerequisite checks.
"""

from sqlalchemy.orm import Session

from app.models.enums import CaseStatus, TaskType, TaskStatus, FulfillmentStatus
from app.models.models import (
    Case,
    TimelineEvent,
    AuditLog,
    Task,
    FinancialClearance,
    PharmacyOrder,
    Schedule,
)


# ── Allowed transitions map ───────────────────────────────────────────────────
# Each key maps to a set of statuses it can transition TO.
ALLOWED_TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.REFERRAL_RECEIVED: {
        CaseStatus.CLINICAL_COMPLETENESS_CHECK,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.CLINICAL_COMPLETENESS_CHECK: {
        CaseStatus.BENEFITS_INVESTIGATION,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.BENEFITS_INVESTIGATION: {
        CaseStatus.PRIOR_AUTH_SUBMITTED,
        CaseStatus.FINANCIAL_COUNSELING_PENDING,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.PRIOR_AUTH_SUBMITTED: {
        CaseStatus.PRIOR_AUTH_APPROVED,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.PRIOR_AUTH_APPROVED: {
        CaseStatus.FINANCIAL_COUNSELING_PENDING,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.FINANCIAL_COUNSELING_PENDING: {
        CaseStatus.FINANCIAL_CLEARED,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.FINANCIAL_CLEARED: {
        CaseStatus.WELCOME_CALL_PENDING,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.WELCOME_CALL_PENDING: {
        CaseStatus.WELCOME_CALL_COMPLETED,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.WELCOME_CALL_COMPLETED: {
        CaseStatus.SCHEDULING_READY,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.SCHEDULING_READY: {
        CaseStatus.SCHEDULED,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.SCHEDULED: {
        CaseStatus.PHARMACY_PUSH_PENDING,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.PHARMACY_PUSH_PENDING: {
        CaseStatus.PHARMACY_PUSHED,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.PHARMACY_PUSHED: {
        CaseStatus.DRUG_FULFILLMENT_IN_PROGRESS,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.DRUG_FULFILLMENT_IN_PROGRESS: {
        CaseStatus.DRUG_READY,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.DRUG_READY: {
        CaseStatus.INFUSION_COMPLETED,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.INFUSION_COMPLETED: {
        CaseStatus.ON_THERAPY,
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.ON_THERAPY: {
        CaseStatus.DISCONTINUED,
    },
    CaseStatus.DISCONTINUED: set(),
}


class TransitionError(Exception):
    """Raised when a status transition is invalid."""

    pass


def _check_prerequisites(
    db: Session, case: Case, new_status: CaseStatus
) -> list[str]:
    """Return list of blocker messages if prerequisites are not met."""
    blockers = []

    if new_status == CaseStatus.FINANCIAL_CLEARED:
        fc = (
            db.query(FinancialClearance)
            .filter(FinancialClearance.case_id == case.id)
            .first()
        )
        if not fc:
            blockers.append("Financial clearance record does not exist.")
        elif not fc.patient_acknowledged_cost:
            blockers.append("Patient has not acknowledged cost.")
        elif not fc.cleared_at:
            blockers.append("Financial clearance has not been marked as cleared.")

    if new_status == CaseStatus.WELCOME_CALL_COMPLETED:
        wc_task = (
            db.query(Task)
            .filter(
                Task.case_id == case.id,
                Task.type == TaskType.WELCOME_CALL,
                Task.status == TaskStatus.DONE,
            )
            .first()
        )
        if not wc_task:
            blockers.append(
                "Welcome call task must be completed (status=DONE) before transitioning."
            )

    if new_status == CaseStatus.SCHEDULING_READY:
        if case.status != CaseStatus.WELCOME_CALL_COMPLETED:
            blockers.append("Welcome call must be completed first.")
        fc = (
            db.query(FinancialClearance)
            .filter(FinancialClearance.case_id == case.id)
            .first()
        )
        if not fc or not fc.cleared_at:
            blockers.append("Financial clearance must be completed first.")

    if new_status == CaseStatus.SCHEDULED:
        if case.status != CaseStatus.SCHEDULING_READY:
            blockers.append("Case must be in SCHEDULING_READY status.")
        schedule = (
            db.query(Schedule).filter(Schedule.case_id == case.id).first()
        )
        if not schedule:
            blockers.append("Schedule must be created before marking as SCHEDULED.")

    if new_status == CaseStatus.PHARMACY_PUSHED:
        if case.status not in (
            CaseStatus.PHARMACY_PUSH_PENDING,
            CaseStatus.SCHEDULED,
        ):
            blockers.append("Case must be in SCHEDULED or PHARMACY_PUSH_PENDING status.")
        po = (
            db.query(PharmacyOrder)
            .filter(PharmacyOrder.case_id == case.id)
            .first()
        )
        if not po or not po.pushed_at:
            blockers.append("Pharmacy order must be pushed before transitioning.")

    if new_status == CaseStatus.DRUG_READY:
        if case.status != CaseStatus.DRUG_FULFILLMENT_IN_PROGRESS:
            blockers.append(
                "Case must be in DRUG_FULFILLMENT_IN_PROGRESS status."
            )
        po = (
            db.query(PharmacyOrder)
            .filter(PharmacyOrder.case_id == case.id)
            .first()
        )
        if not po or po.fulfillment_status not in (
            FulfillmentStatus.READY,
            FulfillmentStatus.SHIPPED,
            FulfillmentStatus.RECEIVED,
        ):
            blockers.append(
                "Pharmacy fulfillment status must be READY, SHIPPED, or RECEIVED."
            )

    return blockers


def transition_case(
    db: Session,
    case: Case,
    new_status: CaseStatus,
    actor_user_id,
) -> Case:
    """
    Attempt to transition a case to new_status.
    Raises TransitionError if the transition is not allowed.
    Creates timeline event and audit log on success.
    """
    old_status = case.status

    # Check if transition is allowed by the graph
    allowed = ALLOWED_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        raise TransitionError(
            f"Cannot transition from {old_status.value} to {new_status.value}. "
            f"Allowed transitions: {[s.value for s in allowed]}"
        )

    # Check prerequisites
    blockers = _check_prerequisites(db, case, new_status)
    if blockers:
        raise TransitionError(
            f"Cannot transition to {new_status.value}. Blockers: {'; '.join(blockers)}"
        )

    # Perform transition
    case.status = new_status

    # Create timeline event
    event = TimelineEvent(
        case_id=case.id,
        event_type="STATUS_CHANGED",
        actor_user_id=actor_user_id,
        metadata_json={
            "old_status": old_status.value,
            "new_status": new_status.value,
        },
    )
    db.add(event)

    # Write audit log
    audit = AuditLog(
        actor_user_id=actor_user_id,
        action="STATUS_CHANGED",
        entity_type="case",
        entity_id=case.id,
        metadata_json={
            "old_status": old_status.value,
            "new_status": new_status.value,
        },
    )
    db.add(audit)

    db.flush()
    return case


def get_case_blockers(db: Session, case: Case) -> list[dict]:
    """Return list of blockers preventing the case from advancing."""
    blockers = []

    # Check prescription completeness
    if case.prescription:
        rx = case.prescription
        missing_rx = []
        if not rx.drug_name:
            missing_rx.append("drug_name")
        if not rx.dose:
            missing_rx.append("dose")
        if not rx.frequency:
            missing_rx.append("frequency")
        if missing_rx:
            blockers.append({
                "type": "MISSING_RX_FIELDS",
                "message": f"Prescription missing: {', '.join(missing_rx)}",
                "fields": missing_rx,
            })
    else:
        blockers.append({
            "type": "MISSING_PRESCRIPTION",
            "message": "No prescription attached to case.",
        })

    # Check insurance
    if not case.insurance:
        blockers.append({
            "type": "MISSING_INSURANCE",
            "message": "No insurance information attached to case.",
        })

    # Financial clearance
    fc = (
        db.query(FinancialClearance)
        .filter(FinancialClearance.case_id == case.id)
        .first()
    )
    if not fc or not fc.cleared_at:
        blockers.append({
            "type": "FINANCIAL_NOT_CLEARED",
            "message": "Financial clearance not completed.",
        })

    # Welcome call
    wc_task = (
        db.query(Task)
        .filter(
            Task.case_id == case.id,
            Task.type == TaskType.WELCOME_CALL,
            Task.status == TaskStatus.DONE,
        )
        .first()
    )
    if not wc_task:
        blockers.append({
            "type": "WELCOME_CALL_NOT_COMPLETE",
            "message": "Welcome call not completed.",
        })

    # Schedule
    if not case.schedule:
        blockers.append({
            "type": "SCHEDULE_NOT_SET",
            "message": "Infusion not scheduled.",
        })

    # Pharmacy push
    po = (
        db.query(PharmacyOrder)
        .filter(PharmacyOrder.case_id == case.id)
        .first()
    )
    if not po or not po.pushed_at:
        blockers.append({
            "type": "PHARMACY_NOT_PUSHED",
            "message": "Pharmacy order not pushed.",
        })

    return blockers
