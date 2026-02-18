"""
Tests for the workflow state machine, transition validation,
financial clearance rules, welcome call requirements, and pharmacy coupling.
"""

import uuid
from datetime import datetime, timezone, date

import pytest

from app.models.enums import (
    CaseStatus,
    TaskType,
    TaskStatus,
    FulfillmentStatus,
)
from app.models.models import (
    Case,
    Task,
    FinancialClearance,
    PharmacyOrder,
    Schedule,
    TimelineEvent,
    AuditLog,
)
from app.services.workflow import (
    transition_case,
    TransitionError,
    ALLOWED_TRANSITIONS,
    get_case_blockers,
)


class TestWorkflowTransitions:
    """Test basic transition validation."""

    def test_valid_transition_from_referral_received(self, db, base_case, admin_user):
        result = transition_case(
            db, base_case, CaseStatus.CLINICAL_COMPLETENESS_CHECK, admin_user.id
        )
        assert result.status == CaseStatus.CLINICAL_COMPLETENESS_CHECK

    def test_invalid_transition_skipping_status(self, db, base_case, admin_user):
        with pytest.raises(TransitionError) as exc_info:
            transition_case(
                db, base_case, CaseStatus.BENEFITS_INVESTIGATION, admin_user.id
            )
        assert "Cannot transition" in str(exc_info.value)

    def test_cannot_transition_from_discontinued(self, db, base_case, admin_user):
        base_case.status = CaseStatus.DISCONTINUED
        db.flush()
        with pytest.raises(TransitionError):
            transition_case(
                db, base_case, CaseStatus.REFERRAL_RECEIVED, admin_user.id
            )

    def test_can_always_discontinue(self, db, base_case, admin_user):
        result = transition_case(
            db, base_case, CaseStatus.DISCONTINUED, admin_user.id
        )
        assert result.status == CaseStatus.DISCONTINUED

    def test_transition_creates_timeline_event(self, db, base_case, admin_user):
        transition_case(
            db, base_case, CaseStatus.CLINICAL_COMPLETENESS_CHECK, admin_user.id
        )
        events = (
            db.query(TimelineEvent)
            .filter(
                TimelineEvent.case_id == base_case.id,
                TimelineEvent.event_type == "STATUS_CHANGED",
            )
            .all()
        )
        assert len(events) == 1
        assert events[0].metadata_json["old_status"] == "REFERRAL_RECEIVED"
        assert events[0].metadata_json["new_status"] == "CLINICAL_COMPLETENESS_CHECK"

    def test_transition_creates_audit_log(self, db, base_case, admin_user):
        transition_case(
            db, base_case, CaseStatus.CLINICAL_COMPLETENESS_CHECK, admin_user.id
        )
        logs = (
            db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "case",
                AuditLog.entity_id == base_case.id,
                AuditLog.action == "STATUS_CHANGED",
            )
            .all()
        )
        assert len(logs) == 1

    def test_all_statuses_have_transitions_defined(self):
        for status in CaseStatus:
            assert status in ALLOWED_TRANSITIONS, (
                f"{status} missing from ALLOWED_TRANSITIONS"
            )

    def test_sequential_transitions_through_happy_path(
        self, db, base_case, admin_user
    ):
        """Walk the happy path from REFERRAL_RECEIVED to FINANCIAL_COUNSELING_PENDING."""
        transitions = [
            CaseStatus.CLINICAL_COMPLETENESS_CHECK,
            CaseStatus.BENEFITS_INVESTIGATION,
            CaseStatus.PRIOR_AUTH_SUBMITTED,
            CaseStatus.PRIOR_AUTH_APPROVED,
            CaseStatus.FINANCIAL_COUNSELING_PENDING,
        ]
        for new_status in transitions:
            transition_case(db, base_case, new_status, admin_user.id)
            assert base_case.status == new_status


