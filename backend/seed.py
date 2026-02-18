"""
Seed script: creates organizations, users, and sample cases.
Run: python seed.py
"""

import uuid
from datetime import datetime, timezone, timedelta, date

from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.enums import (
    UserRole,
    OrgType,
    CaseStatus,
    TaskType,
    TaskStatus,
    FulfillmentStatus,
)
from app.models.models import (
    Organization,
    User,
    Patient,
    Provider,
    Case,
    Prescription,
    Insurance,
    Task,
    TimelineEvent,
    FinancialClearance,
    PharmacyOrder,
    Schedule,
    Document,
)


def seed():
    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(Organization).first():
            print("Database already seeded. Skipping.")
            return

        # ── Organizations ──────────────────────────────────────────────
        provider_org = Organization(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            name="Metro Rheumatology Associates",
            type=OrgType.PROVIDER_ORG,
        )
        infusion_org = Organization(
            id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            name="Specialty Infusion Center",
            type=OrgType.INFUSION_ORG,
        )
        db.add_all([provider_org, infusion_org])
        db.flush()

        # ── Users ──────────────────────────────────────────────────────
        provider_user = User(
            id=uuid.UUID("10000000-0000-0000-0000-000000000001"),
            email="provider@example.com",
            password_hash=hash_password("password123"),
            role=UserRole.PROVIDER,
            org_id=provider_org.id,
        )
        admin_user = User(
            id=uuid.UUID("10000000-0000-0000-0000-000000000002"),
            email="admin@example.com",
            password_hash=hash_password("password123"),
            role=UserRole.INFUSION_ADMIN,
            org_id=infusion_org.id,
        )
        db.add_all([provider_user, admin_user])
        db.flush()

        # ── Provider ───────────────────────────────────────────────────
        doc = Provider(
            org_id=provider_org.id,
            name="Dr. Sarah Chen",
            npi="1234567890",
        )
        db.add(doc)
        db.flush()

        # ── Patients ──────────────────────────────────────────────────
        patients = []
        patient_data = [
            ("John", "Doe", date(1965, 3, 15), "555-0101", "john.doe@email.com"),
            ("Jane", "Smith", date(1978, 7, 22), "555-0102", "jane.smith@email.com"),
            ("Robert", "Johnson", date(1955, 11, 8), "555-0103", "r.johnson@email.com"),
            ("Maria", "Garcia", date(1982, 1, 30), "555-0104", "m.garcia@email.com"),
            ("David", "Wilson", date(1970, 5, 12), "555-0105", "d.wilson@email.com"),
            ("Susan", "Brown", date(1968, 9, 3), "555-0106", "s.brown@email.com"),
            ("Michael", "Davis", date(1990, 2, 28), "555-0107", "m.davis@email.com"),
            ("Lisa", "Martinez", date(1985, 12, 17), "555-0108", "l.martinez@email.com"),
            ("James", "Anderson", date(1972, 6, 9), "555-0109", "j.anderson@email.com"),
            ("Patricia", "Taylor", date(1960, 4, 25), "555-0110", "p.taylor@email.com"),
        ]
        for fn, ln, dob, phone, email in patient_data:
            p = Patient(first_name=fn, last_name=ln, dob=dob, phone=phone, email=email)
            db.add(p)
            patients.append(p)
        db.flush()

        # ── Cases at various statuses ─────────────────────────────────
        now = datetime.now(timezone.utc)
        case_configs = [
            (CaseStatus.REFERRAL_RECEIVED, False),
            (CaseStatus.CLINICAL_COMPLETENESS_CHECK, True),
            (CaseStatus.BENEFITS_INVESTIGATION, True),
            (CaseStatus.PRIOR_AUTH_SUBMITTED, True),
            (CaseStatus.PRIOR_AUTH_APPROVED, True),
            (CaseStatus.FINANCIAL_COUNSELING_PENDING, True),
            (CaseStatus.FINANCIAL_CLEARED, True),
            (CaseStatus.WELCOME_CALL_COMPLETED, True),
            (CaseStatus.SCHEDULED, True),
            (CaseStatus.ON_THERAPY, True),
        ]

        drugs = [
            ("Infliximab", "5mg/kg", "Every 8 weeks", "IV", "M05.79"),
            ("Rituximab", "1000mg", "Every 6 months", "IV", "M06.09"),
            ("Ocrelizumab", "600mg", "Every 6 months", "IV", "G35"),
            ("Natalizumab", "300mg", "Every 4 weeks", "IV", "G35"),
            ("Vedolizumab", "300mg", "Every 8 weeks", "IV", "K50.90"),
            ("Tocilizumab", "8mg/kg", "Every 4 weeks", "IV", "M06.09"),
            ("Abatacept", "1000mg", "Every 4 weeks", "IV", "M05.79"),
            ("Belimumab", "10mg/kg", "Every 4 weeks", "IV", "M32.9"),
            ("Eculizumab", "900mg", "Every 2 weeks", "IV", "D59.3"),
            ("IVIG", "2g/kg", "Every 3 weeks", "IV", "D80.1"),
        ]

        for i, (status, assign_infusion) in enumerate(case_configs):
            case = Case(
                patient_id=patients[i].id,
                provider_org_id=provider_org.id,
                infusion_org_id=infusion_org.id if assign_infusion else None,
                status=status,
                created_by_user_id=provider_user.id,
                created_at=now - timedelta(days=30 - i * 3),
            )
            db.add(case)
            db.flush()

            # Add prescription
            drug_name, dose, freq, route, icd10 = drugs[i]
            rx = Prescription(
                case_id=case.id,
                drug_name=drug_name,
                dose=dose,
                frequency=freq,
                route=route,
                diagnosis_icd10=icd10,
            )
            db.add(rx)

            # Add insurance
            ins = Insurance(
                case_id=case.id,
                payer_name="Blue Cross Blue Shield",
                member_id=f"BCBS-{100000 + i}",
                group_id=f"GRP-{5000 + i}",
            )
            db.add(ins)

            # Timeline event for creation
            event = TimelineEvent(
                case_id=case.id,
                event_type="CASE_CREATED",
                actor_user_id=provider_user.id,
                metadata_json={"status": CaseStatus.REFERRAL_RECEIVED.value},
                created_at=case.created_at,
            )
            db.add(event)

            # For advanced cases, add financial clearance
            if status in (
                CaseStatus.FINANCIAL_CLEARED,
                CaseStatus.WELCOME_CALL_COMPLETED,
                CaseStatus.SCHEDULED,
                CaseStatus.ON_THERAPY,
            ):
                fc = FinancialClearance(
                    case_id=case.id,
                    benefits_verified_at=now - timedelta(days=15),
                    cost_estimate_amount=2500.00,
                    patient_acknowledged_cost=True,
                    cleared_at=now - timedelta(days=14),
                )
                db.add(fc)

            # For welcome call completed and beyond
            if status in (
                CaseStatus.WELCOME_CALL_COMPLETED,
                CaseStatus.SCHEDULED,
                CaseStatus.ON_THERAPY,
            ):
                wc = Task(
                    case_id=case.id,
                    type=TaskType.WELCOME_CALL,
                    status=TaskStatus.DONE,
                    owner_user_id=admin_user.id,
                    payload_json={
                        "reached": True,
                        "outcome": "REACHED",
                        "patient_questions": "None at this time",
                        "next_steps": "Proceed to scheduling",
                    },
                )
                db.add(wc)

            # For scheduled and beyond
            if status in (CaseStatus.SCHEDULED, CaseStatus.ON_THERAPY):
                sched = Schedule(
                    case_id=case.id,
                    date_time=now + timedelta(days=7 + i),
                    location="Specialty Infusion Center - Suite 200",
                    duration_minutes=120,
                )
                db.add(sched)

            # For ON_THERAPY, add pharmacy order
            if status == CaseStatus.ON_THERAPY:
                po = PharmacyOrder(
                    case_id=case.id,
                    pushed_at=now - timedelta(days=5),
                    ship_to="Specialty Infusion Center - Suite 200",
                    requested_arrival_date=date.today() + timedelta(days=2),
                    fulfillment_status=FulfillmentStatus.RECEIVED,
                    pharmacy_notes="Standard delivery",
                )
                db.add(po)

        db.commit()
        print("Seed data created successfully!")
        print("  - 2 organizations (provider + infusion)")
        print("  - 2 users: provider@example.com / admin@example.com (password: password123)")
        print("  - 10 patients with 10 cases across various statuses")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
