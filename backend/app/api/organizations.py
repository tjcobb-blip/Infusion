from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Organization, User
from app.schemas.schemas import OrgResponse

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("", response_model=list[OrgResponse])
def list_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Organization).order_by(Organization.name).all()