class TestFinancialClearanceRules:
    """Test financial clearance prerequisites."""

    def test_cannot_clear_financial_without_record(self, db, base_case, admin_user):
        base_case.status = CaseStatus.FINANCIAL_COUNSELING_PENDING
        db.flush()
        with pytest.raises(TransitionError) as exc_info:
            transition_case(
                db, base_case, CaseStatus.FINANCIAL_CLEARED, admin_user.id
            )
        assert "Financial clearance record does not exist" in str(exc_info.value)

    def test_cannot_clear_financial_without_acknowledgement(
        self, db, base_case, admin_user
    ):
        base_case.status = CaseStatus.FINANCIAL_COUNSELING_PENDING
        fc = FinancialClearance(
            case_id=base_case.id,
            patient_acknowledged_cost=False,
        )
        db.add(fc)
        db.flush()
        with pytest.raises(TransitionError) as exc_info:
            transition_case(
                db, base_case, CaseStatus.FINANCIAL_CLEARED, admin_user.id
            )
        assert "acknowledged cost" in str(exc_info.value)

    def test_cannot_clear_financial_without_cleared_at(
        self, db, base_case, admin_user
    ):
        base_case.status = CaseStatus.FINANCIAL_COUNSELING_PENDING
        fc = FinancialClearance(
            case_id=base_case.id,
            patient_acknowledged_cost=True,
            cleared_at=None,
        )
        db.add(fc)
        db.flush()
        with pytest.raises(TransitionError) as exc_info:
            transition_case(
                db, base_case, CaseStatus.FINANCIAL_CLEARED, admin_user.id
            )
        assert "cleared" in str(exc_info.value).lower()

    def test_can_clear_financial_with_proper_record(
        self, db, base_case, admin_user
    ):
        base_case.status = CaseStatus.FINANCIAL_COUNSELING_PENDING
        fc = FinancialClearance(
            case_id=base_case.id,
            patient_acknowledged_cost=True,
            cleared_at=datetime.now(timezone.utc),
        )
        db.add(fc)
        db.flush()
        result = transition_case(
            db, base_case, CaseStatus.FINANCIAL_CLEARED, admin_user.id
        )
        assert result.status == CaseStatus.FINANCIAL_CLEARED


class TestWelcomeCallCompletion:
    """Test welcome call task completion requirements."""

    def test_cannot_complete_welcome_call_without_done_task(
        self, db, base_case, admin_user
    ):
        base_case.status = CaseStatus.WELCOME_CALL_PENDING
        db.flush()
        with pytest.raises(TransitionError) as exc_info:
            transition_case(
                db, base_case, CaseStatus.WELCOME_CALL_COMPLETED, admin_user.id
            )
        assert "Welcome call task must be completed" in str(exc_info.value)

    def test_pending_welcome_call_task_not_sufficient(
        self, db, base_case, admin_user
    ):
        base_case.status = CaseStatus.WELCOME_CALL_PENDING
        task = Task(
            case_id=base_case.id,
            type=TaskType.WELCOME_CALL,
            status=TaskStatus.PENDING,
        )
        db.add(task)
        db.flush()
        with pytest.raises(TransitionError):
            transition_case(
                db, base_case, CaseStatus.WELCOME_CALL_COMPLETED, admin_user.id
            )

    def test_can_complete_welcome_call_with_done_task(
        self, db, base_case, admin_user
    ):
        base_case.status = CaseStatus.WELCOME_CALL_PENDING
        task = Task(
            case_id=base_case.id,
            type=TaskType.WELCOME_CALL,
            status=TaskStatus.DONE,
            payload_json={
                "reached": True,
                "outcome": "REACHED",
                "patient_questions": "None",
                "next_steps": "Proceed",
            },
        )
        db.add(task)
        db.flush()
        result = transition_case(
            db, base_case, CaseStatus.WELCOME_CALL_COMPLETED, admin_user.id
        )
        assert result.status == CaseStatus.WELCOME_CALL_COMPLETED


class TestSchedulingPrerequisites:
    """Test scheduling readiness checks."""

    def test_scheduling_ready_requires_welcome_call_completed(
        self, db, base_case, admin_user
    ):
        base_case.status = CaseStatus.WELCOME_CALL_COMPLETED
        db.flush()
        # Missing financial clearance
        with pytest.raises(TransitionError) as exc_info:
            transition_case(
                db, base_case, CaseStatus.SCHEDULING_READY, admin_user.id
            )
        assert "Financial clearance" in str(exc_info.value)

    def test_scheduling_ready_succeeds_with_all_prerequisites(
        self, db, base_case, admin_user
    ):
        base_case.status = CaseStatus.WELCOME_CALL_COMPLETED
        fc = FinancialClearance(
            case_id=base_case.id,
            patient_acknowledged_cost=True,
            cleared_at=datetime.now(timezone.utc),
        )
        db.add(fc)
        db.flush()
        result = transition_case(
            db, base_case, CaseStatus.SCHEDULING_READY, admin_user.id
        )
        assert result.status == CaseStatus.SCHEDULING_READY

    def test_scheduled_requires_schedule_record(
        self, db, base_case, admin_user
    ):
        base_case.status = CaseStatus.SCHEDULING_READY
        db.flush()
        with pytest.raises(TransitionError) as exc_info:
            transition_case(
                db, base_case, CaseStatus.SCHEDULED, admin_user.id
            )
        assert "Schedule must be created" in str(exc_info.value)

    def test_scheduled_succeeds_with_schedule(
        self, db, base_case, admin_user
    ):
        base_case.status = CaseStatus.SCHEDULING_READY
        sched = Schedule(
            case_id=base_case.id,
            date_time=datetime.now(timezone.utc),
            location="Suite 200",
            duration_minutes=120,
        )
        db.add(sched)
        db.flush()
        result = transition_case(
            db, base_case, CaseStatus.SCHEDULED, admin_user.id
        )
        assert result.status == CaseStatus.SCHEDULED


