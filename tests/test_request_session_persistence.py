import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api import routes
from app.main import app
from app.storage.application_settings import (
    ApplicationSettingsRepository,
    REQUEST_SESSION_ID,
    REQUEST_SESSION_STARTED_UTC,
)
from app.storage.database import initialize_database
from tests.test_routes import (
    FakeCliClient,
    isolate_portal,
    select_site_context,
    select_segment_context,
    select_location_context,
    start_discovery,
    TAMPA,
    PUMP_TRAIN,
    MOTOR_DE,
)
from app.services.mcegold_cli_discovery_client import CliDiscoveryError


def session_request():
    return Request({"type": "http", "app": app, "session": {}, "headers": []})


def repository():
    return ApplicationSettingsRepository(app.state.database.db_path)


def closed_error():
    return CliDiscoveryError("The request session does not exist.", command=[])


@pytest.mark.parametrize("message,expected", [
    ("Request session is closed.", True),
    ("Session 'opaque-id' has been closed.", True),
    ("Session with ID abc does not exist.", True),
    ("The session request failed: the connection closed unexpectedly.", False),
    ("Could not open a request session: config file does not exist.", False),
    ("Connection timed out for session abc.", False),
])
def test_only_explicit_session_errors_are_invalidations(message, expected):
    assert routes.is_closed_cli_session_error(CliDiscoveryError(message, [])) is expected


def test_new_session_is_saved_and_reused_across_browsers():
    with TestClient(app) as browser:
        cli = start_discovery(browser)
        saved = repository().get_request_session()
        assert saved == (app.state.discovery_session_id, app.state.discovery_started_at)
        assert saved[0] == "session-1"
        assert saved[1]
        with TestClient(app) as other_browser:
            response = other_browser.post("/discovery/start", follow_redirects=False)
            assert response.status_code == 303
        assert cli.opened == 1
        assert repository().get_request_session() == saved


def test_restart_restores_original_timestamp_without_remote_open_or_close(monkeypatch):
    cli = FakeCliClient()
    monkeypatch.setattr(routes, "create_discovery_client", lambda: cli)
    with TestClient(app) as browser:
        start_discovery(browser, cli)
        saved = repository().get_request_session()
    assert cli.closed == []
    for attr in ("discovery_client", "discovery_session_id", "discovery_started_at"):
        delattr(app.state, attr)
    with TestClient(app) as browser:
        assert (app.state.discovery_session_id, app.state.discovery_started_at) == saved
        assert not hasattr(app.state, "discovery_client")
        assert cli.opened == 1
        browser.post("/discovery/start", follow_redirects=False)
        assert cli.opened == 1
        assert repository().get_request_session() == saved
    assert cli.closed == []


@pytest.mark.parametrize("saved_id", [None, "", "   "])
def test_startup_without_saved_id_never_opens_session(monkeypatch, saved_id):
    path = routes.settings.discovery_database_path
    initialize_database(path)
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE ApplicationSetting SET SettingValue = ? WHERE SettingKey = ?", (saved_id, REQUEST_SESSION_ID))
    monkeypatch.setattr(routes, "create_discovery_client", lambda: pytest.fail("Startup contacted the CLI"))
    with TestClient(app):
        assert app.state.discovery_session_id is None
        assert app.state.discovery_started_at is None


def test_pair_update_rolls_back_if_second_value_fails(tmp_path):
    path = tmp_path / "atomic.db"
    initialize_database(path)
    repo = ApplicationSettingsRepository(path)
    repo.set_request_session("opaque original", "original-time")
    with sqlite3.connect(path) as connection:
        connection.execute(f"""
            CREATE TRIGGER reject_timestamp BEFORE UPDATE ON ApplicationSetting
            WHEN NEW.SettingKey = '{REQUEST_SESSION_STARTED_UTC}'
            BEGIN SELECT RAISE(ABORT, 'timestamp write rejected'); END
        """)
    with pytest.raises(sqlite3.IntegrityError):
        repo.set_request_session("replacement", "new-time")
    assert repo.get_request_session() == ("opaque original", "original-time")
    with pytest.raises(sqlite3.IntegrityError):
        repo.set_request_session(None, None)
    assert repo.get_request_session() == ("opaque original", "original-time")


