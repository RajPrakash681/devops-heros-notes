import pytest

from app.server import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_calc(client):
    resp = client.get("/calc?a=10&op=multiply&b=5")
    assert resp.status_code == 200
    assert resp.get_json()["result"] == 50


def test_calc_bad_input_is_a_400_not_a_500(client):
    assert client.get("/calc?a=10&op=divide&b=0").status_code == 400
    assert client.get("/calc?a=10").status_code == 400
    assert client.get("/calc?a=ten&b=5").status_code == 400
