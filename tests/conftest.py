import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_service import AIServiceError  # noqa: E402
from database import get_session  # noqa: E402
from main import app, get_reviewer  # noqa: E402


class FakeReviewer:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls = []

    def analyze_code(self, code: str, language: str) -> dict:
        self.calls.append((code, language))
        if self.fail:
            raise AIServiceError("boom")
        return {"security_status": "High Risk", "ai_feedback": "Use parameterized queries."}


@pytest.fixture
def reviewer():
    return FakeReviewer()


@pytest.fixture
def client(reviewer, monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_reviewer] = lambda: reviewer
    # No `with` block: the startup hook (which touches the real DB) is not run.
    yield TestClient(app)
    app.dependency_overrides.clear()
