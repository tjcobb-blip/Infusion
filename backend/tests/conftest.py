"""
Test configuration using SQLite in-memory database.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.enums import (
    UserRole,
    OrgType,
    CaseStatus,
    TaskType,
    TaskStatus,
)
from app.models.models import (
    Organization,
    User,
    Patient,
    Case,
    Prescription,
    Insurance,
    Task,
    FinancialClearance,
    Schedule,
    PharmacyOrder,
)
from app.main import app

# Use SQLite for testing
TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def db():
    """Create fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def provider_org(db):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Provider Org",
        type=OrgType.PROVIDER_ORG,
    )
    db.add(org)
    db.flush()
    return org


@pytest.fixture
def infusion_org(db):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Infusion Org",
        type=OrgType.INFUSION_ORG,
    )
    db.add(org)
    db.flush()
    return org


@pytest.fixture
def provider_user(db, provider_org):
    user = User(
        id=uuid.uuid4(),
        email="test-provider@example.com",
        password_hash=hash_password("password123"),
        role=UserRole.PROVIDER,
        org_id=provider_org.id,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def admin_user(db, infusion_org):
    user = User(
        id=uuid.uuid4(),
        email="test-admin@example.com",
        password_hash=hash_password("password123"),
        role=UserRole.INFUSION_ADMIN,
        org_id=infusion_org.id,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def patient(db):
    p = Patient(
        id=uuid.uuid4(),
        first_name="Test",
        last_name="Patient",
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def base_case(db, patient, provider_org, admin_user):
    case = Case(
        id=uuid.uuid4(),
        patient_id=patient.id,
        provider_org_id=provider_org.id,
        status=CaseStatus.REFERRAL_RECEIVED,
        created_by_user_id=admin_user.id,
    )
    db.add(case)
    db.flush()
    return case


@pytest.fixture
def case_with_rx_and_insurance(db, base_case):
    rx = Prescription(
        case_id=base_case.id,
        drug_name="Infliximab",
        dose="5mg/kg",
        frequency="Every 8 weeks",
        route="IV",
        diagnosis_icd10="M05.79",
    )
    ins = Insurance(
        case_id=base_case.id,
        payer_name="Test Payer",
        member_id="MEM-001",
        group_id="GRP-001",
    )
    db.add_all([rx, ins])
    db.flush()
    return base_case
