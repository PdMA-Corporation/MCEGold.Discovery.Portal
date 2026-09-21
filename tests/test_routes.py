import json
import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from app.api import routes
from app.main import app
from app.models import Measurement, MeasurementLocation, Segment, Site
from app.services.mcegold_cli_discovery_client import CliDiscoveryError, MceGoldCliDiscoveryClient
from tests.fake_discovery_client import MOTOR_DE, PUMP_TRAIN, TAMPA


class FakeCliClient(MceGoldCliDiscoveryClient):
    def __init__(self) -> None:
        super().__init__("cli.exe", "config.json")
        self.opened = 0
        self.closed: list[str] = []
        self.site_calls: list[str | None] = []
        self.segment_calls: list[dict[str, object]] = []
        self.location_calls: list[dict[str, object]] = []
        self.measurement_calls: list[dict[str, object]] = []

    def open_request_session(self) -> str:
        self.opened += 1
        return "session-1"

    def close_request_session(self, session_id: str) -> None:
        self.closed.append(session_id)

    def get_sites(self, session_id: str | None = None) -> list[Site]:
        self.site_calls.append(session_id)
        return [
            Site(
                site_uuid=TAMPA,
                site_name="Tampa Plant",
                site_type="Plant",
                status="Active",
                region="Southeast",
                description="Synthetic site",
            )
        ]

    def get_assets(self):
        return []

    def get_segments(
        self,
        site_uuid: str | None = None,
        session_id: str | None = None,
        segment_type_uuid: str | None = None,
        max_items: int | None = None,
    ) -> list[Segment]:
        self.segment_calls.append(
            {
                "site_uuid": site_uuid,
                "session_id": session_id,
                "segment_type_uuid": segment_type_uuid,
                "max_items": max_items,
            }
        )
        return [
            Segment(
                segment_uuid=PUMP_TRAIN,
                site_uuid=TAMPA,
                segment_name="Pump Train P-101",
                segment_type="Pump Train",
                segment_type_uuid="type-1",
                status="Active",
                description="Synthetic segment",
            )
        ]

    def get_measurement_locations(
        self,
        segment_uuid: str | None = None,
        session_id: str | None = None,
        measurement_location_type_uuid: str | None = None,
        max_items: int | None = None,
    ) -> list[MeasurementLocation]:
        self.location_calls.append(
            {
                "segment_uuid": segment_uuid,
                "session_id": session_id,
                "measurement_location_type_uuid": measurement_location_type_uuid,
                "max_items": max_items,
            }
        )
        return [
            MeasurementLocation(
                location_uuid=MOTOR_DE,
                segment_uuid=PUMP_TRAIN,
                location_name="Motor DE",
                location_type="Bearing",
                type_uuid="location-type-1",
                value_class="Measure",
                unit="mm/s",
            )
        ]

    def get_measurements(
        self,
        location_uuid: str | None = None,
        session_id: str | None = None,
        segment_uuid: str | None = None,
        recorded_from: str | None = None,
        recorded_to: str | None = None,
        max_items: int | None = None,
        fallback_unit: str | None = None,
    ) -> list[Measurement]:
        self.measurement_calls.append(
            {
                "location_uuid": location_uuid,
                "session_id": session_id,
                "segment_uuid": segment_uuid,
                "recorded_from": recorded_from,
                "recorded_to": recorded_to,
                "max_items": max_items,
                "fallback_unit": fallback_unit,
            }
        )
        return [
            Measurement(
                measurement_uuid="measurement-1",
                location_uuid=location_uuid or MOTOR_DE,
                measurement_name="Overall Velocity",
                measurement_type="Vibration",
                value=2.41,
                unit=fallback_unit or "mm/s",
                timestamp_utc=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
                status="Normal",
            )
        ]


