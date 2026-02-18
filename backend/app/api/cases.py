from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.enums import UserRole, CaseStatus
from app.models.models import (
    Case,
    Patient,
    Prescription,
    Insurance,
    User,
    TimelineEvent,
    AuditLog,
)
from app.schemas.schemas import (
    CaseCreate,
    CaseSummaryResponse,
    CaseDetailResponse,
    CaseStatusUpdate,
    AssignInfusionOrg,
    PatientCreate,
    PatientResponse,
    PrescriptionUpdate,
    PrescriptionResponse,
    InsuranceUpdate,
    InsuranceResponse,
    TimelineEventResponse,
    BlockerResponse,
)
from app.services.workflow import transition_case, TransitionError, get_case_blockers

router = APIRouter(prefix="/cases", tags=["cases"])


def _get_case_or_404(db: Session, case_id: UUID) -> Case:
    case = (
        db.query(Case)
        .options(
            joinedload(Case.patient),
            joinedload(Case.prescription),
            joinedload(Case.insurance),
        )
        .filter(Case.id == case_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


def _check_case_access(case: Case, user: User):
    """Ensure user's org can see this case."""
    if user.role == UserRole.PROVIDER and case.provider_org_id != user.org_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    if (
        user.role == UserRole.INFUSION_ADMIN
        and case.infusion_org_id is not None
        and case.infusion_org_id != user.org_id
    ):
        raise HTTPException(status_code=403, detail="Access denied.")


@router.post("", response_model=CaseSummaryResponse, status_code=201)
def create_case(
    body: CaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = None
    if body.patient_id:
        patient = db.query(Patient).filter(Patient.id == body.patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found.")
    elif body.patient:
        patient = Patient(**body.patient.model_dump())
        db.add(patient)
        db.flush()

    case = Case(
        patient_id=patient.id if patient else None,
        provider_org_id=current_user.org_id,
        status=CaseStatus.REFERRAL_RECEIVED,
        created_by_user_id=current_user.id,
    )
    db.add(case)
    db.flush()

    # Create timeline event
    event = TimelineEvent(
        case_id=case.id,
        event_type="CASE_CREATED",
        actor_user_id=current_user.id,
        metadata_json={"status": CaseStatus.REFERRAL_RECEIVED.value},
    )
    db.add(event)

    # Audit log
    audit = AuditLog(
        actor_user_id=current_user.id,
        action="CASE_CREATED",
        entity_type="case",
        entity_id=case.id,
    )
    db.add(audit)

    db.commit()
    db.refresh(case)
    return case


@router.get("", response_model=list[CaseSummaryResponse])
def list_cases(
    status_filter: CaseStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Case).options(joinedload(Case.patient))

    if current_user.role == UserRole.PROVIDER:
        query = query.filter(Case.provider_org_id == current_user.org_id)
    elif current_user.role == UserRole.INFUSION_ADMIN:
        # Infusion admins see cases assigned to their org OR unassigned
        query = query.filter(
            (Case.infusion_org_id == current_user.org_id)
            | (Case.infusion_org_id.is_(None))
        )

    if status_filter:
        query = query.filter(Case.status == status_filter)

    return query.order_by(Case.created_at.desc()).all()


@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_case_or_404(db, case_id)
    _check_case_access(case, current_user)
    return case


@router.patch("/{case_id}/status", response_model=CaseDetailResponse)
def update_case_status(
    case_id: UUID,
    body: CaseStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_case_or_404(db, case_id)
    _check_case_access(case, current_user)
    try:
        case = transition_case(db, case, body.new_status, current_user.id)
        db.commit()
        db.refresh(case)
        return case
    except TransitionError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/{case_id}/assign-infusion-org", response_model=CaseDetailResponse)
def assign_infusion_org(
    case_id: UUID,
    body: AssignInfusionOrg,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.INFUSION_ADMIN:
        raise HTTPException(status_code=403, detail="Only infusion admins can assign.")
    case = _get_case_or_404(db, case_id)
    case.infusion_org_id = body.infusion_org_id
    event = TimelineEvent(
        case_id=case.id,
        event_type="INFUSION_ORG_ASSIGNED",
        actor_user_id=current_user.id,
        metadata_json={"infusion_org_id": str(body.infusion_org_id)},
    )
    db.add(event)
    db.commit()
    db.refresh(case)
    return case


# ── Patient ───────────────────────────────────────────────────────────────────
@router.post("/{case_id}/patient", response_model=PatientResponse, status_code=201)
def create_or_attach_patient(
    case_id: UUID,
    body: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_case_or_404(db, case_id)
    _check_case_access(case, current_user)
    patient = Patient(**body.model_dump())
    db.add(patient)
    db.flush()
    case.patient_id = patient.id
    event = TimelineEvent(
        case_id=case.id,
        event_type="PATIENT_ATTACHED",
        actor_user_id=current_user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(patient)
    return patient


# ── Prescription ──────────────────────────────────────────────────────────────
@router.patch("/{case_id}/prescription", response_model=PrescriptionResponse)
def update_prescription(
    case_id: UUID,
    body: PrescriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_case_or_404(db, case_id)
    _check_case_access(case, current_user)

    rx = db.query(Prescription).filter(Prescription.case_id == case_id).first()
    if not rx:
        rx = Prescription(case_id=case_id)
        db.add(rx)
        db.flush()

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(rx, field, value)

    event = TimelineEvent(
        case_id=case.id,
        event_type="PRESCRIPTION_UPDATED",
        actor_user_id=current_user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(rx)
    return rx


# ── Insurance ─────────────────────────────────────────────────────────────────
@router.patch("/{case_id}/insurance", response_model=InsuranceResponse)
def update_insurance(
    case_id: UUID,
    body: InsuranceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_case_or_404(db, case_id)
    _check_case_access(case, current_user)

    ins = db.query(Insurance).filter(Insurance.case_id == case_id).first()
    if not ins:
        ins = Insurance(case_id=case_id)
        db.add(ins)
        db.flush()

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(ins, field, value)

    event = TimelineEvent(
        case_id=case.id,
        event_type="INSURANCE_UPDATED",
        actor_user_id=current_user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(ins)
    return ins


# ── Timeline ─────────────────────────────────────────────────────────────────
@router.get("/{case_id}/timeline", response_model=list[TimelineEventResponse])
def get_timeline(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_case_or_404(db, case_id)
    _check_case_access(case, current_user)
    events = (
        db.query(TimelineEvent)
        .filter(TimelineEvent.case_id == case_id)
        .order_by(TimelineEvent.created_at.desc())
        .all()
    )
    return events


# ── Blockers ─────────────────────────────────────────────────────────────────
@router.get("/{case_id}/blockers", response_model=list[BlockerResponse])
def get_blockers(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_case_or_404(db, case_id)
    _check_case_access(case, current_user)
    return get_case_blockers(db, case)
