from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.runner import resume_thread, run_message_stream, sse_from_iterator
from app.auth.deps import get_current_user
from app.db.session import get_db
from app.models.thread import Thread
from app.models.user import User

router = APIRouter(prefix="/api/threads", tags=["threads"])


class CreateThreadBody(BaseModel):
    title: str = Field(default="New conversation", max_length=512)


class MessageBody(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class ResumeBody(BaseModel):
    decision: str = Field(pattern="^(approve|edit|reject)$")
    edits: dict | None = None


def _get_owned_thread(db: Session, thread_id: int, user: User) -> Thread:
    thread = db.get(Thread, thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    if thread.owner_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return thread


@router.post("")
def create_thread(body: CreateThreadBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    thread = Thread(owner_user_id=user.id, title=body.title)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return {"id": thread.id, "title": thread.title}


@router.get("")
def list_threads(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(Thread)
        .filter(Thread.owner_user_id == user.id)
        .order_by(Thread.updated_at.desc())
        .all()
    )
    return [{"id": t.id, "title": t.title, "updated_at": t.updated_at.isoformat()} for t in rows]


@router.get("/{thread_id}")
def get_thread(thread_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    thread = _get_owned_thread(db, thread_id, user)
    return {"id": thread.id, "title": thread.title, "owner_user_id": thread.owner_user_id}


@router.post("/{thread_id}/messages/stream")
async def stream_message(
    thread_id: int,
    body: MessageBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_thread(db, thread_id, user)
    events = run_message_stream(thread_id=thread_id, user_id=user.id, content=body.content)
    return StreamingResponse(sse_from_iterator(events), media_type="text/event-stream")


@router.post("/{thread_id}/resume")
async def resume(
    thread_id: int,
    body: ResumeBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_thread(db, thread_id, user)
    if body.decision == "reject":
        decision = "reject"
        edits = None
    elif body.decision == "edit":
        decision = "approve"
        edits = body.edits or {}
    else:
        decision = "approve"
        edits = body.edits
    events = resume_thread(thread_id=thread_id, decision=decision, edits=edits)
    return StreamingResponse(sse_from_iterator(events), media_type="text/event-stream")