@pytest.fixture(autouse=True)
def isolate_portal(monkeypatch, tmp_path):
    original_db_path = routes.settings.discovery_database_path
    original_config_path = routes.settings.portal_local_config_path
    original_cli_path = routes.settings.mcegold_cli_path
    original_connector_config_path = routes.settings.connector_config_path
    original_dashboard_url = routes.settings.grafana_dashboard_url
    original_admin_controls_enabled = routes.settings.admin_controls_enabled
    had_client = hasattr(app.state, "discovery_client")
    original_client = getattr(app.state, "discovery_client", None)
    had_session = hasattr(app.state, "discovery_session_id")
    original_session = getattr(app.state, "discovery_session_id", None)
    had_started = hasattr(app.state, "discovery_started_at")
    original_started = getattr(app.state, "discovery_started_at", None)
    monkeypatch.setattr(routes, "should_persist_discovery_results", lambda request: False)
    object.__setattr__(routes.settings, "discovery_database_path", str(tmp_path / "route-test.db"))
    object.__setattr__(routes.settings, "portal_local_config_path", str(tmp_path / "portal.local.json"))
    object.__setattr__(routes.settings, "mcegold_cli_path", "")
    object.__setattr__(routes.settings, "connector_config_path", "configs/connector.config.json")
    object.__setattr__(routes.settings, "grafana_dashboard_url", "http://127.0.0.1:3000/d/test")
    object.__setattr__(routes.settings, "admin_controls_enabled", True)
    for attr in ("discovery_client", "discovery_session_id", "discovery_started_at"):
        if hasattr(app.state, attr):
            delattr(app.state, attr)
    try:
        yield
    finally:
        object.__setattr__(routes.settings, "discovery_database_path", original_db_path)
        object.__setattr__(routes.settings, "portal_local_config_path", original_config_path)
        object.__setattr__(routes.settings, "mcegold_cli_path", original_cli_path)
        object.__setattr__(routes.settings, "connector_config_path", original_connector_config_path)
        object.__setattr__(routes.settings, "grafana_dashboard_url", original_dashboard_url)
        object.__setattr__(routes.settings, "admin_controls_enabled", original_admin_controls_enabled)
        if had_client:
            app.state.discovery_client = original_client
        elif hasattr(app.state, "discovery_client"):
            delattr(app.state, "discovery_client")
        if had_session:
            app.state.discovery_session_id = original_session
        elif hasattr(app.state, "discovery_session_id"):
            delattr(app.state, "discovery_session_id")
        if had_started:
            app.state.discovery_started_at = original_started
        elif hasattr(app.state, "discovery_started_at"):
            delattr(app.state, "discovery_started_at")


def install_client(client: FakeCliClient) -> FakeCliClient:
    app.state.discovery_client = client
    return client


