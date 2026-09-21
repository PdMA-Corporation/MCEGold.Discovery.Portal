from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.storage.application_settings import ApplicationSettingsRepository
from app.storage.collector_runtime_status import CollectorRuntimeStatus, CollectorRuntimeStatusRepository


DEFAULT_COLLECTOR_POLLING_INTERVAL_SECONDS = 15
OFFLINE_TIMEOUT_FLOOR_SECONDS = 90
SUPPORTED_RUNTIME_STATUSES = {"Running", "Idle", "Error"}


@dataclass(frozen=True)
class CollectorStatusView:
    enabled: bool
    runtime_status: str
    last_seen_utc: datetime | None
    last_publication_utc: datetime | None
    last_error_utc: datetime | None
    last_error: str | None


def get_publication_collector_status(
    database_path: str | Path,
    now_utc: datetime | None = None,
) -> CollectorStatusView:
    settings_repository = ApplicationSettingsRepository(database_path)
    raw_status = CollectorRuntimeStatusRepository(database_path).get_publication_collector_status()
    enabled = settings_repository.get_boolean("Collector.Enabled") is True
    polling_interval = (
        settings_repository.get_integer("Collector.PollingIntervalSeconds")
        or DEFAULT_COLLECTOR_POLLING_INTERVAL_SECONDS
    )
    return derive_collector_status(
        raw_status,
        enabled=enabled,
        polling_interval_seconds=polling_interval,
        now_utc=now_utc,
    )


def derive_collector_status(
    raw_status: CollectorRuntimeStatus | None,
    enabled: bool,
    polling_interval_seconds: int | float,
    now_utc: datetime | None = None,
) -> CollectorStatusView:
    effective_now_utc = _as_utc(now_utc or datetime.now(UTC))
    if raw_status is None:
        return CollectorStatusView(
            enabled=enabled,
            runtime_status="Offline",
            last_seen_utc=None,
            last_publication_utc=None,
            last_error_utc=None,
            last_error=None,
        )

    last_seen = parse_utc_timestamp(raw_status.last_heartbeat_utc)
    if (
        last_seen is None
        or raw_status.runtime_state not in SUPPORTED_RUNTIME_STATUSES
        or effective_now_utc - last_seen > timedelta(seconds=offline_after_seconds(polling_interval_seconds))
    ):
        runtime_status = "Offline"
    else:
        runtime_status = raw_status.runtime_state

    return CollectorStatusView(
        enabled=enabled,
        runtime_status=runtime_status,
        last_seen_utc=last_seen,
        last_publication_utc=parse_utc_timestamp(raw_status.last_publication_utc),
        last_error_utc=parse_utc_timestamp(raw_status.last_error_utc),
        last_error=raw_status.last_error,
    )


def offline_after_seconds(polling_interval_seconds: int | float) -> float:
    return max(OFFLINE_TIMEOUT_FLOOR_SECONDS, float(polling_interval_seconds) * 4)


def parse_utc_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return _as_utc(parsed)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware.")
    return value.astimezone(UTC)
