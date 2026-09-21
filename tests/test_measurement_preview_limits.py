import re

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.models import Measurement, MeasurementLocation, Segment, Site
from app.services.mcegold_cli_discovery_client import MceGoldCliDiscoveryClient


SITE_UUID = "site-preview"
SEGMENT_UUID = "segment-preview"
LOCATION_UUID = "location-preview"
MEASUREMENTS_PATH = (
    f"/discovery/sites/{SITE_UUID}/segments/{SEGMENT_UUID}"
    f"/measurement-locations/{LOCATION_UUID}/measurements"
)


class FrozenDateTime(routes.datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 8, 20, 12, 34, 56, tzinfo=routes.timezone.utc)
        return value if tz is None else value.astimezone(tz)


class PreviewLimitClient(MceGoldCliDiscoveryClient):
    def __init__(self) -> None:
        super().__init__("cli.exe", "config.json")
        self.measurement_calls: list[dict[str, object]] = []

    def open_request_session(self) -> str:
        return "session-preview"

    def get_sites(self, session_id=None):
        return [
            Site(
                site_uuid=SITE_UUID,
                site_name="Preview Site",
                site_type="Plant",
                status="Active",
                region="",
                description="",
            )
        ]

    def get_segments(self, site_uuid=None, session_id=None, segment_type_uuid=None, max_items=None):
        return [
            Segment(
                segment_uuid=SEGMENT_UUID,
                site_uuid=SITE_UUID,
                segment_name="Preview Segment",
                segment_type="Line",
                status="Active",
                description="",
            )
        ]

    def get_measurement_locations(self, segment_uuid=None, session_id=None, measurement_location_type_uuid=None, max_items=None):
        return [
            MeasurementLocation(
                location_uuid=LOCATION_UUID,
                segment_uuid=SEGMENT_UUID,
                location_name="Preview Location",
                location_type="Bearing",
                value_class="Measure",
                unit="mm/s",
            )
        ]

    def get_measurements(
        self,
        location_uuid=None,
        session_id=None,
        segment_uuid=None,
        recorded_from=None,
        recorded_to=None,
        max_items=None,
        fallback_unit=None,
    ):
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
                measurement_uuid="measurement-preview",
                location_uuid=location_uuid,
                measurement_name="Preview Measurement",
                measurement_type="Measure",
                value=1.25,
                unit=fallback_unit or "",
                timestamp_utc=routes.datetime(2026, 1, 1, tzinfo=routes.timezone.utc),
                status="Unknown",
            )
        ]


@pytest.fixture
def preview_client(tmp_path):
    original_database_path = routes.settings.discovery_database_path
    had_client = hasattr(app.state, "discovery_client")
    original_client = getattr(app.state, "discovery_client", None)

    client = PreviewLimitClient()
    object.__setattr__(routes.settings, "discovery_database_path", str(tmp_path / "preview-limit.db"))
    app.state.discovery_client = client

    try:
        yield client
    finally:
        object.__setattr__(routes.settings, "discovery_database_path", original_database_path)
        if had_client:
            app.state.discovery_client = original_client
        elif hasattr(app.state, "discovery_client"):
            delattr(app.state, "discovery_client")


def test_measurement_preview_default_and_ui_options(monkeypatch, preview_client) -> None:
    monkeypatch.setattr(routes, "datetime", FrozenDateTime)

    with TestClient(app) as test_client:
        select_measurement_location(test_client)
        response = test_client.get(MEASUREMENTS_PATH)

    assert response.status_code == 200
    assert 'id="max_items"' in response.text
    options = re.findall(r'<option value="(\d+)"', response.text)
    assert options == ["10", "25", "50"]
    assert 'value="10" selected' in response.text
    assert 'value="100"' not in response.text
    assert 'value="250"' not in response.text
    assert 'id="recorded_from" name="recorded_from" value="2026-08-19T12:34"' in response.text
    assert 'id="recorded_to" name="recorded_to" value="2026-08-20T12:34"' in response.text


