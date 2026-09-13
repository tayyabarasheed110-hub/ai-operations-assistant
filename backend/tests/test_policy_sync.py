from app.models.document import Document
from app.services.policy_sync import POLICY_SOURCE_PREFIX, sync_policy_docs_from_disk
from app.services.users import get_user_by_email


def test_sync_policy_docs_idempotent(db_session):
    admin = get_user_by_email(db_session, "admin@assistant.test")
    first = sync_policy_docs_from_disk(db_session, uploaded_by=admin.id)
    second = sync_policy_docs_from_disk(db_session, uploaded_by=admin.id)
    assert len(first) >= 1
    assert second == []
    count = db_session.query(Document).filter(Document.filename.like(f"{POLICY_SOURCE_PREFIX}%")).count()
    assert count == len(first)
