import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_role
from app.models.task import Task, TaskCategory, TaskStatus
from app.models.user import User
from app.schemas.task import ChecklistItemUpdate, TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])

_organizer_dep = Depends(require_role(["organizer"]))


def _task_to_out(task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        event_id=task.event_id,
        title=task.title,
        category=task.category.value,
        status=task.status.value,
        deadline=task.deadline,
        checklist=task.checklist or [],
        assignee_id=task.assignee_id,
        assignee=task.assignee,
        created_at=task.created_at,
    )


@router.get("/", response_model=dict)
async def list_tasks(
    event_id: uuid.UUID,
    current_user: Annotated[User, _organizer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> dict:
    """Return tasks grouped by status: { todo: [], in_progress: [], done: [] }"""
    query = (
        select(Task)
        .options(selectinload(Task.assignee))
        .where(Task.event_id == event_id)
    )
    if category:
        try:
            query = query.where(Task.category == TaskCategory(category))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid category: '{category}'")
    if status_filter:
        try:
            query = query.where(Task.status == TaskStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status: '{status_filter}'")

    result = await db.execute(query)
    tasks = result.scalars().all()

    grouped: dict[str, list] = {"todo": [], "in_progress": [], "done": []}
    for t in tasks:
        grouped[t.status.value].append(_task_to_out(t))
    return grouped


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    current_user: Annotated[User, _organizer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskOut:
    try:
        cat = TaskCategory(body.category)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid category: '{body.category}'")

    task = Task(
        event_id=body.event_id,
        title=body.title,
        category=cat,
        status=TaskStatus.todo,
        assignee_id=body.assignee_id,
        deadline=body.deadline,
        checklist=[item.model_dump() for item in body.checklist],
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    result = await db.execute(
        select(Task).options(selectinload(Task.assignee)).where(Task.id == task.id)
    )
    return _task_to_out(result.scalar_one())


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    current_user: Annotated[User, _organizer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskOut:
    result = await db.execute(
        select(Task).options(selectinload(Task.assignee)).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if body.title is not None:
        task.title = body.title
    if body.category is not None:
        try:
            task.category = TaskCategory(body.category)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid category: '{body.category}'")
    if body.status is not None:
        try:
            task.status = TaskStatus(body.status)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status: '{body.status}'")
    if body.assignee_id is not None:
        task.assignee_id = body.assignee_id
    if body.deadline is not None:
        task.deadline = body.deadline
    if body.checklist is not None:
        task.checklist = [item.model_dump() for item in body.checklist]

    await db.commit()
    await db.refresh(task)
    result2 = await db.execute(
        select(Task).options(selectinload(Task.assignee)).where(Task.id == task_id)
    )
    return _task_to_out(result2.scalar_one())


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    current_user: Annotated[User, _organizer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()


@router.patch("/{task_id}/checklist", response_model=TaskOut)
async def update_checklist_item(
    task_id: uuid.UUID,
    body: ChecklistItemUpdate,
    current_user: Annotated[User, _organizer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskOut:
    result = await db.execute(
        select(Task).options(selectinload(Task.assignee)).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    checklist = list(task.checklist or [])
    if body.index < 0 or body.index >= len(checklist):
        raise HTTPException(status_code=422, detail=f"Checklist index {body.index} out of range")

    # SQLAlchemy won't detect in-place JSONB mutation — replace the list
    checklist[body.index] = {**checklist[body.index], "done": body.done}
    task.checklist = checklist

    # Force SQLAlchemy to detect the change on a JSONB column
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(task, "checklist")

    await db.commit()
    await db.refresh(task)
    result2 = await db.execute(
        select(Task).options(selectinload(Task.assignee)).where(Task.id == task_id)
    )
    return _task_to_out(result2.scalar_one())
