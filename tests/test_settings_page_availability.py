import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.core.config import resolve_admin_controls_enabled
from app.main import app
from app.models import Site
from app.services.mcegold_cli_discovery_client import MceGoldCliDiscoveryClient
from app.storage.application_settings import ApplicationSettingsRepository

class AvailabilityDiscoveryClient:
    def get_sites(self, session_id: str | None = None) -> list[Site]:
        return []

@pytest.fixture
def portal_settings_availability_test(tmp_path):
    original_config_path = routes.settings.portal_local_config_path
    original_database_path = routes.settings.discovery_database_path
    original_admin_controls_enabled = routes.settings.admin_controls_enabled
    had_client = hasattr(app.state, "discovery_client")
    original_client = getattr(app.state, "discovery_client", None)
    had_shared_session = hasattr(app.state, "discovery_session_id")
    original_shared_session = getattr(app.state, "discovery_session_id", None)
    had_shared_started_at = hasattr(app.state, "discovery_started_at")
    original_shared_started_at = getattr(app.state, "discovery_started_at", None)

    database_path = tmp_path / "settings-availability.db"
    object.__setattr__(routes.settings, "portal_local_config_path", str(tmp_path / "portal.local.json"))
    object.__setattr__(routes.settings, "discovery_database_path", str(database_path))
    object.__setattr__(routes.settings, "admin_controls_enabled", True)
    app.state.discovery_client = AvailabilityDiscoveryClient()
    for attr in ("discovery_session_id", "discovery_started_at"):
        if hasattr(app.state, attr):
            delattr(app.state, attr)

    try:
        yield database_path
    finally:
        object.__setattr__(routes.settings, "portal_local_config_path", original_config_path)
        object.__setattr__(routes.settings, "discovery_database_path", original_database_path)
        object.__setattr__(routes.settings, "admin_controls_enabled", original_admin_controls_enabled)
        if had_client:
            app.state.discovery_client = original_client
        elif hasattr(app.state, "discovery_client"):
            delattr(app.state, "discovery_client")
        if had_shared_session:
            app.state.discovery_session_id = original_shared_session
        elif hasattr(app.state, "discovery_session_id"):
            delattr(app.state, "discovery_session_id")
        if had_shared_started_at:
            app.state.discovery_started_at = original_shared_started_at
        elif hasattr(app.state, "discovery_started_at"):
            delattr(app.state, "discovery_started_at")


@pytest.mark.parametrize(
    ("local_config", "expected"),
    [
        ({}, True),
        ({"adminControlsEnabled": True}, True),
        ({"adminControlsEnabled": False}, False),
        ({"adminControlsEnabled": "not-a-bool"}, True),
    ],
)
def test_admin_controls_enabled_configuration_uses_local_json(monkeypatch, local_config, expected) -> None:
    monkeypatch.delenv("PORTAL_ADMIN_CONTROLS_ENABLED", raising=False)

    enabled, _source = resolve_admin_controls_enabled(local_config)

    assert enabled is expected


@pytest.mark.parametrize(
    ("local_config", "env_value", "expected"),
    [
        ({"adminControlsEnabled": True}, "false", True),
        ({"adminControlsEnabled": False}, "true", False),
    ],
)
def test_admin_controls_enabled_ignores_environment(monkeypatch, local_config, env_value, expected) -> None:
    monkeypatch.setenv("PORTAL_ADMIN_CONTROLS_ENABLED", env_value)

    enabled, source = resolve_admin_controls_enabled(local_config)

    assert enabled is expected
    assert source == "local config"


def test_old_admin_control_names_are_not_recognized(monkeypatch) -> None:
    monkeypatch.delenv("PORTAL_ADMIN_CONTROLS_ENABLED", raising=False)
    monkeypatch.setenv("PORTAL_SETTINGS_ENABLED", "false")

    enabled, source = resolve_admin_controls_enabled({"settingsPageEnabled": False})

    assert enabled is True
    assert source == "default"


def test_navigation_renders_settings_link_when_enabled(portal_settings_availability_test) -> None:
    object.__setattr__(routes.settings, "admin_controls_enabled", True)

    with TestClient(app) as test_client:
        response = test_client.get("/")

    assert response.status_code == 200
    assert 'href="/settings"' in response.text
    assert 'href="/"' in response.text
    assert 'href="/discovery/sites"' in response.text
    assert "Dashboard" in response.text