def start_discovery(test_client: TestClient, client: FakeCliClient | None = None) -> FakeCliClient:
    client = install_client(client or FakeCliClient())
    response = test_client.post("/discovery/start", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/discovery/sites"
    return client


def select_site_context(test_client: TestClient) -> None:
    response = test_client.post(
        "/discovery/select-site",
        data={"site_uuid": TAMPA, "site_name": "Tampa Plant", "site_type": "Plant"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def select_segment_context(test_client: TestClient) -> None:
    select_site_context(test_client)
    response = test_client.post(
        "/discovery/select-segment",
        data={
            "site_uuid": TAMPA,
            "segment_uuid": PUMP_TRAIN,
            "segment_name": "Pump Train P-101",
            "segment_type": "Pump Train",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def select_location_context(test_client: TestClient) -> None:
    select_segment_context(test_client)
    response = test_client.post(
        "/discovery/select-measurement-location",
        data={
            "site_uuid": TAMPA,
            "segment_uuid": PUMP_TRAIN,
            "location_uuid": MOTOR_DE,
            "location_name": "Motor DE",
            "location_type": "Bearing",
            "value_class": "Measure",
            "unit": "mm/s",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_home_and_settings_pages_render() -> None:
    with TestClient(app) as test_client:
        home = test_client.get("/")
        settings = test_client.get("/settings")

    assert home.status_code == 200
    assert "MCEGold Discovery Portal" in home.text
    assert settings.status_code == 200
    assert "Portal Settings" in settings.text
    assert "MCEGold CLI executable path" in settings.text


def test_discovery_pages_redirect_without_session() -> None:
    with TestClient(app) as test_client:
        response = test_client.get("/discovery/sites", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/?message=start_discovery"


def test_start_discovery_opens_cli_request_session() -> None:
    with TestClient(app) as test_client:
        client = start_discovery(test_client)

    assert client.opened == 1


def test_end_discovery_closes_cli_session_and_clears_context() -> None:
    with TestClient(app) as test_client:
        client = start_discovery(test_client)
        select_location_context(test_client)
        response = test_client.post("/discovery/end", follow_redirects=False)

    assert response.status_code == 303
    assert client.closed == ["session-1"]
    assert not hasattr(app.state, "discovery_session_id")


def test_sites_page_calls_get_sites_with_session_id() -> None:
    with TestClient(app) as test_client:
        client = start_discovery(test_client)
        response = test_client.get("/discovery/sites")

    assert response.status_code == 200
    assert "Tampa Plant" in response.text
    assert client.site_calls == ["session-1"]


def test_child_pages_require_selected_workflow_context() -> None:
    with TestClient(app) as test_client:
        start_discovery(test_client)
        response = test_client.get(f"/discovery/sites/{TAMPA}/segments")

    assert response.status_code == 409
    assert "Please navigate from Sites through the guided workflow" in response.text


def test_segments_page_search_passes_filters_to_cli() -> None:
    with TestClient(app) as test_client:
        client = start_discovery(test_client)
        select_site_context(test_client)
        response = test_client.get(
            f"/discovery/sites/{TAMPA}/segments",
            params={"searched": "true", "segment_type_uuid": "type-1", "max_items": "25"},
        )

    assert response.status_code == 200
    assert "Pump Train P-101" in response.text
    assert client.segment_calls == [
        {"site_uuid": TAMPA, "session_id": "session-1", "segment_type_uuid": "type-1", "max_items": 25}
    ]


def test_segments_page_without_search_does_not_call_cli() -> None:
    with TestClient(app) as test_client:
        client = start_discovery(test_client)
        select_site_context(test_client)
        response = test_client.get(f"/discovery/sites/{TAMPA}/segments")

    assert response.status_code == 200
    assert client.segment_calls == []


def test_measurement_locations_page_search_passes_filters_to_cli() -> None:
    with TestClient(app) as test_client:
        client = start_discovery(test_client)
        select_segment_context(test_client)
        response = test_client.get(
            f"/discovery/sites/{TAMPA}/segments/{PUMP_TRAIN}/measurement-locations",
            params={"searched": "true", "measurement_location_type_uuid": "location-type-1", "max_items": "25"},
        )

    assert response.status_code == 200
    assert "Motor DE" in response.text
    assert client.location_calls == [
        {
            "segment_uuid": PUMP_TRAIN,
            "session_id": "session-1",
            "measurement_location_type_uuid": "location-type-1",
            "max_items": 25,
        }
    ]


def test_measurements_page_search_passes_filters_to_cli() -> None:
    with TestClient(app) as test_client:
        client = start_discovery(test_client)
        select_location_context(test_client)
        response = test_client.get(
            f"/discovery/sites/{TAMPA}/segments/{PUMP_TRAIN}/measurement-locations/{MOTOR_DE}/measurements",
            params={
                "searched": "true",
                "recorded_from": "2026-01-01T00:00:00Z",
                "recorded_to": "2026-01-02T00:00:00Z",
                "max_items": "10",
            },
        )

    assert response.status_code == 200
    assert "2.41" in response.text
    assert client.measurement_calls == [
        {
            "location_uuid": MOTOR_DE,
            "session_id": "session-1",
            "segment_uuid": PUMP_TRAIN,
            "recorded_from": "2026-01-01T00:00:00Z",
            "recorded_to": "2026-01-02T00:00:00Z",
            "max_items": 10,
            "fallback_unit": "mm/s",
        }
    ]


def test_measurement_invalid_recorded_range_does_not_call_cli() -> None:
    with TestClient(app) as test_client:
        client = start_discovery(test_client)
        select_location_context(test_client)
        response = test_client.get(
            f"/discovery/sites/{TAMPA}/segments/{PUMP_TRAIN}/measurement-locations/{MOTOR_DE}/measurements",
            params={
                "searched": "true",
                "recorded_from": "2026-01-02T00:00:00Z",
                "recorded_to": "2026-01-01T00:00:00Z",
            },
        )

    assert response.status_code == 200
    assert "Recorded From must be earlier than or equal to Recorded To." in response.text
    assert client.measurement_calls == []


def test_settings_save_writes_current_local_config(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "portal.local.json"
    object.__setattr__(routes.settings, "portal_local_config_path", str(config_path))

    with TestClient(app) as test_client:
        response = test_client.post(
            "/settings",
            data={
                "mcegold_data_services_url": "https://example.test/mcegold",
                "mcegold_username": "demo-user",
                "mcegold_cli_path": r"C:\tools\MCEGold.Data.Services.Connector.Cli.exe",
                "connector_config_path": r"configs\connector.config.json",
                "discovery_database_path": r"data\demo.db",
                "grafana_dashboard_url": "http://127.0.0.1:3000/d/test",
            },
        )

    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert response.status_code == 200
    assert "Settings saved." in response.text
    assert saved["mcegoldDataServicesUrl"] == "https://example.test/mcegold"
    assert saved["mcegoldUsername"] == "demo-user"
    assert saved["mcegoldCliPath"] == r"C:\tools\MCEGold.Data.Services.Connector.Cli.exe"
    assert saved["connectorConfigPath"] == r"configs\connector.config.json"
    assert saved["discoveryDatabasePath"] == r"data\demo.db"
    assert saved["grafanaDashboardUrl"] == "http://127.0.0.1:3000/d/test"


def test_settings_save_rejects_missing_required_paths(tmp_path) -> None:
    config_path = tmp_path / "portal.local.json"
    object.__setattr__(routes.settings, "portal_local_config_path", str(config_path))

    with TestClient(app) as test_client:
        response = test_client.post(
            "/settings",
            data={
                "mcegold_cli_path": "",
                "connector_config_path": "",
                "discovery_database_path": "",
                "grafana_dashboard_url": "",
            },
        )

    assert response.status_code == 400
    assert "MCEGold CLI executable path is required." in response.text
    assert "Connector config path is required." in response.text
    assert "SQLite database path is required." in response.text
    assert "Grafana dashboard URL is required." in response.text
    assert not config_path.exists()


def test_cli_error_shows_friendly_alert() -> None:
    class FailingClient(FakeCliClient):
        def get_sites(self, session_id: str | None = None) -> list[Site]:
            raise CliDiscoveryError("The MCEGold CLI could not read the GetSites response.", command=["cli.exe"])

    with TestClient(app) as test_client:
        start_discovery(test_client, FailingClient())
        response = test_client.get("/discovery/sites")

    assert response.status_code == 200
    assert "The MCEGold CLI could not read the GetSites response." in response.text


def test_admin_controls_disabled_hides_settings_and_blocks_end_discovery() -> None:
    object.__setattr__(routes.settings, "admin_controls_enabled", False)

    with TestClient(app) as test_client:
        start_discovery(test_client)
        settings_response = test_client.get("/settings")
        end_response = test_client.post("/discovery/end")

    assert settings_response.status_code == 404
    assert end_response.status_code == 404