@pytest.mark.parametrize("max_items", ["10", "25", "49", "50"])
def test_measurement_preview_accepts_approved_max_items(preview_client, max_items: str) -> None:
    with TestClient(app) as test_client:
        select_measurement_location(test_client)
        response = test_client.get(MEASUREMENTS_PATH, params={"searched": "true", "max_items": max_items})

    assert response.status_code == 200
    assert "1.25" in response.text
    assert preview_client.measurement_calls[-1]["max_items"] == int(max_items)


def test_measurement_preview_preserves_selected_max_items_after_search(preview_client) -> None:
    with TestClient(app) as test_client:
        select_measurement_location(test_client)
        response = test_client.get(MEASUREMENTS_PATH, params={"searched": "true", "max_items": "25"})

    assert response.status_code == 200
    assert 'value="25" selected' in response.text
    assert preview_client.measurement_calls[-1]["max_items"] == 25


def test_measurement_preview_preserves_user_entered_dates_after_search(preview_client) -> None:
    with TestClient(app) as test_client:
        select_measurement_location(test_client)
        response = test_client.get(
            MEASUREMENTS_PATH,
            params={
                "searched": "true",
                "recorded_from": "2026-08-18T09:15",
                "recorded_to": "2026-08-19T10:45",
                "max_items": "10",
            },
        )

    assert response.status_code == 200
    assert 'id="recorded_from" name="recorded_from" value="2026-08-18T09:15"' in response.text
    assert 'id="recorded_to" name="recorded_to" value="2026-08-19T10:45"' in response.text
    assert preview_client.measurement_calls[-1]["recorded_from"] == "2026-08-18T09:15:00Z"
    assert preview_client.measurement_calls[-1]["recorded_to"] == "2026-08-19T10:45:00Z"


@pytest.mark.parametrize(
    ("max_items", "message"),
    [
        ("51", "Max Items cannot exceed 50."),
        ("100", "Max Items cannot exceed 50."),
        ("250", "Max Items cannot exceed 50."),
        ("0", "Max Items must be greater than 0."),
        ("-1", "Max Items must be greater than 0."),
        ("abc", "Max Items must be a valid integer."),
    ],
)
def test_measurement_preview_rejects_invalid_or_tampered_max_items(
    preview_client,
    max_items: str,
    message: str,
) -> None:
    with TestClient(app) as test_client:
        select_measurement_location(test_client)
        response = test_client.get(MEASUREMENTS_PATH, params={"searched": "true", "max_items": max_items})

    assert response.status_code == 200
    assert message in response.text
    assert preview_client.measurement_calls == []


def test_measurement_preview_rejects_tampered_request_before_service_layer(preview_client) -> None:
    with TestClient(app) as test_client:
        select_measurement_location(test_client)
        response = test_client.get(
            MEASUREMENTS_PATH,
            params={"searched": "true", "max_items": "1000", "last_n_data": "1000"},
        )

    assert response.status_code == 200
    assert "Max Items cannot exceed 50." in response.text
    assert preview_client.measurement_calls == []


def select_measurement_location(test_client: TestClient) -> None:
    response = test_client.post("/discovery/start", follow_redirects=False)
    assert response.status_code == 303
    response = test_client.post(
        "/discovery/select-site",
        data={"site_uuid": SITE_UUID, "site_name": "Preview Site", "site_type": "Plant"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    response = test_client.post(
        "/discovery/select-segment",
        data={
            "site_uuid": SITE_UUID,
            "segment_uuid": SEGMENT_UUID,
            "segment_name": "Preview Segment",
            "segment_type": "Line",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    response = test_client.post(
        "/discovery/select-measurement-location",
        data={
            "site_uuid": SITE_UUID,
            "segment_uuid": SEGMENT_UUID,
            "location_uuid": LOCATION_UUID,
            "location_name": "Preview Location",
            "location_type": "Bearing",
            "value_class": "Measure",
            "unit": "mm/s",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