def test_existing_v17_initialization_seeds_only_missing_values(tmp_path):
    path = tmp_path / "existing.db"
    initialize_database(path)
    repo = ApplicationSettingsRepository(path)
    repo.set_request_session("opaque / not-a-uuid", "original-time")
    with sqlite3.connect(path) as connection:
        tables_before = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        connection.execute("DELETE FROM ApplicationSetting WHERE SettingKey = ?", (REQUEST_SESSION_STARTED_UTC,))
    result = initialize_database(path)
    assert result.current_version == 17
    assert result.migrations_applied == ()
    assert repo.get_request_session() == ("opaque / not-a-uuid", None)
    assert repo.get_setting(REQUEST_SESSION_STARTED_UTC).value_type == "String"
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall() == tables_before
    repo.set_request_session("saved", "original-time")
    initialize_database(path)
    assert repo.get_request_session() == ("saved", "original-time")


@pytest.mark.parametrize("close_fails", [False, True])
def test_end_clears_persistence_even_when_remote_close_fails(monkeypatch, close_fails):
    with TestClient(app) as browser:
        cli = start_discovery(browser)
        if close_fails:
            monkeypatch.setattr(cli, "close_request_session", lambda _: (_ for _ in ()).throw(CliDiscoveryError("offline", [])))
        response = browser.post("/discovery/end", follow_redirects=False)
        assert response.status_code == 303
        assert repository().get_request_session() == (None, None)
        assert not hasattr(app.state, "discovery_session_id")
        assert ("close_failed" in response.headers["location"]) == close_fails


@pytest.mark.parametrize("url", ["/discovery/sites", "/api/sites", f"/api/sites/{TAMPA}/segments"])
@pytest.mark.parametrize("invalid", [True, False])
def test_confirmed_invalidation_but_not_connectivity_failure(monkeypatch, url, invalid):
    with TestClient(app) as browser:
        cli = start_discovery(browser)
        saved = repository().get_request_session()
        error = closed_error() if invalid else CliDiscoveryError("The connection timed out.", [], timeout_seconds=30)
        monkeypatch.setattr(cli, "get_sites", lambda *_: (_ for _ in ()).throw(error))
        response = browser.get(url)
        assert response.status_code == (502 if url.startswith("/api/") else 200)
        assert repository().get_request_session() == ((None, None) if invalid else saved)
        assert getattr(app.state, "discovery_session_id", None) == (None if invalid else saved[0])


@pytest.mark.parametrize("replacement_fails", [False, True])
def test_segments_clears_old_id_before_replacement_and_retries_once(monkeypatch, replacement_fails):
    with TestClient(app) as browser:
        cli = start_discovery(browser)
        select_site_context(browser)
        calls = []
        original_get_segments = cli.get_segments

        def get_segments(*args, **kwargs):
            calls.append(kwargs["session_id"])
            if len(calls) == 1:
                raise closed_error()
            return original_get_segments(*args, **kwargs)

        def open_replacement():
            assert repository().get_request_session() == (None, None)
            assert not hasattr(app.state, "discovery_session_id")
            if replacement_fails:
                raise CliDiscoveryError("Cannot open replacement.", [])
            return "replacement"

        monkeypatch.setattr(cli, "get_segments", get_segments)
        monkeypatch.setattr(cli, "open_request_session", open_replacement)
        response = browser.get(f"/discovery/sites/{TAMPA}/segments?searched=true")
        assert response.status_code == 200
        assert calls == (["session-1"] if replacement_fails else ["session-1", "replacement"])
        assert repository().get_request_session()[0] == (None if replacement_fails else "replacement")
        if not replacement_fails:
            assert "Pump Train P-101" in response.text


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_failed_persistence_closes_unpublished_remote_session(monkeypatch, cleanup_fails):
    with TestClient(app) as browser:
        cli = FakeCliClient()
        app.state.discovery_client = cli
        closed = []

        def close(session_id):
            closed.append(session_id)
            if cleanup_fails:
                raise CliDiscoveryError("Cannot close.", [])

        monkeypatch.setattr(cli, "close_request_session", close)
        monkeypatch.setattr(ApplicationSettingsRepository, "set_request_session", lambda *args: (_ for _ in ()).throw(sqlite3.OperationalError("locked")))
        response = browser.post("/discovery/start")
        assert response.status_code == 503
        assert closed == ["session-1"]
        assert getattr(app.state, "discovery_session_id", None) is None
        assert repository().get_request_session() == (None, None)