class TestPharmacyPushStatusCoupling:
    """Test pharmacy push and fulfillment status coupling."""

    def test_pharmacy_pushed_requires_order(
        self, db, base_case, admin_user
    ):
        base_case.status = CaseStatus.PHARMACY_PUSH_PENDING
        db.flush()
        with pytest.raises(TransitionError) as exc_info:
            transition_case(
                db, base_case, CaseStatus.PHARMACY_PUSHED, admin_user.id
            )
        assert "Pharmacy order must be pushed" in str(exc_info.value)

    def test_pharmacy_pushed_succeeds_with_order(
        self, db, base_case, admin_user
    ):
        base_case.status = CaseStatus.PHARMACY_PUSH_PENDING
        po = PharmacyOrder(
            case_id=base_case.id,
            pushed_at=datetime.now(timezone.utc),
            fulfillment_status=FulfillmentStatus.NOT_STARTED,
        )
        db.add(po)
        db.flush()
        result = transition_case(
            db, base_case, CaseStatus.PHARMACY_PUSHED, admin_user.id
        )
        assert result.status == CaseStatus.PHARMACY_PUSHED

    def test_drug_ready_requires_fulfillment_ready(
        self, db, base_case, admin_user
    ):
        base_case.status = CaseStatus.DRUG_FULFILLMENT_IN_PROGRESS
        po = PharmacyOrder(
            case_id=base_case.id,
            pushed_at=datetime.now(timezone.utc),
            fulfillment_status=FulfillmentStatus.IN_PROGRESS,
        )
        db.add(po)
        db.flush()
        with pytest.raises(TransitionError) as exc_info:
            transition_case(
                db, base_case, CaseStatus.DRUG_READY, admin_user.id
            )
        assert "fulfillment status" in str(exc_info.value).lower()

    def test_drug_ready_succeeds_with_ready_fulfillment(
        self, db, base_case, admin_user
    ):
        base_case.status = CaseStatus.DRUG_FULFILLMENT_IN_PROGRESS
        po = PharmacyOrder(
            case_id=base_case.id,
            pushed_at=datetime.now(timezone.utc),
            fulfillment_status=FulfillmentStatus.READY,
        )
        db.add(po)
        db.flush()
        result = transition_case(
            db, base_case, CaseStatus.DRUG_READY, admin_user.id
        )
        assert result.status == CaseStatus.DRUG_READY

    def test_drug_ready_succeeds_with_received_fulfillment(
        self, db, base_case, admin_user
    ):
        base_case.status = CaseStatus.DRUG_FULFILLMENT_IN_PROGRESS
        po = PharmacyOrder(
            case_id=base_case.id,
            pushed_at=datetime.now(timezone.utc),
            fulfillment_status=FulfillmentStatus.RECEIVED,
        )
        db.add(po)
        db.flush()
        result = transition_case(
            db, base_case, CaseStatus.DRUG_READY, admin_user.id
        )
        assert result.status == CaseStatus.DRUG_READY


class TestBlockers:
    """Test the blockers panel logic."""

    def test_fresh_case_has_all_blockers(self, db, base_case):
        blockers = get_case_blockers(db, base_case)
        types = [b["type"] for b in blockers]
        assert "MISSING_PRESCRIPTION" in types
        assert "MISSING_INSURANCE" in types
        assert "FINANCIAL_NOT_CLEARED" in types
        assert "WELCOME_CALL_NOT_COMPLETE" in types
        assert "SCHEDULE_NOT_SET" in types
        assert "PHARMACY_NOT_PUSHED" in types

    def test_case_with_all_requirements_has_no_blockers(
        self, db, case_with_rx_and_insurance, admin_user
    ):
        case = case_with_rx_and_insurance
        # Add financial clearance
        fc = FinancialClearance(
            case_id=case.id,
            patient_acknowledged_cost=True,
            cleared_at=datetime.now(timezone.utc),
        )
        db.add(fc)
        # Add welcome call task
        wc = Task(
            case_id=case.id,
            type=TaskType.WELCOME_CALL,
            status=TaskStatus.DONE,
        )
        db.add(wc)
        # Add schedule
        sched = Schedule(
            case_id=case.id,
            date_time=datetime.now(timezone.utc),
        )
        db.add(sched)
        # Add pharmacy order
        po = PharmacyOrder(
            case_id=case.id,
            pushed_at=datetime.now(timezone.utc),
            fulfillment_status=FulfillmentStatus.NOT_STARTED,
        )
        db.add(po)
        db.flush()

        blockers = get_case_blockers(db, case)
        assert len(blockers) == 0
