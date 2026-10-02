import re
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.storage.application_settings import ApplicationSettingsRepository
from app.storage.database import initialize_database


@pytest.fixture
def portal_settings_retention_test(tmp_path):
    original_config_path = routes.settings.portal_local_config_path
    original_database_path = routes.settings.discovery_database_path
    had_client = hasattr(app.state, "discovery_client")
    original_client = getattr(app.state, "discovery_client", None)

    database_path = tmp_path / "retention-settings.db"
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


def test_data_retention_defaults_seeded_idempotently_and_preserve_existing_values(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    assert setting_row(db_path, "DataRetention.Enabled") == ("false", "Boolean")
    assert setting_row(db_path, "DataRetention.Days") == ("90", "Integer")

    repository = ApplicationSettingsRepository(db_path)
    repository.set_setting("DataRetention.Enabled", True)
    repository.set_setting("DataRetention.Days", 180)

    initialize_database(db_path)

    assert setting_row(db_path, "DataRetention.Enabled") == ("true", "Boolean")
    assert setting_row(db_path, "DataRetention.Days") == ("180", "Integer")


def test_settings_page_renders_data_retention_controls(portal_settings_retention_test) -> None:
    with TestClient(app) as test_client:
        response = test_client.get("/settings")

    assert response.status_code == 200
    assert "Data Retention" in response.text
    assert "Enable automatic data retention" in response.text
    assert "Measurement retention period" in response.text
    assert re.search(r'id="data_retention_days"[^>]*min="30"[^>]*max="730"[^>]*step="1"', response.text)
    assert re.search(r'id="data_retention_days"[^>]*value="90"', response.text)
    assert re.search(r'id="data_retention_enabled"[^>]*checked', response.text) is None


@pytest.mark.parametrize("days", [30, 90, 180, 730])
def test_settings_validation_accepts_retention_values(portal_settings_retention_test, days: int) -> None:
    with TestClient(app) as test_client:
        response = test_client.post(
            "/settings",
            data=settings_form(portal_settings_retention_test, data_retention_enabled=True, data_retention_days=str(days)),
        )

    assert response.status_code == 200
    assert "Settings saved." in response.text
    assert setting_row(portal_settings_retention_test, "DataRetention.Enabled") == ("true", "Boolean")
    assert setting_row(portal_settings_retention_test, "DataRetention.Days") == (str(days), "Integer")


@pytest.mark.parametrize("days", ["29", "731", "0", "-1", "", "abc", "90.5"])
def test_settings_validation_rejects_invalid_retention_values(
    portal_settings_retention_test,
    days: str,
) -> None:
    with TestClient(app) as test_client:
        insert_measurement_fact(portal_settings_retention_test, "measurement-before-invalid-save")
        before_count = fact_count(portal_settings_retention_test)

        response = test_client.post(
            "/settings",
            data=settings_form(portal_settings_retention_test, data_retention_enabled=True, data_retention_days=days),
        )

    assert response.status_code == 400
    assert "Settings were not saved." in response.text
    assert setting_row(portal_settings_retention_test, "DataRetention.Enabled") == ("false", "Boolean")
    assert setting_row(portal_settings_retention_test, "DataRetention.Days") == ("90", "Integer")
    assert fact_count(portal_settings_retention_test) == before_count


def test_data_retention_toggle_persists_without_deleting_measurements(portal_settings_retention_test) -> None:
    with TestClient(app) as test_client:
        insert_measurement_fact(portal_settings_retention_test, "measurement-before-toggle")
        before_count = fact_count(portal_settings_retention_test)

        enabled_response = test_client.post(
            "/settings",
            data=settings_form(portal_settings_retention_test, data_retention_enabled=True, data_retention_days="90"),
        )
        disabled_response = test_client.post(
            "/settings",
            data=settings_form(portal_settings_retention_test, data_retention_enabled=False, data_retention_days="90"),
        )

    assert enabled_response.status_code == 200
    assert disabled_response.status_code == 200
    assert setting_row(portal_settings_retention_test, "DataRetention.Enabled") == ("false", "Boolean")
    assert setting_row(portal_settings_retention_test, "DataRetention.Days") == ("90", "Integer")
    assert fact_count(portal_settings_retention_test) == before_count


def setting_row(database_path, setting_key: str) -> tuple[str | None, str]:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT SettingValue, ValueType
            FROM ApplicationSetting
            WHERE SettingKey = ?
            """,
            (setting_key,),
        ).fetchone()
    assert row is not None
    return row[0], row[1]


def settings_form(database_path, *, data_retention_enabled: bool, data_retention_days: str) -> dict[str, str]:
    form = {
        "application_settings_present": "1",
        "mcegold_cli_path": "tests\\fake-cli.exe",
        "connector_config_path": str(database_path.parent / "connector.config.json"),
        "discovery_database_path": str(database_path),
        "grafana_dashboard_url": "http://127.0.0.1:3000/d/test",
        "collector_enabled": "on",
        "collector_polling_interval_seconds": "15",
        "energy_cost_currency_uom_uuid": "",
        "energy_cost_rate_per_kwh": "",
        "data_retention_days": data_retention_days,
    }
    if data_retention_enabled:
        form["data_retention_enabled"] = "on"
    return form


def insert_measurement_fact(database_path, measurement_uuid: str) -> None:
    with sqlite3.connect(database_path) as connection:
        location_key = connection.execute(
            """
            INSERT INTO DimMeasurementLocation(
                MeasurementLocationUuid,
                MeasurementLocationName,
                ValueClass,
                FirstSeenUtc,
                LastSeenUtc
            )
            VALUES (?, 'Retention Test Location', 'Number', '2026-08-20T12:00:00Z', '2026-08-20T12:00:00Z')
            """,
            (f"{measurement_uuid}-location",),
        ).lastrowid
        connection.execute(
            """
            INSERT INTO FactMeasurement(
                MeasurementUuid,
                MeasurementLocationKey,
                MeasurementLocationUuid,
                MeasurementTimestampUtc,
                NumericValue,
                InsertedUtc
            )
            VALUES (?, ?, ?, '2026-01-01T00:00:00Z', 42.0, '2026-08-20T12:00:01Z')
            """,
            (measurement_uuid, location_key, f"{measurement_uuid}-location"),
        )
        connection.commit()


def fact_count(database_path) -> int:
    with sqlite3.connect(database_path) as connection:
        return int(connection.execute("SELECT COUNT(*) FROM FactMeasurement").fetchone()[0])
