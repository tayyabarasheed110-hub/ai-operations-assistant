from app.models.audit import AuditLog
from app.models.order import Order
from app.services.users import get_user_by_email
from app.tools.email_tool import draft_email, execute_email
from app.tools.lookup_inventory import lookup_inventory
from app.tools.orders import draft_order, execute_order
from app.tools.registry import invoke_read_tool


def test_sku_1043_quantity(db_session):
    user = get_user_by_email(db_session, "ali@assistant.test")
    result = lookup_inventory(db_session, user_id=user.id, thread_id=None, sku="SKU-1043")
    assert result.ok
    assert result.data["quantity"] == 120


def test_unknown_sku(db_session):
    user = get_user_by_email(db_session, "ali@assistant.test")
    result = lookup_inventory(db_session, user_id=user.id, thread_id=None, sku="SKU-9999")
    assert not result.ok
    assert result.outcome == "not_found"


def test_ali_cannot_order_or_email_direct(db_session):
    user = get_user_by_email(db_session, "ali@assistant.test")
    order = draft_order(
        db_session,
        user_id=user.id,
        thread_id=None,
        sku="SKU-1043",
        quantity=1,
        supplier="RetailPrint",
    )
    assert not order.ok and order.outcome == "denied"
    email = draft_email(
        db_session,
        user_id=user.id,
        thread_id=None,
        recipient="x@example.com",
        subject="hi",
        body="body",
    )
    assert not email.ok and email.outcome == "denied"


def test_sara_can_order_not_email(db_session):
    user = get_user_by_email(db_session, "sara@assistant.test")
    order = draft_order(
        db_session,
        user_id=user.id,
        thread_id=None,
        sku="SKU-1043",
        quantity=2,
        supplier="RetailPrint",
    )
    assert order.ok
    email = draft_email(
        db_session,
        user_id=user.id,
        thread_id=None,
        recipient="x@example.com",
        subject="hi",
        body="body",
    )
    assert not email.ok and email.outcome == "denied"


def test_dave_denied(db_session):
    user = get_user_by_email(db_session, "dave@assistant.test")
    assert not lookup_inventory(db_session, user_id=user.id, thread_id=None, sku="SKU-1043").ok


def test_audit_on_denied(db_session):
    user = get_user_by_email(db_session, "dave@assistant.test")
    before = db_session.query(AuditLog).count()
    lookup_inventory(db_session, user_id=user.id, thread_id=None, sku="SKU-1043")
    after = db_session.query(AuditLog).count()
    assert after == before + 1


def test_idempotent_order(db_session):
    user = get_user_by_email(db_session, "sara@assistant.test")
    key = "test-key-001"
    first = execute_order(
        db_session,
        user_id=user.id,
        thread_id=None,
        sku="SKU-1043",
        quantity=3,
        supplier="RetailPrint",
        idempotency_key=key,
    )
    second = execute_order(
        db_session,
        user_id=user.id,
        thread_id=None,
        sku="SKU-1043",
        quantity=3,
        supplier="RetailPrint",
        idempotency_key=key,
    )
    assert first.ok and second.ok
    assert db_session.query(Order).filter(Order.idempotency_key == key).count() == 1


def test_unknown_tool_audited(db_session):
    user = get_user_by_email(db_session, "admin@assistant.test")
    before = db_session.query(AuditLog).count()
    result = invoke_read_tool(db_session, "create_order", user.id, {}, None)
    assert not result.ok
    assert db_session.query(AuditLog).count() == before + 1


def test_user_id_spoof_execute_still_checks_session_user(db_session):
    sara = get_user_by_email(db_session, "sara@assistant.test")
    ali = get_user_by_email(db_session, "ali@assistant.test")
    # Caller passes ali's id but supplies sara-capable operation — must use explicit user_id param
    result = execute_order(
        db_session,
        user_id=ali.id,
        thread_id=None,
        sku="SKU-1043",
        quantity=1,
        supplier="RetailPrint",
        idempotency_key="spoof-key",
    )
    assert not result.ok and result.outcome == "denied"
    # Even if arguments pretend to be sara, tool uses user_id parameter only
    result2 = execute_order(
        db_session,
        user_id=sara.id,
        thread_id=None,
        sku="SKU-1043",
        quantity=1,
        supplier="RetailPrint",
        idempotency_key="spoof-key-2",
    )
    assert result2.ok