def test_failed_replacement_persistence_keeps_invalid_id_cleared(monkeypatch):
    with TestClient(app) as browser:
        cli = start_discovery(browser)
        original_write = ApplicationSettingsRepository.set_request_session

        def write(repo, session_id, started):
            if session_id:
                raise sqlite3.OperationalError("locked")
            original_write(repo, session_id, started)

        monkeypatch.setattr(ApplicationSettingsRepository, "set_request_session", write)
        with pytest.raises(HTTPException) as error:
            routes.reopen_cli_session_for_retry(session_request(), "session-1")
        assert error.value.status_code == 503
        assert repository().get_request_session() == (None, None)
        assert not hasattr(app.state, "discovery_session_id")
        assert cli.closed == ["session-1"]


@pytest.mark.parametrize("retry_invalid", [False, True])
def test_replacement_retry_failure_clears_only_a_confirmed_invalid_replacement(monkeypatch, retry_invalid):
    with TestClient(app) as browser:
        cli = start_discovery(browser)
        select_site_context(browser)
        calls = []

        def fail_segments(*args, **kwargs):
            calls.append(kwargs["session_id"])
            if len(calls) == 1 or retry_invalid:
                raise closed_error()
            raise CliDiscoveryError("Temporary network failure.", [])

        monkeypatch.setattr(cli, "get_segments", fail_segments)
        monkeypatch.setattr(cli, "open_request_session", lambda: "replacement")
        response = browser.get(f"/discovery/sites/{TAMPA}/segments?searched=true")
        assert response.status_code == 200
        assert calls == ["session-1", "replacement"]
        assert repository().get_request_session()[0] == (None if retry_invalid else "replacement")


def test_failed_clear_preserves_matching_memory_and_database(monkeypatch):
    with TestClient(app) as browser:
        start_discovery(browser)
        saved = repository().get_request_session()
        monkeypatch.setattr(ApplicationSettingsRepository, "set_request_session", lambda *args: (_ for _ in ()).throw(sqlite3.OperationalError("locked")))
        response = browser.post("/discovery/end")
        assert response.status_code == 503
        assert repository().get_request_session() == saved
        assert app.state.discovery_session_id == saved[0]


def test_late_invalid_response_cannot_clear_or_replace_newer_session(monkeypatch):
    with TestClient(app) as browser:
        cli = start_discovery(browser)
        entered, release = Event(), Event()

        def late_failure():
            req = session_request()
            used_id = routes.get_discovery_session_id(req)
            entered.set()
            assert release.wait(5)
            return routes.clear_discovery_session(req, used_id)

        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(late_failure)
            assert entered.wait(5)
            routes.refresh_discovery_session(session_request(), "newer")
            release.set()
            assert pending.result(timeout=5) is False
        saved = repository().get_request_session()
        assert routes.reopen_cli_session_for_retry(session_request(), "session-1") == "newer"
        assert cli.opened == 1
        assert repository().get_request_session() == saved
        assert app.state.discovery_session_id == "newer"


def test_concurrent_start_opens_only_one_remote_session():
    with TestClient(app):
        cli = FakeCliClient()
        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(lambda _: routes.get_or_open_shared_discovery_session(session_request(), cli), range(2)))
        assert ids == ["session-1", "session-1"]
        assert cli.opened == 1
        assert repository().get_request_session()[0] == "session-1"


def test_invalidation_waiting_on_replacement_cannot_undo_it(monkeypatch):
    with TestClient(app) as browser:
        cli = start_discovery(browser)
        opened, release, invalidating = Event(), Event(), Event()

        def open_replacement():
            # A remote CLI operation must not run inside a SQLite write transaction.
            with sqlite3.connect(app.state.database.db_path, timeout=0) as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.rollback()
            opened.set()
            assert release.wait(5)
            return "newer"

        def invalidate_old():
            invalidating.set()
            return routes.clear_discovery_session(session_request(), "session-1")

        monkeypatch.setattr(cli, "open_request_session", open_replacement)
        with ThreadPoolExecutor(max_workers=2) as pool:
            replacing = pool.submit(routes.reopen_cli_session_for_retry, session_request(), "session-1")
            assert opened.wait(5)
            clearing = pool.submit(invalidate_old)
            assert invalidating.wait(5)
            release.set()
            assert replacing.result(timeout=5) == "newer"
            assert clearing.result(timeout=5) is False
        assert repository().get_request_session()[0] == app.state.discovery_session_id == "newer"


