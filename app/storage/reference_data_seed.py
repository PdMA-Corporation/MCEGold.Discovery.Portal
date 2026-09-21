from __future__ import annotations

import hashlib
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.models import ReferenceDataEntry
from app.services.reference_data_service import ReferenceDataService


logger = logging.getLogger("mcegold.discovery.storage.reference_data")

REFERENCE_DATA_SEEDER_VERSION = 3
REFERENCE_CLASSES = {
    "SiteType",
    "SegmentType",
    "MeasurementLocationType",
    "UnitOfMeasure",
    "UOMQuantity",
}
REFERENCE_TABLES = (
    "DimSiteType",
    "DimSegmentType",
    "DimMeasurementLocationType",
    "DimUnit",
    "DimUomQuantity",
)


@dataclass(frozen=True)
class ReferenceDataSeedResult:
    source_file_name: str
    source_file_hash: str | None
    entity_count: int
    import_version: int | None
    seeded: bool
    reason: str
    counts: dict[str, int]


class ReferenceDataInitializationError(RuntimeError):
    pass


def seed_reference_data(
    db_path: str | Path,
    reference_data: ReferenceDataService,
) -> ReferenceDataSeedResult:
    return ReferenceDataSeeder(db_path, reference_data).seed()


class ReferenceDataSeeder:
    def __init__(
        self,
        db_path: str | Path,
        reference_data: ReferenceDataService,
    ) -> None:
        self.db_path = Path(db_path)
        self.reference_data = reference_data

    def seed(self) -> ReferenceDataSeedResult:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            seeded = is_reference_data_seeded(connection)
            if seeded:
                latest = _latest_import(connection)
                return ReferenceDataSeedResult(
                    source_file_name=str(latest["SourceFileName"] or self.reference_data.file_path),
                    source_file_hash=latest["SourceFileHash"],
                    entity_count=int(latest["EntityCount"] or 0),
                    import_version=int(latest["ImportVersion"]),
                    seeded=False,
                    reason="already_seeded",
                    counts=_reference_counts(connection),
                )

        source_path = Path(self.reference_data.file_path)
        if not source_path.exists():
            raise ReferenceDataInitializationError(
                f"Reference data XML file is required to initialize an unseeded database: {source_path}"
            )

        source_hash = _file_hash(source_path)
        if not self.reference_data.is_loaded():
            self.reference_data.load()
        if not self.reference_data.is_loaded():
            raise ReferenceDataInitializationError(
                f"Reference data XML failed to load from {source_path}: {self.reference_data.warning or self.reference_data.status}"
            )

        entries = self.reference_data.get_all_entries()
        reference_entries = [entry for entry in entries if entry.class_name in REFERENCE_CLASSES]

        with sqlite3.connect(self.db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            try:
                _seed_info_sources(connection, entries)
                _seed_site_types(connection, _entries_by_class(entries, "SiteType"))
                _seed_segment_types(connection, _entries_by_class(entries, "SegmentType"))
                _seed_measurement_location_types(connection, _entries_by_class(entries, "MeasurementLocationType"))
                _seed_uom_quantities(connection, _entries_by_class(entries, "UOMQuantity"))
                _seed_units(connection, _entries_by_class(entries, "UnitOfMeasure"))
                _seed_uom_quantities(connection, _entries_by_class(entries, "UOMQuantity"))
                counts = _reference_counts(connection)
                empty_tables = [table_name for table_name, count in counts.items() if count == 0]
                if empty_tables:
                    raise ReferenceDataInitializationError(
                        "Reference data import did not populate required reference tables from "
                        f"{source_path}: " + ", ".join(empty_tables)
                    )
                import_version = max(_current_import_version(connection) + 1, REFERENCE_DATA_SEEDER_VERSION)
                connection.execute(
                    """
                    INSERT INTO ReferenceDataImport (
                        SourceFileName,
                        SourceFileHash,
                        ImportedUtc,
                        EntityCount,
                        ImportVersion
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(source_path),
                        source_hash,
                        _utc_now(),
                        len(reference_entries),
                        import_version,
                    ),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

        logger.info("Seeded CCOM reference data source=%s counts=%s", source_path, counts)
        return ReferenceDataSeedResult(
            source_file_name=str(source_path),
            source_file_hash=source_hash,
            entity_count=len(reference_entries),
            import_version=import_version,
            seeded=True,
            reason="seeded",
            counts=counts,
        )


def is_reference_data_seeded(connection: sqlite3.Connection) -> bool:
    latest = _latest_import(connection)
    if latest is None or int(latest["ImportVersion"] or 0) < REFERENCE_DATA_SEEDER_VERSION:
        return False
    counts = _reference_counts(connection)
    empty_tables = [table_name for table_name, count in counts.items() if count == 0]
    if empty_tables:
        raise ReferenceDataInitializationError(
            "Reference data import marker exists, but required reference tables are empty: "
            + ", ".join(empty_tables)
        )
    return True


def _entries_by_class(entries: Iterable[ReferenceDataEntry], class_name: str) -> list[ReferenceDataEntry]:
    return [entry for entry in entries if entry.class_name == class_name]


def _seed_info_sources(connection: sqlite3.Connection, entries: Iterable[ReferenceDataEntry]) -> None:
    explicit = _entries_by_class(entries, "InfoSource")
    rows_by_uuid: dict[str, tuple[str, str | None, str, str]] = {}
    now = _utc_now()
    for entry in explicit:
        rows_by_uuid[entry.uuid] = (
            entry.uuid,
            entry.short_name or entry.uuid,
            now,
            now,
        )
    if not rows_by_uuid:
        return
    connection.executemany(
        """
        INSERT INTO DimInfoSource (
            InfoSourceUuid,
            ShortName,
            FirstSeenUtc,
            LastSeenUtc
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(InfoSourceUuid) DO UPDATE SET
            ShortName = COALESCE(excluded.ShortName, DimInfoSource.ShortName),
            LastSeenUtc = excluded.LastSeenUtc
        """,
        list(rows_by_uuid.values()),
    )


def _seed_site_types(connection: sqlite3.Connection, entries: Iterable[ReferenceDataEntry]) -> None:
    rows = [
        (
            entry.uuid,
            entry.short_name or entry.uuid,
            entry.info_source_uuid,
            _info_source_key(connection, entry.info_source_uuid),
        )
        for entry in entries
    ]
    connection.executemany(
        """
        INSERT INTO DimSiteType (
            SiteTypeUuid,
            ShortName,
            InfoSourceUuid,
            InfoSourceKey
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(SiteTypeUuid) DO UPDATE SET
            ShortName = excluded.ShortName,
            InfoSourceUuid = COALESCE(excluded.InfoSourceUuid, DimSiteType.InfoSourceUuid),
            InfoSourceKey = COALESCE(excluded.InfoSourceKey, DimSiteType.InfoSourceKey)
        """,
        rows,
    )


def _seed_segment_types(connection: sqlite3.Connection, entries: Iterable[ReferenceDataEntry]) -> None:
    rows = []
    for entry in entries:
        rows.append(
            (
                entry.uuid,
                entry.short_name or entry.uuid,
                entry.info_source_uuid,
                _info_source_key(connection, entry.info_source_uuid),
            )
        )
    connection.executemany(
        """
        INSERT INTO DimSegmentType (
            SegmentTypeUuid,
            ShortName,
            InfoSourceUuid,
            InfoSourceKey
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(SegmentTypeUuid) DO UPDATE SET
            ShortName = excluded.ShortName,
            InfoSourceUuid = COALESCE(excluded.InfoSourceUuid, DimSegmentType.InfoSourceUuid),
            InfoSourceKey = COALESCE(excluded.InfoSourceKey, DimSegmentType.InfoSourceKey)
        """,
        rows,
    )


def _seed_measurement_location_types(connection: sqlite3.Connection, entries: Iterable[ReferenceDataEntry]) -> None:
    rows = []
    for entry in entries:
        rows.append(
            (
                entry.uuid,
                entry.short_name or entry.uuid,
                entry.uom_quantity,
                entry.info_source_uuid,
                _info_source_key(connection, entry.info_source_uuid),
            )
        )
    connection.executemany(
        """
        INSERT INTO DimMeasurementLocationType (
            MeasurementLocationTypeUuid,
            ShortName,
            UomQuantityUuid,
            InfoSourceUuid,
            InfoSourceKey
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(MeasurementLocationTypeUuid) DO UPDATE SET
            ShortName = excluded.ShortName,
            UomQuantityUuid = COALESCE(excluded.UomQuantityUuid, DimMeasurementLocationType.UomQuantityUuid),
            InfoSourceUuid = COALESCE(excluded.InfoSourceUuid, DimMeasurementLocationType.InfoSourceUuid),
            InfoSourceKey = COALESCE(excluded.InfoSourceKey, DimMeasurementLocationType.InfoSourceKey)
        """,
        rows,
    )


def _seed_units(connection: sqlite3.Connection, entries: Iterable[ReferenceDataEntry]) -> None:
    rows = [
        (
            entry.uuid,
            entry.short_name or entry.uuid,
            entry.uom_quantity,
            _uom_quantity_key(connection, entry.uom_quantity),
            _to_float(entry.conversion_scale),
            _to_float(entry.conversion_offset),
            entry.info_source_uuid,
            _info_source_key(connection, entry.info_source_uuid),
        )
        for entry in entries
    ]
    connection.executemany(
        """
        INSERT INTO DimUnit (
            UnitUuid,
            ShortName,
            UomQuantityUuid,
            UomQuantityKey,
            ConversionScale,
            ConversionOffset,
            InfoSourceUuid,
            InfoSourceKey
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(UnitUuid) DO UPDATE SET
            ShortName = excluded.ShortName,
            UomQuantityUuid = COALESCE(excluded.UomQuantityUuid, DimUnit.UomQuantityUuid),
            UomQuantityKey = COALESCE(excluded.UomQuantityKey, DimUnit.UomQuantityKey),
            ConversionScale = COALESCE(excluded.ConversionScale, DimUnit.ConversionScale),
            ConversionOffset = COALESCE(excluded.ConversionOffset, DimUnit.ConversionOffset),
            InfoSourceUuid = COALESCE(excluded.InfoSourceUuid, DimUnit.InfoSourceUuid),
            InfoSourceKey = COALESCE(excluded.InfoSourceKey, DimUnit.InfoSourceKey)
        """,
        rows,
    )


def _seed_uom_quantities(connection: sqlite3.Connection, entries: Iterable[ReferenceDataEntry]) -> None:
    rows = [
        (
            entry.uuid,
            entry.short_name or entry.uuid,
            entry.reference_unit_of_measure,
            _unit_key(connection, entry.reference_unit_of_measure),
            entry.info_source_uuid,
            _info_source_key(connection, entry.info_source_uuid),
        )
        for entry in entries
    ]
    connection.executemany(
        """
        INSERT INTO DimUomQuantity (
            UomQuantityUuid,
            ShortName,
            ReferenceUnitUuid,
            ReferenceUnitKey,
            InfoSourceUuid,
            InfoSourceKey
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(UomQuantityUuid) DO UPDATE SET
            ShortName = excluded.ShortName,
            ReferenceUnitUuid = COALESCE(excluded.ReferenceUnitUuid, DimUomQuantity.ReferenceUnitUuid),
            ReferenceUnitKey = COALESCE(excluded.ReferenceUnitKey, DimUomQuantity.ReferenceUnitKey),
            InfoSourceUuid = COALESCE(excluded.InfoSourceUuid, DimUomQuantity.InfoSourceUuid),
            InfoSourceKey = COALESCE(excluded.InfoSourceKey, DimUomQuantity.InfoSourceKey)
        """,
        rows,
    )


def _latest_import(connection: sqlite3.Connection) -> sqlite3.Row | None:
    original_row_factory = connection.row_factory
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(
            """
            SELECT SourceFileName, SourceFileHash, EntityCount, ImportVersion, ImportedUtc
            FROM ReferenceDataImport
            WHERE ImportVersion >= ?
            ORDER BY ReferenceDataImportKey DESC
            LIMIT 1
            """,
            (REFERENCE_DATA_SEEDER_VERSION,),
        ).fetchone()
    finally:
        connection.row_factory = original_row_factory


def _current_import_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT COALESCE(MAX(ImportVersion), 0) FROM ReferenceDataImport").fetchone()
    return int(row[0] or 0)


def _reference_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {table_name: _table_count(connection, table_name) for table_name in REFERENCE_TABLES}


def _table_count(connection: sqlite3.Connection, table_name: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
    return int(row[0])


def _info_source_key(connection: sqlite3.Connection, uuid: str | None) -> int | None:
    if not uuid:
        return None
    row = connection.execute(
        "SELECT InfoSourceKey FROM DimInfoSource WHERE InfoSourceUuid = ?",
        (uuid,),
    ).fetchone()
    return int(row[0]) if row else None


def _uom_quantity_key(connection: sqlite3.Connection, uuid: str | None) -> int | None:
    if not uuid:
        return None
    row = connection.execute(
        "SELECT UomQuantityKey FROM DimUomQuantity WHERE UomQuantityUuid = ?",
        (uuid,),
    ).fetchone()
    return int(row[0]) if row else None


def _unit_key(connection: sqlite3.Connection, uuid: str | None) -> int | None:
    if not uuid:
        return None
    row = connection.execute(
        "SELECT UnitKey FROM DimUnit WHERE UnitUuid = ?",
        (uuid,),
    ).fetchone()
    return int(row[0]) if row else None


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _to_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
