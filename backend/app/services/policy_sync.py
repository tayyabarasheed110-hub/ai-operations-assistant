"""Index policy markdown from disk into DB + Chroma (one-time per file via seed)."""

import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.document import Document
from app.services.documents import delete_document, index_document

# Stable Document.filename values — used for idempotent seed sync.
POLICY_SOURCE_PREFIX = "policy_docs/"

_TITLE_OVERRIDES: dict[str, str] = {
    "leave_policy.md": "Leave Policy",
    "expense_reimbursement_policy.md": "Expense Reimbursement Policy",
    "procurement_policy.md": "Procurement Policy",
}

_PLACEHOLDER_RE = re.compile(r"\[TBD:", re.IGNORECASE)
_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _title_for_file(path: Path, raw: str) -> str:
    if path.name in _TITLE_OVERRIDES:
        return _TITLE_OVERRIDES[path.name]
    m = _HEADING_RE.search(raw)
    if m:
        return m.group(1).strip()
    return path.stem.replace("_", " ").title()


def _is_indexable(raw: str) -> bool:
    if not raw.strip():
        return False
    if _PLACEHOLDER_RE.search(raw):
        return False
    return True


def sync_policy_docs_from_disk(db: Session, *, uploaded_by: int) -> list[str]:
    """
    Index each *.md under policy_docs_dir once (skip if Document.filename already exists).
    Returns list of filenames newly indexed.
    """
    settings = get_settings()
    policy_dir = settings.policy_docs_dir
    if not policy_dir.is_dir():
        return []

    indexed: list[str] = []
    for path in sorted(policy_dir.glob("*.md")):
        stable_name = f"{POLICY_SOURCE_PREFIX}{path.name}"
        if db.query(Document).filter(Document.filename == stable_name).first():
            continue
        raw = path.read_text(encoding="utf-8")
        if not _is_indexable(raw):
            continue
        title = _title_for_file(path, raw)
        index_document(
            db,
            title=title,
            filename=stable_name,
            raw_bytes=raw.encode("utf-8"),
            uploaded_by=uploaded_by,
        )
        indexed.append(path.name)
    return indexed


def resync_policy_doc(db: Session, *, filename: str, uploaded_by: int) -> Document | None:
    """Replace a single disk policy in the index (admin/dev helper)."""
    settings = get_settings()
    path = settings.policy_docs_dir / filename
    if not path.is_file():
        return None
    stable_name = f"{POLICY_SOURCE_PREFIX}{path.name}"
    existing = db.query(Document).filter(Document.filename == stable_name).first()
    if existing:
        delete_document(db, existing.id)
    raw = path.read_text(encoding="utf-8")
    if not _is_indexable(raw):
        return None
    return index_document(
        db,
        title=_title_for_file(path, raw),
        filename=stable_name,
        raw_bytes=raw.encode("utf-8"),
        uploaded_by=uploaded_by,
    )
