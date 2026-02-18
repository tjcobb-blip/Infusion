from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.enums import FulfillmentStatus
from app.models.models import Case, PharmacyOrder, User, TimelineEvent, AuditLog
from app.schemas.schemas import (
    PharmacyPushCreate,
    PharmacyOrderUpdate,
    PharmacyOrderResponse,
)

router = APIRouter(prefix="/cases/{case_id}/pharmacy-push", tags=["pharmacy"])


@router.post("", response_model=PharmacyOrderResponse, status_code=201)
def pharmacy_push(
    case_id: UUID,
    body: PharmacyPushCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    existing = (
        db.query(PharmacyOrder)
        .filter(PharmacyOrder.case_id == case_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Pharmacy order already exists for this case."
        )

    order = PharmacyOrder(
        case_id=case_id,
        pushed_at=datetime.now(timezone.utc),
        ship_to=body.ship_to,
        requested_arrival_date=body.requested_arrival_date,
        pharmacy_notes=body.pharmacy_notes,
        fulfillment_status=FulfillmentStatus.NOT_STARTED,
    )
    db.add(order)

    event = TimelineEvent(
        case_id=case_id,
        event_type="PHARMACY_PUSHED",
        actor_user_id=current_user.id,
        metadata_json={"ship_to": body.ship_to},
    )
    db.add(event)

    audit = AuditLog(
        actor_user_id=current_user.id,
        action="PHARMACY_PUSHED",
        entity_type="pharmacy_order",
        entity_id=case_id,
    )
    db.add(audit)
    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=PharmacyOrderResponse | None)
def get_pharmacy_order(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    order = (
        db.query(PharmacyOrder)
        .filter(PharmacyOrder.case_id == case_id)
        .first()
    )
    return order


@router.patch("", response_model=PharmacyOrderResponse)
def update_pharmacy_order(
    case_id: UUID,
    body: PharmacyOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = (
        db.query(PharmacyOrder)
        .filter(PharmacyOrder.case_id == case_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Pharmacy order not found.")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(order, field, value)

    event = TimelineEvent(
        case_id=case_id,
        event_type="PHARMACY_ORDER_UPDATED",
        actor_user_id=current_user.id,
        metadata_json=body.model_dump(exclude_unset=True, mode="json"),
    )
    db.add(event)
    db.commit()
    db.refresh(order)
    return order
