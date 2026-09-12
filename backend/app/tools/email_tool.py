import secrets
from typing import Any

from email_validator import EmailNotValidError, validate_email
from pydantic import Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.capabilities import EMAIL_SEND
from app.models.email_message import EmailMessage
from app.services.users import get_user_by_id, user_has_capability
from app.tools.base import StrictToolInput, ToolResult, audit_and_return, check_user_active

TOOL_DRAFT = "draft_email"
TOOL_EXECUTE = "execute_email"


class DraftEmailInput(StrictToolInput):
    recipient: str = Field(min_length=3, max_length=255)
    subject: str = Field(min_length=1, max_length=512)
    body: str = Field(min_length=1, max_length=20000)
    idempotency_key: str | None = Field(default=None, max_length=128)


def _validate_recipient(recipient: str) -> str:
    try:
        v = validate_email(recipient, check_deliverability=False)
        return v.normalized
    except EmailNotValidError as e:
        raise ValueError(str(e)) from e


def draft_email(
    db: Session,
    *,
    user_id: int,
    thread_id: int | None,
    recipient: str,
    subject: str,
    body: str,
    idempotency_key: str | None = None,
) -> ToolResult:
    args = {"recipient": recipient, "subject": subject, "body": body[:200]}
    inactive = check_user_active(db, user_id)
    if inactive:
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_DRAFT,
            arguments=args,
            outcome=inactive.outcome,
            thread_id=thread_id,
            result=inactive,
        )
    if not user_has_capability(db, user_id, EMAIL_SEND):
        result = ToolResult(ok=False, outcome="denied", error="Missing capability: email:send")
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_DRAFT,
            arguments=args,
            outcome="denied",
            thread_id=thread_id,
            result=result,
        )
    try:
        norm_recipient = _validate_recipient(recipient.strip())
        parsed = DraftEmailInput(recipient=norm_recipient, subject=subject.strip(), body=body)
    except Exception as e:
        result = ToolResult(ok=False, outcome="invalid", error=str(e))
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_DRAFT,
            arguments=args,
            outcome="invalid",
            thread_id=thread_id,
            result=result,
        )
    key = idempotency_key or secrets.token_urlsafe(16)
    user = get_user_by_id(db, user_id)
    pending = {
        "action_type": "email",
        "recipient": parsed.recipient,
        "subject": parsed.subject,
        "body": parsed.body,
        "sent_by": user_id,
        "sent_by_email": user.email if user else None,
        "idempotency_key": key,
    }
    result = ToolResult(ok=True, outcome="success", data={"pending": pending, "requires_approval": True})
    return audit_and_return(
        db,
        user_id=user_id,
        tool=TOOL_DRAFT,
        arguments={**args, "idempotency_key": key},
        outcome="success",
        thread_id=thread_id,
        result=result,
    )


def execute_email(
    db: Session,
    *,
    user_id: int,
    thread_id: int | None,
    recipient: str,
    subject: str,
    body: str,
    idempotency_key: str,
) -> ToolResult:
    args = {
        "recipient": recipient,
        "subject": subject,
        "body": body[:200],
        "idempotency_key": idempotency_key,
    }
    inactive = check_user_active(db, user_id)
    if inactive:
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_EXECUTE,
            arguments=args,
            outcome=inactive.outcome,
            thread_id=thread_id,
            result=inactive,
        )
    if not user_has_capability(db, user_id, EMAIL_SEND):
        result = ToolResult(ok=False, outcome="denied", error="Missing capability: email:send")
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_EXECUTE,
            arguments=args,
            outcome="denied",
            thread_id=thread_id,
            result=result,
        )
    try:
        norm_recipient = _validate_recipient(recipient.strip())
        parsed = DraftEmailInput(
            recipient=norm_recipient,
            subject=subject.strip(),
            body=body,
            idempotency_key=idempotency_key,
        )
    except Exception as e:
        result = ToolResult(ok=False, outcome="invalid", error=str(e))
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_EXECUTE,
            arguments=args,
            outcome="invalid",
            thread_id=thread_id,
            result=result,
        )
    existing = db.query(EmailMessage).filter(EmailMessage.idempotency_key == parsed.idempotency_key).first()
    if existing:
        result = ToolResult(
            ok=True,
            outcome="success",
            data={"message_id": existing.id, "duplicate": True, "recipient": existing.recipient},
        )
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_EXECUTE,
            arguments=args,
            outcome="success",
            thread_id=thread_id,
            result=result,
        )
    msg = EmailMessage(
        recipient=parsed.recipient,
        subject=parsed.subject,
        body=parsed.body,
        sent_by=user_id,
        idempotency_key=parsed.idempotency_key or idempotency_key,
    )
    db.add(msg)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(EmailMessage).filter(EmailMessage.idempotency_key == parsed.idempotency_key).first()
        if existing:
            result = ToolResult(
                ok=True,
                outcome="success",
                data={"message_id": existing.id, "duplicate": True},
            )
            return audit_and_return(
                db,
                user_id=user_id,
                tool=TOOL_EXECUTE,
                arguments=args,
                outcome="success",
                thread_id=thread_id,
                result=result,
            )
        result = ToolResult(ok=False, outcome="error", error="Failed to send email")
        return audit_and_return(
            db,
            user_id=user_id,
            tool=TOOL_EXECUTE,
            arguments=args,
            outcome="error",
            thread_id=thread_id,
            result=result,
        )
    db.refresh(msg)
    print(
        f"[MOCK EMAIL] to={msg.recipient} subject={msg.subject!r} body={msg.body[:120]!r} "
        f"by user_id={user_id}"
    )
    result = ToolResult(
        ok=True,
        outcome="success",
        data={"message_id": msg.id, "recipient": msg.recipient, "duplicate": False},
    )
    return audit_and_return(
        db,
        user_id=user_id,
        tool=TOOL_EXECUTE,
        arguments=args,
        outcome="success",
        thread_id=thread_id,
        result=result,
    )


def draft_email_from_raw(db: Session, user_id: int, raw: dict[str, Any], thread_id: int | None) -> ToolResult:
    return draft_email(
        db,
        user_id=user_id,
        thread_id=thread_id,
        recipient=raw.get("recipient", ""),
        subject=raw.get("subject", ""),
        body=raw.get("body", ""),
        idempotency_key=raw.get("idempotency_key"),
    )


def execute_email_from_raw(db: Session, user_id: int, raw: dict[str, Any], thread_id: int | None) -> ToolResult:
    return execute_email(
        db,
        user_id=user_id,
        thread_id=thread_id,
        recipient=raw.get("recipient", ""),
        subject=raw.get("subject", ""),
        body=raw.get("body", ""),
        idempotency_key=raw.get("idempotency_key", ""),
    )
