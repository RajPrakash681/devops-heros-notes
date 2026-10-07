from sqlalchemy.exc import OperationalError

from app.db import get_db
from app.main import app


def test_health(client):
    assert client.get("/health").json() == {"status": "UP"}


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "TaskBoard API"


def test_ready_when_database_is_reachable(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "READY"}


def test_ready_returns_503_when_database_is_down(client):
    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    app.dependency_overrides[get_db] = lambda: BrokenSession()
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "NOT_READY"


def test_info_reports_build_and_environment(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "git_sha", "abc1234")
    monkeypatch.setattr(settings, "app_env", "test")
    body = client.get("/api/info").json()
    assert body["git_sha"] == "abc1234"
    assert body["environment"] == "test"
    assert body["pod"]


def test_create_task_returns_201_with_defaults(client):
    response = client.post("/api/tasks", json={"title": "Deploy application", "priority": "HIGH"})
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Deploy application"
    assert body["priority"] == "HIGH"
    assert body["status"] == "TODO"
    assert body["assignee"] == "Unassigned"
    assert isinstance(body["id"], int)


def test_create_task_rejects_empty_title(client):
    assert client.post("/api/tasks", json={"title": ""}).status_code == 422


def test_create_task_rejects_unknown_priority(client):
    assert client.post("/api/tasks", json={"title": "x", "priority": "URGENT"}).status_code == 422


def test_list_tasks_newest_first(client, make_task):
    first = make_task(title="first")
    second = make_task(title="second")
    ids = [t["id"] for t in client.get("/api/tasks").json()]
    assert ids == [second["id"], first["id"]]


def test_get_task_by_id_and_404(client, make_task):
    task = make_task(title="find me")
    assert client.get(f"/api/tasks/{task['id']}").json()["title"] == "find me"
    assert client.get("/api/tasks/99999").status_code == 404


def test_update_task_changes_only_sent_fields(client, make_task):
    task = make_task(title="ship it", assignee="Raj")
    response = client.put(f"/api/tasks/{task['id']}", json={"status": "IN_PROGRESS"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "IN_PROGRESS"
    assert body["title"] == "ship it"
    assert body["assignee"] == "Raj"


def test_update_rejects_invalid_status(client, make_task):
    task = make_task()
    assert client.put(f"/api/tasks/{task['id']}", json={"status": "BLOCKED"}).status_code == 422


def test_update_missing_task_returns_404(client):
    assert client.put("/api/tasks/424242", json={"status": "DONE"}).status_code == 404


def test_delete_task_then_it_is_gone(client, make_task):
    task = make_task()
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 204
    assert client.get(f"/api/tasks/{task['id']}").status_code == 404
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 404


def test_stats_counts_by_status(client, make_task):
    make_task(status="TODO")
    make_task(status="TODO")
    make_task(status="IN_PROGRESS")
    make_task(status="DONE")
    assert client.get("/api/tasks/stats").json() == {"total": 4, "todo": 2, "inProgress": 1, "done": 1}


def test_metrics_endpoint_counts_api_requests(client, make_task):
    make_task()
    client.get("/api/tasks")
    text = client.get("/metrics").text
    assert "http_requests_total" in text
    assert 'handler="/api/tasks"' in text
