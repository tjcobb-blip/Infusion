from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Case, Task, User, TimelineEvent, AuditLog
from app.schemas.schemas import TaskCreate, TaskUpdate, TaskResponse

router = APIRouter(tags=["tasks"])


@router.post(
    "/cases/{case_id}/tasks", response_model=TaskResponse, status_code=201
)
def create_task(
    case_id: UUID,
    body: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    task = Task(
        case_id=case_id,
        type=body.type,
        owner_user_id=body.owner_user_id,
        due_at=body.due_at,
        payload_json=body.payload_json or {},
    )
    db.add(task)

    event = TimelineEvent(
        case_id=case_id,
        event_type="TASK_CREATED",
        actor_user_id=current_user.id,
        metadata_json={"task_type": body.type.value},
    )
    db.add(event)
    db.commit()
    db.refresh(task)
    return task


@router.get("/cases/{case_id}/tasks", response_model=list[TaskResponse])
def list_tasks(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    tasks = (
        db.query(Task)
        .filter(Task.case_id == case_id)
        .order_by(Task.created_at.desc())
        .all()
    )
    return tasks


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    body: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    event = TimelineEvent(
        case_id=task.case_id,
        event_type="TASK_UPDATED",
        actor_user_id=current_user.id,
        metadata_json={
            "task_id": str(task_id),
            "updates": body.model_dump(exclude_unset=True),
        },
    )
    db.add(event)

    audit = AuditLog(
        actor_user_id=current_user.id,
        action="TASK_UPDATED",
        entity_type="task",
        entity_id=task_id,
        metadata_json=body.model_dump(exclude_unset=True),
    )
    db.add(audit)
    db.commit()
    db.refresh(task)
    return task
