import re
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.document import Document, DocumentChunk
from app.retrieval.chroma_store import delete_chunks, upsert_chunks
from app.utils.sanitize import strip_html_and_scripts

_SECTION_RE = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[tuple[str, str]]:
    cleaned = strip_html_and_scripts(text)
    if not cleaned:
        return []
    sections = _SECTION_RE.findall(cleaned)
    default_section = sections[0] if sections else "section 1"
    chunks: list[tuple[str, str]] = []
    start = 0
    idx = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        piece = cleaned[start:end]
        section = default_section if idx == 0 else f"{default_section} (cont.)"
        chunks.append((piece, section))
        if end >= len(cleaned):
            break
        start = max(0, end - overlap)
        idx += 1
    return chunks


def index_document(
    db: Session,
    *,
    title: str,
    filename: str,
    raw_bytes: bytes,
    uploaded_by: int,
) -> Document:
    settings = get_settings()
    if len(raw_bytes) > settings.upload_max_bytes:
        raise ValueError("Upload exceeds size limit")
    text = raw_bytes.decode("utf-8", errors="ignore")
    doc = Document(title=title, filename=filename, uploaded_by=uploaded_by)
    db.add(doc)
    db.flush()
    pieces = _chunk_text(text, settings.chunk_size, settings.chunk_overlap)
    chroma_ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []
    for i, (content, section) in enumerate(pieces):
        cid = f"doc-{doc.id}-{uuid.uuid4().hex}"
        chroma_ids.append(cid)
        documents.append(content)
        metadatas.append({"title": title, "page_or_section": section, "document_id": doc.id})
        db.add(
            DocumentChunk(
                document_id=doc.id,
                chunk_index=i,
                content=content,
                page_or_section=section,
                chroma_id=cid,
            )
        )
    if chroma_ids:
        upsert_chunks(chroma_ids=chroma_ids, documents=documents, metadatas=metadatas)
    db.commit()
    db.refresh(doc)
    return doc


def delete_document(db: Session, document_id: int) -> None:
    doc = db.get(Document, document_id)
    if not doc:
        return
    ids = [c.chroma_id for c in doc.chunks]
    delete_chunks(ids)
    db.delete(doc)
    db.commit()
