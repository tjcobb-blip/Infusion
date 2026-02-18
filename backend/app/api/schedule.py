from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Case, Schedule, User, TimelineEvent
from app.schemas.schemas import ScheduleCreate, ScheduleResponse

router = APIRouter(prefix="/cases/{case_id}/schedule", tags=["schedule"])


@router.post("", response_model=ScheduleResponse, status_code=201)
def create_schedule(
    case_id: UUID,
    body: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    existing = db.query(Schedule).filter(Schedule.case_id == case_id).first()
    if existing:
        # Update existing schedule
        existing.date_time = body.date_time
        existing.location = body.location
        existing.duration_minutes = body.duration_minutes
        schedule = existing
    else:
        schedule = Schedule(
            case_id=case_id,
            date_time=body.date_time,
            location=body.location,
            duration_minutes=body.duration_minutes,
        )
        db.add(schedule)

    event = TimelineEvent(
        case_id=case_id,
        event_type="SCHEDULE_SET",
        actor_user_id=current_user.id,
        metadata_json={
            "date_time": body.date_time.isoformat(),
            "location": body.location,
        },
    )
    db.add(event)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.get("", response_model=ScheduleResponse | None)
def get_schedule(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    schedule = db.query(Schedule).filter(Schedule.case_id == case_id).first()
    return schedule