def test_navigation_hides_settings_link_when_disabled(portal_settings_availability_test) -> None:
    object.__setattr__(routes.settings, "admin_controls_enabled", False)

    with TestClient(app) as test_client:
        response = test_client.get("/")

    assert response.status_code == 200
    assert 'href="/settings"' not in response.text
    assert 'href="/"' in response.text
    assert 'href="/discovery/sites"' in response.text
    assert "Dashboard" in response.text


def test_get_settings_enabled_returns_settings_page(portal_settings_availability_test) -> None:
    object.__setattr__(routes.settings, "admin_controls_enabled", True)

    with TestClient(app) as test_client:
        response = test_client.get("/settings")

    assert response.status_code == 200
    assert "Portal Settings" in response.text


def test_get_settings_disabled_returns_404(portal_settings_availability_test) -> None:
    object.__setattr__(routes.settings, "admin_controls_enabled", False)

    with TestClient(app) as test_client:
        response = test_client.get("/settings")

    assert response.status_code == 404
    assert "Portal Settings" not in response.text


def test_post_settings_disabled_returns_404_and_does_not_change_application_settings(
    portal_settings_availability_test,
) -> None:
    object.__setattr__(routes.settings, "admin_controls_enabled", False)

    with TestClient(app) as test_client:
        repository = ApplicationSettingsRepository(portal_settings_availability_test)
        repository.set_setting("Collector.Enabled", False)
        repository.set_setting("DataRetention.Days", 90)
        repository.set_setting("EnergyCost.RatePerKwh", "1.250000")
        before_rows = application_setting_rows(portal_settings_availability_test)

        response = test_client.post(
            "/settings",
            data={
                "application_settings_present": "1",
                "mcegold_cli_path": "tampered-cli.exe",
                "connector_config_path": "tampered-connector.json",
                "discovery_database_path": str(portal_settings_availability_test),
                "grafana_dashboard_url": "http://127.0.0.1:3000/d/tampered",
                "collector_enabled": "on",
                "collector_polling_interval_seconds": "30",
                "data_retention_enabled": "on",
                "data_retention_days": "180",
                "energy_cost_currency_uom_uuid": "",
                "energy_cost_rate_per_kwh": "",
            },
        )

    assert response.status_code == 404
    assert application_setting_rows(portal_settings_availability_test) == before_rows
    assert ApplicationSettingsRepository(portal_settings_availability_test).get_boolean("Collector.Enabled") is False
    assert ApplicationSettingsRepository(portal_settings_availability_test).get_integer("DataRetention.Days") == 90


def test_discovery_route_remains_available_when_settings_disabled(portal_settings_availability_test) -> None:
    object.__setattr__(routes.settings, "admin_controls_enabled", False)

    with TestClient(app) as test_client:
        response = test_client.get("/discovery/sites", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/?message=start_discovery"


@pytest.mark.parametrize(
    ("admin_controls_enabled", "expected_diagnostics"),
    [
        (True, True),
        (False, False),
    ],
)
def test_discovery_diagnostics_visibility_follows_admin_controls_enabled(
    portal_settings_availability_test,
    admin_controls_enabled: bool,
    expected_diagnostics: bool,
    monkeypatch,
) -> None:
    cli_client = MceGoldCliDiscoveryClient("cli.exe", "config.json")
    monkeypatch.setattr(cli_client, "open_request_session", lambda: "session-1")
    monkeypatch.setattr(
        cli_client,
        "get_sites",
        lambda session_id=None: [
            Site(
                site_uuid="site-1",
                site_name="Test Site",
                site_type="Plant",
                status="Active",
                region="",
                description="",
            )
        ],
    )
    app.state.discovery_client = cli_client
    object.__setattr__(routes.settings, "admin_controls_enabled", admin_controls_enabled)

    with TestClient(app) as test_client:
        test_client.post("/discovery/start", follow_redirects=False)
        response = test_client.get("/discovery/sites")

    assert response.status_code == 200
    assert "Test Site" in response.text
    assert ("Diagnostics" in response.text) is expected_diagnostics
    assert ("<details" in response.text) is expected_diagnostics


def application_setting_rows(database_path) -> list[tuple[str, str | None, str]]:
    with sqlite3.connect(database_path) as connection:
        return [
            (row[0], row[1], row[2])
            for row in connection.execute(
                """
                SELECT SettingKey, SettingValue, ValueType
                FROM ApplicationSetting
                ORDER BY SettingKey
                """
            )
        ]

