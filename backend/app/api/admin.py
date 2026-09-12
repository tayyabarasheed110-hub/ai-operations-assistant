from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.auth.deps import require_admin
from app.auth.passwords import hash_password
from app.capabilities import ALL_CAPABILITIES
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.document import Document
from app.models.email_message import EmailMessage
from app.models.order import Order
from app.models.user import User, UserCapability
from app.services.documents import delete_document, index_document
from app.services.users import get_user_by_email

router = APIRouter(prefix="/api/admin", tags=["admin"])


class CreateUserBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class CapabilityBody(BaseModel):
    capability: str


@router.get("/users")
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    users = db.query(User).order_by(User.email).all()
    out = []
    for u in users:
        caps = [c.capability for c in u.capabilities]
        out.append({"id": u.id, "email": u.email, "is_admin": u.is_admin, "is_active": u.is_active, "capabilities": caps})
    return out


@router.post("/users")
def create_user(body: CreateUserBody, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    if get_user_by_email(db, body.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email exists")
    user = User(email=body.email, password_hash=hash_password(body.password), is_admin=False, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email}


@router.post("/users/{user_id}/deactivate")
def deactivate_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate self")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = False
    db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/reactivate")
def reactivate_user(user_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = True
    db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/capabilities/grant")
def grant_capability(
    user_id: int,
    body: CapabilityBody,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if body.capability not in ALL_CAPABILITIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown capability")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    exists = (
        db.query(UserCapability)
        .filter(UserCapability.user_id == user_id, UserCapability.capability == body.capability)
        .first()
    )
    if not exists:
        db.add(UserCapability(user_id=user_id, capability=body.capability))
        db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/capabilities/revoke")
def revoke_capability(
    user_id: int,
    body: CapabilityBody,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if body.capability not in ALL_CAPABILITIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown capability")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    row = (
        db.query(UserCapability)
        .filter(UserCapability.user_id == user_id, UserCapability.capability == body.capability)
        .first()
    )
    if row:
        db.delete(row)
        db.commit()
    return {"ok": True}


@router.get("/documents")
def list_documents(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [{"id": d.id, "title": d.title, "filename": d.filename, "created_at": d.created_at.isoformat()} for d in docs]


@router.post("/documents")
async def upload_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    raw = await file.read()
    try:
        doc = index_document(
            db,
            title=title,
            filename=file.filename or "upload.md",
            raw_bytes=raw,
            uploaded_by=admin.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return {"id": doc.id, "title": doc.title}


@router.delete("/documents/{document_id}")
def remove_document(document_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    delete_document(db, document_id)
    return {"ok": True}


@router.get("/activity")
def activity(kind: str = "audit", db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    if kind == "orders":
        rows = db.query(Order).order_by(Order.created_at.desc()).limit(200).all()
        return [
            {
                "order_reference": r.order_reference,
                "sku": r.sku,
                "quantity": r.quantity,
                "requested_by": r.requested_by,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    if kind == "emails":
        rows = db.query(EmailMessage).order_by(EmailMessage.sent_at.desc()).limit(200).all()
        return [
            {
                "recipient": r.recipient,
                "subject": r.subject,
                "sent_by": r.sent_by,
                "sent_at": r.sent_at.isoformat(),
            }
            for r in rows
        ]
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(500).all()
    return [
        {
            "user_id": r.user_id,
            "tool": r.tool,
            "arguments_json": r.arguments_json,
            "outcome": r.outcome,
            "thread_id": r.thread_id,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
