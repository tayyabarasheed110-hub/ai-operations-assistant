from app.models.user import User
from app.services.users import get_user_by_email
from tests.conftest import login


def test_new_user_no_capabilities(client, admin_client, db_session):
    resp = admin_client.post(
        "/api/admin/users",
        json={"email": "newuser@assistant.test", "password": "DemoPass123!"},
    )
    assert resp.status_code == 200
    me = client.post("/api/auth/sign-in", json={"email": "newuser@assistant.test", "password": "DemoPass123!"})
    assert me.status_code == 200
    profile = client.get("/api/auth/me")
    assert profile.json()["capabilities"] == []


def test_grant_capability_without_restart(admin_client, client, db_session):
    admin_client.post(
        "/api/admin/users",
        json={"email": "capuser@assistant.test", "password": "DemoPass123!"},
    )
    login(client, "capuser@assistant.test")
    assert client.get("/api/auth/me").json()["capabilities"] == []
    user = get_user_by_email(db_session, "capuser@assistant.test")
    admin_client.post(f"/api/admin/users/{user.id}/capabilities/grant", json={"capability": "inventory:read"})
    assert "inventory:read" in client.get("/api/auth/me").json()["capabilities"]


def test_admin_cannot_deactivate_self(admin_client):
    me = admin_client.get("/api/auth/me").json()
    resp = admin_client.post(f"/api/admin/users/{me['id']}/deactivate")
    assert resp.status_code == 400


def test_thread_foreign_403(ali_client, sara_client):
    t = ali_client.post("/api/threads", json={"title": "ali thread"}).json()
    resp = sara_client.get(f"/api/threads/{t['id']}")
    assert resp.status_code == 403
