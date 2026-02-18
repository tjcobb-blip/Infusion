from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Case, Document, User, TimelineEvent
from app.schemas.schemas import DocumentResponse

router = APIRouter(prefix="/cases/{case_id}/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=201)
def upload_document(
    case_id: UUID,
    file_name: str = Form(...),
    file_type: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    # MVP: store metadata only; actual file storage would use S3/GCS
    doc = Document(
        case_id=case_id,
        file_name=file_name,
        file_type=file_type,
        storage_url=f"/uploads/{case_id}/{file_name}",
        uploaded_by_user_id=current_user.id,
    )
    db.add(doc)

    event = TimelineEvent(
        case_id=case_id,
        event_type="DOCUMENT_UPLOADED",
        actor_user_id=current_user.id,
        metadata_json={"file_name": file_name},
    )
    db.add(event)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    docs = (
        db.query(Document)
        .filter(Document.case_id == case_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return docs
