import logging

from app.config import Settings
from app.main import QuietProbes


def test_database_url_is_built_from_parts_and_escapes_the_password():
    s = Settings(database_url=None, db_host="pg", db_port=5432, db_name="tb", db_user="u", db_password="p@ss/w:rd")
    assert s.sqlalchemy_url == "postgresql+psycopg://u:p%40ss%2Fw%3Ard@pg:5432/tb"


def test_database_url_override_wins():
    s = Settings(database_url="sqlite:///x.db", db_host="ignored")
    assert s.sqlalchemy_url == "sqlite:///x.db"


def _access_record(path):
    return logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1,
                             '%s - "%s %s HTTP/%s" %d', ("10.0.0.1:1234", "GET", path, "1.1", 200), None)


def test_probe_and_scrape_requests_are_dropped_from_the_access_log():
    f = QuietProbes()
    assert not f.filter(_access_record("/health"))
    assert not f.filter(_access_record("/ready"))
    assert not f.filter(_access_record("/metrics"))
    assert f.filter(_access_record("/api/tasks"))
