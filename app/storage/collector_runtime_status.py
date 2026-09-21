from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


PUBLICATION_COLLECTOR_ID = "publication-collector"


@dataclass(frozen=True)
class CollectorRuntimeStatus:
    collector_id: str
    instance_id: str
    started_utc: str
    last_heartbeat_utc: str
    runtime_state: str
    last_poll_utc: str | None
    last_publication_utc: str | None
    last_error_utc: str | None
    last_error: str | None


class CollectorRuntimeStatusRepository:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def get(self, collector_id: str = PUBLICATION_COLLECTOR_ID) -> CollectorRuntimeStatus | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    CollectorId,
                    InstanceId,
                    StartedUtc,
                    LastHeartbeatUtc,
                    RuntimeState,
                    LastPollUtc,
                    LastPublicationUtc,
                    LastErrorUtc,
                    LastError
                FROM CollectorRuntimeStatus
                WHERE CollectorId = ?
                """,
                (collector_id,),
            ).fetchone()
        return _status_from_row(row) if row else None

    def get_publication_collector_status(self) -> CollectorRuntimeStatus | None:
        return self.get(PUBLICATION_COLLECTOR_ID)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection


def _status_from_row(row: sqlite3.Row) -> CollectorRuntimeStatus:
    return CollectorRuntimeStatus(
        collector_id=row["CollectorId"],
        instance_id=row["InstanceId"],
        started_utc=row["StartedUtc"],
        last_heartbeat_utc=row["LastHeartbeatUtc"],
        runtime_state=row["RuntimeState"],
        last_poll_utc=row["LastPollUtc"],
        last_publication_utc=row["LastPublicationUtc"],
        last_error_utc=row["LastErrorUtc"],
        last_error=row["LastError"],
    )
