import sqlite3
import re
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.storage.application_settings import ApplicationSettingsRepository
from app.storage.collector_runtime_status import PUBLICATION_COLLECTOR_ID


@pytest.fixture
def portal_settings_runtime_test(monkeypatch, tmp_path):
    original_config_path = routes.settings.portal_local_config_path
    original_database_path = routes.settings.discovery_database_path
    had_client = hasattr(app.state, "discovery_client")
    original_client = getattr(app.state, "discovery_client", None)

    database_path = tmp_path / "route-status.db"
    object.__setattr__(routes.settings, "portal_local_config_path", str(tmp_path / "portal.local.json"))
    object.__setattr__(routes.settings, "discovery_database_path", str(database_path))
    app.state.discovery_client = object()

    try:
        yield database_path
    finally:
        object.__setattr__(routes.settings, "portal_local_config_path", original_config_path)
        object.__setattr__(routes.settings, "discovery_database_path", original_database_path)
        if had_client:
            app.state.discovery_client = original_client
        elif hasattr(app.state, "discovery_client"):
            delattr(app.state, "discovery_client")


def test_settings_page_renders_live_collector_runtime_status(portal_settings_runtime_test) -> None:
    with TestClient(app) as test_client:
        store_collector_status(
            portal_settings_runtime_test,
            runtime_state="Running",
            last_heartbeat_utc=datetime.now(UTC).isoformat(),
            last_publication_utc="2026-08-20T14:15:00Z",
        )

        response = test_client.get("/settings")

    assert response.status_code == 200
    assert "Runtime status" in response.text
    assert "Running" in response.text
    assert "text-bg-success" in response.text
    assert "Last publication" in response.text
    assert "2026-08-20 14:15 UTC" in response.text
    assert "Runtime control will be connected in a later stage." not in response.text


def test_settings_page_keeps_disabled_desired_state_separate_from_running_status(
    portal_settings_runtime_test,
) -> None:
    with TestClient(app) as test_client:
        set_collector_enabled(portal_settings_runtime_test, False)
        store_collector_status(
            portal_settings_runtime_test,
            runtime_state="Running",
            last_heartbeat_utc=datetime.now(UTC).isoformat(),
        )

        response = test_client.get("/settings")

    assert response.status_code == 200
    assert "Running" in response.text
    assert "Collector process is alive and publication polling is active." in response.text
    assert re.search(r'id="collector_enabled"[^>]*checked', response.text) is None


def test_settings_page_renders_idle_runtime_status_when_disabled_but_alive(
    portal_settings_runtime_test,
) -> None:
    with TestClient(app) as test_client:
        set_collector_enabled(portal_settings_runtime_test, False)
        store_collector_status(
            portal_settings_runtime_test,
            runtime_state="Idle",
            last_heartbeat_utc=datetime.now(UTC).isoformat(),
        )

        response = test_client.get("/settings")

    assert response.status_code == 200
    assert "Idle" in response.text
    assert "text-bg-info" in response.text
    assert "Collector process is alive and publication polling is paused." in response.text


def test_settings_page_renders_error_runtime_status(portal_settings_runtime_test) -> None:
    with TestClient(app) as test_client:
        store_collector_status(
            portal_settings_runtime_test,
            runtime_state="Error",
            last_heartbeat_utc=datetime.now(UTC).isoformat(),
            last_error="Subscription failed.",
        )

        response = test_client.get("/settings")

    assert response.status_code == 200
    assert "Error" in response.text
    assert "text-bg-danger" in response.text
    assert "Collector process is alive and reported an operational error." in response.text
    assert "Subscription failed." in response.text


def test_settings_page_renders_offline_when_runtime_status_is_missing(portal_settings_runtime_test) -> None:
    with TestClient(app) as test_client:
        response = test_client.get("/settings")

    assert response.status_code == 200
    assert "Offline" in response.text
    assert "text-bg-secondary" in response.text
    assert "Never" in response.text
    assert "None" in response.text
    assert "Collector is enabled, but no active heartbeat is detected." in response.text


def test_settings_page_renders_offline_when_heartbeat_is_stale(portal_settings_runtime_test) -> None:
    with TestClient(app) as test_client:
        store_collector_status(
            portal_settings_runtime_test,
            runtime_state="Running",
            last_heartbeat_utc="2000-01-01T00:00:00Z",
        )

        response = test_client.get("/settings")

    assert response.status_code == 200
    assert "Offline" in response.text
    assert "text-bg-secondary" in response.text
    assert "2000-01-01 00:00 UTC" in response.text


def test_settings_page_escapes_collector_runtime_error(portal_settings_runtime_test) -> None:
    with TestClient(app) as test_client:
        store_collector_status(
            portal_settings_runtime_test,
            runtime_state="Error",
            last_heartbeat_utc=datetime.now(UTC).isoformat(),
            last_error_utc="2026-08-20T14:16:00Z",
            last_error="<script>alert(1)</script>",
        )

        response = test_client.get("/settings")

    assert response.status_code == 200
    assert "Last error" in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text
    assert "<script>alert(1)</script>" not in response.text


def test_settings_page_handles_collector_status_read_failure(monkeypatch, portal_settings_runtime_test) -> None:
    def fail_to_read_status(database_path):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(routes, "get_publication_collector_status", fail_to_read_status)

    with TestClient(app) as test_client:
        response = test_client.get("/settings")

    assert response.status_code == 200
    assert "Offline" in response.text
    assert "Runtime status is temporarily unavailable." in response.text


def set_collector_enabled(database_path, enabled: bool) -> None:
    ApplicationSettingsRepository(database_path).set_setting("Collector.Enabled", enabled)


def store_collector_status(
    database_path,
    *,
    runtime_state: str,
    last_heartbeat_utc: str,
    last_publication_utc: str | None = None,
    last_error_utc: str | None = None,
    last_error: str | None = None,
) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO CollectorRuntimeStatus (
                CollectorId,
                InstanceId,
                StartedUtc,
                LastHeartbeatUtc,
                RuntimeState,
                LastPublicationUtc,
                LastErrorUtc,
                LastError
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                PUBLICATION_COLLECTOR_ID,
                "portal-test",
                "2026-08-20T14:00:00Z",
                last_heartbeat_utc,
                runtime_state,
                last_publication_utc,
                last_error_utc,
                last_error,
            ),
        )
        connection.commit()
