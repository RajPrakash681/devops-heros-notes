import os
import tempfile

# Must happen before `app` is imported: the engine is created from this URL at import
# time. Each test run gets its own throwaway SQLite file - never the real PostgreSQL.
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp(prefix='taskboard-test-')}/test.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    # In production Alembic owns the schema; in tests the models create it directly,
    # and every test starts from empty tables.
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def make_task(client):
    def _make(**fields):
        body = {"title": "Write the runbook", **fields}
        response = client.post("/api/tasks", json=body)
        assert response.status_code == 201, response.text
        return response.json()

    return _make
