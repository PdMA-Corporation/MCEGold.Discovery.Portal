import sqlite3
from datetime import UTC, datetime

from app.services.collector_runtime_status_service import (
    derive_collector_status,
    get_publication_collector_status,
    offline_after_seconds,
)
from app.storage.application_settings import ApplicationSettingsRepository
from app.storage.collector_runtime_status import CollectorRuntimeStatus
from app.storage.database import initialize_database


NOW = datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC)


def raw_status(
    runtime_state: str = "Running",
    last_heartbeat_utc: str = "2026-08-20T11:59:30Z",
) -> CollectorRuntimeStatus:
    return CollectorRuntimeStatus(
        collector_id="publication-collector",
        instance_id="instance-1",
        started_utc="2026-08-20T11:00:00Z",
        last_heartbeat_utc=last_heartbeat_utc,
        runtime_state=runtime_state,
        last_poll_utc="2026-08-20T11:59:25Z",
        last_publication_utc="2026-08-20T11:59:20Z",
        last_error_utc="2026-08-20T11:58:00Z",
        last_error="temporary failure",
    )


def test_missing_runtime_row_is_offline_when_enabled() -> None:
    status = derive_collector_status(None, enabled=True, polling_interval_seconds=15, now_utc=NOW)

    assert status.enabled is True
    assert status.runtime_status == "Offline"
    assert status.last_seen_utc is None
    assert status.last_publication_utc is None
    assert status.last_error is None


def test_missing_runtime_row_is_offline_when_disabled() -> None:
    status = derive_collector_status(None, enabled=False, polling_interval_seconds=15, now_utc=NOW)

    assert status.enabled is False
    assert status.runtime_status == "Offline"


def test_fresh_heartbeat_uses_stored_running_state() -> None:
    status = derive_collector_status(raw_status("Running"), enabled=False, polling_interval_seconds=15, now_utc=NOW)

    assert status.enabled is False
    assert status.runtime_status == "Running"


def test_fresh_heartbeat_uses_stored_idle_state() -> None:
    status = derive_collector_status(raw_status("Idle"), enabled=True, polling_interval_seconds=15, now_utc=NOW)

    assert status.enabled is True
    assert status.runtime_status == "Idle"


def test_fresh_heartbeat_uses_stored_error_state() -> None:
    status = derive_collector_status(raw_status("Error"), enabled=True, polling_interval_seconds=15, now_utc=NOW)

    assert status.runtime_status == "Error"
    assert status.last_error == "temporary failure"


def test_stale_heartbeat_is_offline_for_any_stored_state() -> None:
    for runtime_state in ("Running", "Idle", "Error"):
        status = derive_collector_status(
            raw_status(runtime_state, last_heartbeat_utc="2026-08-20T11:58:29Z"),
            enabled=True,
            polling_interval_seconds=15,
            now_utc=NOW,
        )

        assert status.runtime_status == "Offline"


def test_polling_interval_controls_offline_timeout_after_floor() -> None:
    assert offline_after_seconds(15) == 90
    assert offline_after_seconds(60) == 240

    status = derive_collector_status(
        raw_status("Running", last_heartbeat_utc="2026-08-20T11:56:30Z"),
        enabled=True,
        polling_interval_seconds=60,
        now_utc=NOW,
    )

    assert status.runtime_status == "Running"


def test_invalid_heartbeat_timestamp_is_offline() -> None:
    status = derive_collector_status(
        raw_status("Running", last_heartbeat_utc="not-a-date"),
        enabled=True,
        polling_interval_seconds=15,
        now_utc=NOW,
    )

    assert status.runtime_status == "Offline"
    assert status.last_seen_utc is None


def test_naive_heartbeat_timestamp_is_offline() -> None:
    status = derive_collector_status(
        raw_status("Running", last_heartbeat_utc="2026-08-20T11:59:30"),
        enabled=True,
        polling_interval_seconds=15,
        now_utc=NOW,
    )

    assert status.runtime_status == "Offline"
    assert status.last_seen_utc is None


def test_application_settings_are_combined_with_runtime_status(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)
    ApplicationSettingsRepository(db_path).set_setting("Collector.Enabled", False)
    ApplicationSettingsRepository(db_path).set_setting("Collector.PollingIntervalSeconds", 60)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO CollectorRuntimeStatus (
                CollectorId,
                InstanceId,
                StartedUtc,
                LastHeartbeatUtc,
                RuntimeState,
                LastPublicationUtc
            )
            VALUES (
                'publication-collector',
                'instance-1',
                '2026-08-20T11:00:00Z',
                '2026-08-20T11:56:30Z',
                'Running',
                '2026-08-20T11:56:00Z'
            )
            """
        )
        connection.commit()

    status = get_publication_collector_status(db_path, now_utc=NOW)

    assert status.enabled is False
    assert status.runtime_status == "Running"
    assert status.last_seen_utc == datetime(2026, 8, 20, 11, 56, 30, tzinfo=UTC)
    assert status.last_publication_utc == datetime(2026, 8, 20, 11, 56, 0, tzinfo=UTC)
