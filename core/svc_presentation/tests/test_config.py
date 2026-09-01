"""`config.Config` -- `_build_db_url` branches + `from_env()` env-var wiring."""

from __future__ import annotations

import pytest

from config import Config, _build_db_url


def test_build_db_url_sqlite_ignores_host_port_credentials() -> None:
    url = _build_db_url(
        db_type="sqlite", host="ignored", port="0", name="memory", user="x", password="y"
    )
    assert url == "sqlite:memory"


def test_build_db_url_postgres_with_password() -> None:
    url = _build_db_url(
        db_type="postgresql", host="db", port="5432", name="waddlebot", user="svc", password="p@ss"
    )
    assert url == "postgres://svc:p%40ss@db:5432/waddlebot"


def test_build_db_url_postgres_without_password() -> None:
    url = _build_db_url(
        db_type="postgresql", host="db", port="5432", name="waddlebot", user="svc", password=""
    )
    assert url == "postgres://svc@db:5432/waddlebot"


def test_build_db_url_rejects_unknown_db_type() -> None:
    with pytest.raises(ValueError, match="unsupported DB_TYPE"):
        _build_db_url(db_type="oracle", host="db", port="1", name="n", user="u", password="")


def test_from_env_reads_explicit_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """`DATABASE_URL` set explicitly short-circuits the DB_TYPE/HOST/... assembly."""
    monkeypatch.setenv("DATABASE_URL", "postgres://explicit@host:5432/db")
    monkeypatch.setenv("MODULE_PORT", "9999")
    cfg = Config.from_env()
    assert cfg.database_url == "postgres://explicit@host:5432/db"
    assert cfg.module_port == 9999


def test_from_env_builds_url_from_components(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without `DATABASE_URL`, the DB_TYPE/HOST/PORT/NAME/USER/PASS components assemble one."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_HOST", "myhost")
    monkeypatch.setenv("DB_USER", "svc-presentation-rw")
    cfg = Config.from_env()
    assert "myhost" in cfg.database_url
    assert "svc-presentation-rw" in cfg.database_url


def test_from_env_valkey_url_prefers_valkey_over_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VALKEY_URL", "redis://valkey:6379/0")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    cfg = Config.from_env()
    assert cfg.valkey_url == "redis://valkey:6379/0"


def test_from_env_valkey_url_falls_back_to_redis_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    cfg = Config.from_env()
    assert cfg.valkey_url == "redis://redis:6379/0"


def test_from_env_valkey_url_none_when_neither_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    cfg = Config.from_env()
    assert cfg.valkey_url is None
