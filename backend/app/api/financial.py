from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Case, FinancialClearance, User, TimelineEvent
from app.schemas.schemas import FinancialClearanceUpdate, FinancialClearanceResponse

router = APIRouter(
    prefix="/cases/{case_id}/financial", tags=["financial"]
)


@router.get("", response_model=FinancialClearanceResponse | None)
def get_financial_clearance(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    fc = (
        db.query(FinancialClearance)
        .filter(FinancialClearance.case_id == case_id)
        .first()
    )
    return fc


@router.patch("", response_model=FinancialClearanceResponse)
def update_financial_clearance(
    case_id: UUID,
    body: FinancialClearanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    fc = (
        db.query(FinancialClearance)
        .filter(FinancialClearance.case_id == case_id)
        .first()
    )
    if not fc:
        fc = FinancialClearance(case_id=case_id)
        db.add(fc)
        db.flush()

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(fc, field, value)

    event = TimelineEvent(
        case_id=case_id,
        event_type="FINANCIAL_UPDATED",
        actor_user_id=current_user.id,
        metadata_json=body.model_dump(exclude_unset=True, mode="json"),
    )
    db.add(event)
    db.commit()
    db.refresh(fc)
    return fc