def test_ended_session_is_not_reopened_by_late_retry():
    with TestClient(app) as browser:
        cli = start_discovery(browser)
        browser.post("/discovery/end", follow_redirects=False)
        assert routes.reopen_cli_session_for_retry(session_request(), "session-1") is None
        assert cli.opened == 1
        assert repository().get_request_session() == (None, None)


@pytest.mark.parametrize("field,value,invalidates", [
    ("mcegold_data_services_url", "https://other.example.test", True),
    ("mcegold_username", "other-user", True),
    ("mcegold_password", "new-password", True),
    ("mcegold_api_key", "new-key", True),
    ("connector_config_path", "other.config.json", True),
    ("grafana_dashboard_url", "http://other-grafana:3000", False),
    ("collector_polling_interval_seconds", "45", False),
])
def test_configuration_change_invalidates_only_connection_fields(monkeypatch, field, value, invalidates):
    # Keep test results independent of the developer's connection environment.
    for name in ("MCEGOLD_HOST", "MCEGOLD_USERNAME", "MCEGOLD_PASSWORD", "MCEGOLD_API_KEY", "CONNECTOR_CONFIG_PATH", "MCEGOLD_CLI_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(routes, "synchronize_connector_config_from_portal", lambda *args: None)
    with TestClient(app) as browser:
        cli = start_discovery(browser)
        saved = repository().get_request_session()
        values = {
            "mcegold_cli_path": routes.settings.mcegold_cli_path or "cli.exe",
            "connector_config_path": routes.settings.connector_config_path,
            "discovery_database_path": routes.settings.discovery_database_path,
            "grafana_dashboard_url": routes.settings.grafana_dashboard_url,
            "application_settings_present": "1",
            "collector_enabled": "on",
        }
        # Establish a matching configuration baseline for the active fake client.
        routes.write_portal_local_config({
            "mcegoldCliPath": values["mcegold_cli_path"],
            "connectorConfigPath": values["connector_config_path"],
        }, routes.settings.portal_local_config_path)
        values[field] = value
        response = browser.post("/settings", data=values)
        assert response.status_code == 200
        assert repository().get_request_session() == ((None, None) if invalidates else saved)
        assert getattr(app.state, "discovery_session_id", None) == (None if invalidates else saved[0])
        assert (app.state.discovery_client is not cli) is invalidates
        assert cli.opened == 1
        if field == "collector_polling_interval_seconds":
            assert repository().get_integer("Collector.PollingIntervalSeconds") == 45


def connection_form():
    """Establish a matching saved connection for the fake CLI."""
    values = {
        "mcegold_data_services_url": "https://old.example.test",
        "mcegold_cli_path": "old-cli.exe",
        "connector_config_path": routes.settings.connector_config_path,
        "discovery_database_path": routes.settings.discovery_database_path,
        "grafana_dashboard_url": routes.settings.grafana_dashboard_url,
    }
    config = {
        routes.PORTAL_LOCAL_CONFIG_FIELDS[name]["local"]: value
        for name, value in values.items()
    }
    routes.write_portal_local_config(config, routes.settings.portal_local_config_path)
    routes.refresh_saved_portal_settings(config)
    return values


@pytest.mark.parametrize("new_session_id", ["new-server-session", "session-1"])
@pytest.mark.parametrize("failure_during_retry", [False, True])
def test_segments_retry_aborts_after_concurrent_connection_change(monkeypatch, new_session_id, failure_during_retry):
    monkeypatch.delenv("MCEGOLD_HOST", raising=False)
    monkeypatch.setattr(routes, "synchronize_connector_config_from_portal", lambda *args: None)
    with TestClient(app) as browser:
        values = connection_form()
        old_cli = start_discovery(browser)
        select_site_context(browser)
        entered, release = Event(), Event()
        calls = []

        def fail_old_operation(*args, **kwargs):
            calls.append(kwargs["session_id"])
            if failure_during_retry and len(calls) == 1:
                raise closed_error()
            entered.set()
            assert release.wait(5)
            raise closed_error()

        new_cli = FakeCliClient()
        monkeypatch.setattr(new_cli, "open_request_session", lambda: new_session_id)
        monkeypatch.setattr(old_cli, "get_segments", fail_old_operation)
        monkeypatch.setattr(routes, "create_discovery_client", lambda: new_cli)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(browser.get, f"/discovery/sites/{TAMPA}/segments?searched=true")
            try:
                assert entered.wait(5)
                values["mcegold_data_services_url"] = "https://new.example.test"
                assert browser.post("/settings", data=values).status_code == 200
                assert browser.post("/discovery/start", follow_redirects=False).status_code == 303
                saved = repository().get_request_session()
            finally:
                release.set()
            assert pending.result(timeout=5).status_code == 200
        assert calls == (["session-1", "session-1"] if failure_during_retry else ["session-1"])
        assert app.state.discovery_client is new_cli
        assert app.state.discovery_session_id == new_session_id
        assert repository().get_request_session() == saved


@pytest.mark.parametrize("changed_field", ["mcegold_data_services_url", "connector_config_path", "mcegold_cli_path", None])
def test_partial_configuration_save_does_not_reuse_outdated_client(monkeypatch, tmp_path, changed_field):
    for name in ("MCEGOLD_HOST", "CONNECTOR_CONFIG_PATH", "MCEGOLD_CLI_PATH"):
        monkeypatch.delenv(name, raising=False)

    def fail_sync(*args):
        raise routes.ConnectorConfigSyncError("Connector sync failed.")

    def create_client():
        cli = FakeCliClient()
        cli.cli_path = routes.settings.mcegold_cli_path
        cli.connector_config_path = routes.settings.connector_config_path
        cli.environment_overrides = routes.resolve_data_services_environment(
            routes.read_portal_local_config(routes.settings.portal_local_config_path)
        )
        original_open = cli.open_request_session

        def open_session():
            original_open()
            return "session-from-current-connection"

        cli.open_request_session = open_session
        return cli

    monkeypatch.setattr(routes, "synchronize_connector_config_from_portal", fail_sync)
    monkeypatch.setattr(routes, "create_discovery_client", create_client)
    with TestClient(app) as browser:
        values = connection_form()
        old_cli = start_discovery(browser)
        saved = repository().get_request_session()
        if changed_field:
            values[changed_field] = {
                "mcegold_data_services_url": "https://new.example.test",
                "connector_config_path": str(tmp_path / "new-connector.json"),
                "mcegold_cli_path": "new-cli.exe",
            }[changed_field]
        else:
            values["grafana_dashboard_url"] = "http://new-grafana:3000"
        response = browser.post("/settings", data=values)
        assert response.status_code == 400
        assert "Connector configuration could not be saved." in response.text
        if not changed_field:
            assert app.state.discovery_client is old_cli
            assert repository().get_request_session() == saved
            return
        assert app.state.discovery_client is not old_cli
        assert repository().get_request_session() == (None, None)
        assert browser.post("/discovery/start", follow_redirects=False).status_code == 303
        current_cli = app.state.discovery_client
        assert current_cli.environment_overrides["MCEGOLD_HOST"] == values["mcegold_data_services_url"]
        assert current_cli.cli_path == values["mcegold_cli_path"]
        assert current_cli.connector_config_path == values["connector_config_path"]
        assert old_cli.opened == 1
        assert current_cli.opened == 1
        assert repository().get_request_session()[0] == "session-from-current-connection"


DISCOVERY_INVALIDATION_CASES = [
    ("/api/sites", "get_sites", None),
    (f"/api/sites/{TAMPA}/segments", "get_segments", None),
    (f"/api/sites/{TAMPA}/segments/{PUMP_TRAIN}/measurement-locations", "get_measurement_locations", None),
    (f"/api/sites/{TAMPA}/segments/{PUMP_TRAIN}/measurement-locations/{MOTOR_DE}/measurements", "get_measurements", None),
    ("/discovery/sites", "get_sites", None),
    (f"/discovery/sites/{TAMPA}/segments?searched=true", "get_segments", select_site_context),
    (f"/discovery/sites/{TAMPA}/segments/{PUMP_TRAIN}/measurement-locations?searched=true", "get_measurement_locations", select_segment_context),
    (f"/discovery/sites/{TAMPA}/segments/{PUMP_TRAIN}/measurement-locations/{MOTOR_DE}/measurements?searched=true", "get_measurements", select_location_context),
]


@pytest.mark.parametrize("url,method,select_context", DISCOVERY_INVALIDATION_CASES)
def test_delayed_discovery_error_preserves_same_id_on_new_connection(monkeypatch, url, method, select_context):
    monkeypatch.delenv("MCEGOLD_HOST", raising=False)
    monkeypatch.setattr(routes, "synchronize_connector_config_from_portal", lambda *args: None)
    with TestClient(app) as browser:
        values = connection_form()
        old_cli = start_discovery(browser)
        if select_context:
            select_context(browser)
        entered, release = Event(), Event()
        calls = []

        def delayed_error(*args, **kwargs):
            calls.append((args, kwargs))
            entered.set()
            assert release.wait(5)
            raise closed_error()

        monkeypatch.setattr(old_cli, method, delayed_error)
        new_cli = FakeCliClient()  # Both connections return the opaque ID session-1.
        monkeypatch.setattr(routes, "create_discovery_client", lambda: new_cli)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(browser.get, url)
            try:
                assert entered.wait(5)
                values["mcegold_data_services_url"] = "https://new.example.test"
                assert browser.post("/settings", data=values).status_code == 200
                assert browser.post("/discovery/start", follow_redirects=False).status_code == 303
                saved = repository().get_request_session()
                generation = app.state.discovery_connection_generation
            finally:
                release.set()
            response = pending.result(timeout=5)
        assert response.status_code == (502 if url.startswith("/api/") else 200)
        assert len(calls) == 1
        assert app.state.discovery_connection_generation == generation
        assert app.state.discovery_client is new_cli
        assert app.state.discovery_session_id == "session-1"
        assert repository().get_request_session() == saved


@pytest.mark.parametrize("url,method,select_context", DISCOVERY_INVALIDATION_CASES)
def test_current_generation_discovery_error_clears_session(monkeypatch, url, method, select_context):
    with TestClient(app) as browser:
        cli = start_discovery(browser)
        if select_context:
            select_context(browser)

        def invalid_session(*args, **kwargs):
            raise closed_error()

        monkeypatch.setattr(cli, method, invalid_session)
        response = browser.get(url)
        assert response.status_code == (502 if url.startswith("/api/") else 200)
        assert repository().get_request_session() == (None, None)
        assert getattr(app.state, "discovery_session_id", None) is None
        assert cli.opened == (2 if url.startswith("/discovery/") and method == "get_segments" else 1)


def test_api_parent_lookup_and_child_request_use_the_same_connection(monkeypatch):
    monkeypatch.delenv("MCEGOLD_HOST", raising=False)
    monkeypatch.setattr(routes, "synchronize_connector_config_from_portal", lambda *args: None)
    with TestClient(app) as browser:
        values = connection_form()
        old_cli = start_discovery(browser)
        entered, release = Event(), Event()
        original_get_sites = old_cli.get_sites
        old_segment_ids = []

        def parent_lookup(session_id=None):
            entered.set()
            assert release.wait(5)
            return original_get_sites(session_id)

        def child_request(*args, **kwargs):
            old_segment_ids.append(kwargs["session_id"])
            raise closed_error()

        monkeypatch.setattr(old_cli, "get_sites", parent_lookup)
        monkeypatch.setattr(old_cli, "get_segments", child_request)
        new_cli = FakeCliClient()
        monkeypatch.setattr(routes, "create_discovery_client", lambda: new_cli)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(browser.get, f"/api/sites/{TAMPA}/segments")
            try:
                assert entered.wait(5)
                values["mcegold_data_services_url"] = "https://new.example.test"
                assert browser.post("/settings", data=values).status_code == 200
                assert browser.post("/discovery/start", follow_redirects=False).status_code == 303
                saved = repository().get_request_session()
            finally:
                release.set()
            assert pending.result(timeout=5).status_code == 502
        assert old_segment_ids == ["session-1"]
        assert new_cli.segment_calls == []
        assert app.state.discovery_session_id == "session-1"
        assert repository().get_request_session() == saved
