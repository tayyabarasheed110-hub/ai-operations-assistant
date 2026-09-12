import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Must set before app imports that read settings
_test_root = Path(__file__).resolve().parents[1] / "test_data"
_test_root.mkdir(exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{(_test_root / 'test.db').as_posix()}"
os.environ["CHROMA_PATH"] = str(_test_root / "chroma")
os.environ["JWT_SECRET"] = "test-secret"
os.environ["EMBEDDING_MODE"] = "test"

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
import seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed.seed()
    yield


@pytest.fixture()
def db_session():
    engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(client: TestClient, email: str, password: str = "DemoPass123!"):
    return client.post("/api/auth/sign-in", json={"email": email, "password": password})


@pytest.fixture()
def ali_client(client):
    login(client, "ali@assistant.test")
    return client


@pytest.fixture()
def sara_client(client):
    login(client, "sara@assistant.test")
    return client


@pytest.fixture()
def admin_client(client):
    login(client, "admin@assistant.test")
    return client
