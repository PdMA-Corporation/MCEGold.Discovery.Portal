import sqlite3

from app.storage.collector_runtime_status import CollectorRuntimeStatusRepository
from app.storage.database import initialize_database


def test_missing_publication_collector_runtime_status_returns_none(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    status = CollectorRuntimeStatusRepository(db_path).get_publication_collector_status()

    assert status is None


def test_stored_publication_collector_runtime_status_returns_raw_model(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO CollectorRuntimeStatus (
                CollectorId,
                InstanceId,
                StartedUtc,
                LastHeartbeatUtc,
                RuntimeState,
                LastPollUtc,
                LastPublicationUtc,
                LastErrorUtc,
                LastError
            )
            VALUES (
                'publication-collector',
                'instance-1',
                '2026-08-20T12:00:00Z',
                '2026-08-20T12:00:05Z',
                'Running',
                '2026-08-20T12:00:04Z',
                '2026-08-20T12:00:03Z',
                '2026-08-20T12:00:02Z',
                'temporary failure'
            )
            """
        )
        connection.commit()

    status = CollectorRuntimeStatusRepository(db_path).get_publication_collector_status()

    assert status is not None
    assert status.collector_id == "publication-collector"
    assert status.instance_id == "instance-1"
    assert status.started_utc == "2026-08-20T12:00:00Z"
    assert status.last_heartbeat_utc == "2026-08-20T12:00:05Z"
    assert status.runtime_state == "Running"
    assert status.last_poll_utc == "2026-08-20T12:00:04Z"
    assert status.last_publication_utc == "2026-08-20T12:00:03Z"
    assert status.last_error_utc == "2026-08-20T12:00:02Z"
    assert status.last_error == "temporary failure"


def test_publication_collector_runtime_status_allows_nullable_optional_fields(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO CollectorRuntimeStatus (
                CollectorId,
                InstanceId,
                StartedUtc,
                LastHeartbeatUtc,
                RuntimeState
            )
            VALUES (
                'publication-collector',
                'instance-1',
                '2026-08-20T12:00:00Z',
                '2026-08-20T12:00:05Z',
                'Idle'
            )
            """
        )
        connection.commit()

    status = CollectorRuntimeStatusRepository(db_path).get_publication_collector_status()

    assert status is not None
    assert status.runtime_state == "Idle"
    assert status.last_poll_utc is None
    assert status.last_publication_utc is None
    assert status.last_error_utc is None
    assert status.last_error is None
