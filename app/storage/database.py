from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.storage.application_settings import (
    create_application_setting_table,
    seed_default_application_settings,
)


CURRENT_SCHEMA_VERSION = 17
DEFAULT_DATABASE_PATH = Path("data/discovery_portal.db")

logger = logging.getLogger("mcegold.discovery.storage")


class UnsupportedDatabaseSchemaError(RuntimeError):
    pass


@dataclass(frozen=True)
class DatabaseInitializationResult:
    db_path: Path
    current_version: int
    migrations_applied: tuple[int, ...]


@dataclass(frozen=True)
class FactMeasurementUnitRepairResult:
    repaired_count: int
    unresolved_count: int


def initialize_database(db_path: str | Path = DEFAULT_DATABASE_PATH) -> DatabaseInitializationResult:
    path = Path(db_path)
    database_existed = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Initializing local discovery database path=%s", path)
    initialization_failed = False
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")

        if database_existed:
            current_version = _read_existing_schema_version(connection)
            logger.info("Current local discovery database schema version=%s", current_version)
            if current_version < CURRENT_SCHEMA_VERSION:
                raise UnsupportedDatabaseSchemaError(
                    "Existing local discovery database schema version "
                    f"{current_version} is older than supported release schema version "
                    f"{CURRENT_SCHEMA_VERSION}. Pre-release schema upgrades are not supported."
                )
            if current_version > CURRENT_SCHEMA_VERSION:
                raise UnsupportedDatabaseSchemaError(
                    "Existing local discovery database schema version "
                    f"{current_version} is newer than supported release schema version "
                    f"{CURRENT_SCHEMA_VERSION}."
                )
        else:
            current_version = CURRENT_SCHEMA_VERSION
            connection.execute("BEGIN IMMEDIATE")

        _create_current_schema(connection)
        _create_current_indexes(connection)
        _create_reporting_views(connection)
        if not database_existed:
            _record_current_schema_version(connection)
        seed_default_application_settings(connection)
        repair_result = _repair_measure_fact_units(connection)
        logger.info(
            "Measurement fact unit repair repaired=%s unresolved=%s",
            repair_result.repaired_count,
            repair_result.unresolved_count,
        )
        connection.commit()
    except Exception:
        initialization_failed = True
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()
        if initialization_failed and not database_existed:
            _remove_failed_new_database(path)

    logger.info("Local discovery database schema initialized directly; historical migrations applied=none")
    return DatabaseInitializationResult(
        db_path=path,
        current_version=current_version,
        migrations_applied=(),
    )


def _read_existing_schema_version(connection: sqlite3.Connection) -> int:
    if not _table_exists(connection, "SchemaVersion"):
        raise UnsupportedDatabaseSchemaError(
            "Existing local discovery database does not contain SchemaVersion. "
            "Pre-release or incompatible databases are not upgraded automatically."
        )
    return _get_current_schema_version(connection)


def _create_current_schema(connection: sqlite3.Connection) -> None:
    _ensure_schema_version_table(connection)
    _execute_schema_script(
        connection,
        """
        CREATE TABLE IF NOT EXISTS ReferenceDataImport (
            ReferenceDataImportKey INTEGER PRIMARY KEY AUTOINCREMENT,
            SourceFileName TEXT NOT NULL,
            SourceFileHash TEXT NOT NULL,
            ImportedUtc TEXT NOT NULL,
            EntityCount INTEGER NULL,
            ImportVersion INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS DimInfoSource (
            InfoSourceKey INTEGER PRIMARY KEY AUTOINCREMENT,
            InfoSourceUuid TEXT NOT NULL UNIQUE,
            ShortName TEXT NULL,
            FirstSeenUtc TEXT NOT NULL,
            LastSeenUtc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS DimSiteType (
            SiteTypeKey INTEGER PRIMARY KEY AUTOINCREMENT,
            SiteTypeUuid TEXT NOT NULL UNIQUE,
            ShortName TEXT NOT NULL,
            IsMobile INTEGER NULL,
            InfoSourceUuid TEXT NULL,
            InfoSourceKey INTEGER NULL REFERENCES DimInfoSource(InfoSourceKey)
        );

        CREATE TABLE IF NOT EXISTS DimSegmentType (
            SegmentTypeKey INTEGER PRIMARY KEY AUTOINCREMENT,
            SegmentTypeUuid TEXT NOT NULL UNIQUE,
            ShortName TEXT NOT NULL,
            InfoSourceUuid TEXT NULL,
            InfoSourceKey INTEGER NULL REFERENCES DimInfoSource(InfoSourceKey)
        );

        CREATE TABLE IF NOT EXISTS DimMeasurementLocationType (
            MeasurementLocationTypeKey INTEGER PRIMARY KEY AUTOINCREMENT,
            MeasurementLocationTypeUuid TEXT NOT NULL UNIQUE,
            ShortName TEXT NOT NULL,
            UomQuantityUuid TEXT NULL,
            InfoSourceUuid TEXT NULL,
            InfoSourceKey INTEGER NULL REFERENCES DimInfoSource(InfoSourceKey)
        );

        CREATE TABLE IF NOT EXISTS DimUomQuantity (
            UomQuantityKey INTEGER PRIMARY KEY AUTOINCREMENT,
            UomQuantityUuid TEXT NOT NULL UNIQUE,
            ShortName TEXT NOT NULL,
            ReferenceUnitUuid TEXT NULL,
            ReferenceUnitKey INTEGER NULL,
            InfoSourceUuid TEXT NULL,
            InfoSourceKey INTEGER NULL REFERENCES DimInfoSource(InfoSourceKey)
        );

        CREATE TABLE IF NOT EXISTS DimUnit (
            UnitKey INTEGER PRIMARY KEY AUTOINCREMENT,
            UnitUuid TEXT NOT NULL UNIQUE,
            ShortName TEXT NOT NULL,
            UomQuantityUuid TEXT NULL,
            UomQuantityKey INTEGER NULL REFERENCES DimUomQuantity(UomQuantityKey),
            ConversionScale REAL NULL,
            ConversionOffset REAL NULL,
            InfoSourceUuid TEXT NULL,
            InfoSourceKey INTEGER NULL REFERENCES DimInfoSource(InfoSourceKey)
        );

        CREATE TABLE IF NOT EXISTS DimSite (
            SiteKey INTEGER PRIMARY KEY AUTOINCREMENT,
            SiteUuid TEXT NOT NULL UNIQUE,
            SiteName TEXT NOT NULL,
            SiteTypeUuid TEXT NULL,
            SiteTypeKey INTEGER NULL REFERENCES DimSiteType(SiteTypeKey),
            InfoSourceUuid TEXT NULL,
            InfoSourceKey INTEGER NULL REFERENCES DimInfoSource(InfoSourceKey),
            FirstSeenUtc TEXT NOT NULL,
            LastSeenUtc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS DimSegment (
            SegmentKey INTEGER PRIMARY KEY AUTOINCREMENT,
            SegmentUuid TEXT NOT NULL UNIQUE,
            SegmentName TEXT NOT NULL,
            SegmentTypeUuid TEXT NULL,
            SegmentTypeKey INTEGER NULL REFERENCES DimSegmentType(SegmentTypeKey),
            SiteUuid TEXT NULL,
            SiteKey INTEGER NULL REFERENCES DimSite(SiteKey),
            InfoSourceUuid TEXT NULL,
            InfoSourceKey INTEGER NULL REFERENCES DimInfoSource(InfoSourceKey),
            FirstSeenUtc TEXT NOT NULL,
            LastSeenUtc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS DimMeasurementLocation (
            MeasurementLocationKey INTEGER PRIMARY KEY AUTOINCREMENT,
            MeasurementLocationUuid TEXT NOT NULL UNIQUE,
            MeasurementLocationName TEXT NOT NULL,
            MeasurementLocationTypeUuid TEXT NULL,
            MeasurementLocationTypeKey INTEGER NULL,
            SegmentUuid TEXT NULL,
            SegmentKey INTEGER NULL,
            ValueClass TEXT NULL,
            DefaultUnitUuid TEXT NULL,
            DefaultUnitKey INTEGER NULL REFERENCES DimUnit(UnitKey),
            UomQuantityUuid TEXT NULL,
            UomQuantityKey INTEGER NULL REFERENCES DimUomQuantity(UomQuantityKey),
            InfoSourceUuid TEXT NULL,
            InfoSourceKey INTEGER NULL REFERENCES DimInfoSource(InfoSourceKey),
            FirstSeenUtc TEXT NOT NULL,
            LastSeenUtc TEXT NOT NULL,
            FOREIGN KEY (MeasurementLocationTypeKey) REFERENCES DimMeasurementLocationType(MeasurementLocationTypeKey),
            FOREIGN KEY (SegmentKey) REFERENCES DimSegment(SegmentKey)
        );

        CREATE TABLE IF NOT EXISTS FactMeasurement (
            MeasurementFactKey INTEGER PRIMARY KEY AUTOINCREMENT,
            MeasurementUuid TEXT NULL,
            MeasurementLocationKey INTEGER NOT NULL REFERENCES DimMeasurementLocation(MeasurementLocationKey),
            MeasurementLocationUuid TEXT NOT NULL,
            UnitKey INTEGER NULL REFERENCES DimUnit(UnitKey),
            UnitUuid TEXT NULL,
            MeasurementTimestampUtc TEXT NOT NULL,
            NumericValue REAL NOT NULL,
            InfoSourceKey INTEGER NULL REFERENCES DimInfoSource(InfoSourceKey),
            InfoSourceUuid TEXT NULL,
            InsertedUtc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS DiscoveryPayload (
            SourcePayloadKey INTEGER PRIMARY KEY AUTOINCREMENT,
            EntityKind TEXT NOT NULL,
            EntityUuid TEXT NULL,
            RequestType TEXT NULL,
            PayloadJson TEXT NOT NULL,
            ReceivedUtc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS CollectorRuntimeStatus (
            CollectorId TEXT PRIMARY KEY,
            InstanceId TEXT NOT NULL,
            StartedUtc TEXT NOT NULL,
            LastHeartbeatUtc TEXT NOT NULL,
            RuntimeState TEXT NOT NULL
                CHECK (RuntimeState IN ('Running', 'Idle', 'Error')),
            LastPollUtc TEXT NULL,
            LastPublicationUtc TEXT NULL,
            LastErrorUtc TEXT NULL,
            LastError TEXT NULL
                CHECK (LastError IS NULL OR length(LastError) <= 2048)
        );
        """
    )
    create_application_setting_table(connection)


def _create_current_indexes(connection: sqlite3.Connection) -> None:
    _execute_schema_script(
        connection,
        """
        CREATE INDEX IF NOT EXISTS IX_DimInfoSource_InfoSourceUuid
            ON DimInfoSource(InfoSourceUuid);

        CREATE INDEX IF NOT EXISTS IX_DimSiteType_InfoSourceKey
            ON DimSiteType(InfoSourceKey);
        CREATE INDEX IF NOT EXISTS IX_DimSegmentType_InfoSourceKey
            ON DimSegmentType(InfoSourceKey);
        CREATE INDEX IF NOT EXISTS IX_DimMeasurementLocationType_InfoSourceKey
            ON DimMeasurementLocationType(InfoSourceKey);

        CREATE INDEX IF NOT EXISTS IX_DimUomQuantity_ReferenceUnitKey
            ON DimUomQuantity(ReferenceUnitKey);
        CREATE INDEX IF NOT EXISTS IX_DimUomQuantity_InfoSourceKey
            ON DimUomQuantity(InfoSourceKey);

        CREATE INDEX IF NOT EXISTS IX_DimUnit_UomQuantityKey
            ON DimUnit(UomQuantityKey);
        CREATE INDEX IF NOT EXISTS IX_DimUnit_InfoSourceKey
            ON DimUnit(InfoSourceKey);

        CREATE INDEX IF NOT EXISTS IX_DimSite_SiteUuid
            ON DimSite(SiteUuid);
        CREATE INDEX IF NOT EXISTS IX_DimSite_InfoSourceKey
            ON DimSite(InfoSourceKey);

        CREATE INDEX IF NOT EXISTS IX_DimSegment_SegmentUuid
            ON DimSegment(SegmentUuid);
        CREATE INDEX IF NOT EXISTS IX_DimSegment_SiteUuid
            ON DimSegment(SiteUuid);
        CREATE INDEX IF NOT EXISTS IX_DimSegment_InfoSourceKey
            ON DimSegment(InfoSourceKey);

        CREATE INDEX IF NOT EXISTS IX_DimMeasurementLocation_MeasurementLocationUuid
            ON DimMeasurementLocation(MeasurementLocationUuid);
        CREATE INDEX IF NOT EXISTS IX_DimMeasurementLocation_SegmentUuid
            ON DimMeasurementLocation(SegmentUuid);
        CREATE INDEX IF NOT EXISTS IX_DimMeasurementLocation_InfoSourceKey
            ON DimMeasurementLocation(InfoSourceKey);
        CREATE INDEX IF NOT EXISTS IX_DimMeasurementLocation_DefaultUnitKey
            ON DimMeasurementLocation(DefaultUnitKey);
        CREATE INDEX IF NOT EXISTS IX_DimMeasurementLocation_UomQuantityKey
            ON DimMeasurementLocation(UomQuantityKey);

        CREATE INDEX IF NOT EXISTS IX_FactMeasurement_MeasurementTimestampUtc
            ON FactMeasurement(MeasurementTimestampUtc);
        CREATE INDEX IF NOT EXISTS IX_FactMeasurement_LocationTimestamp
            ON FactMeasurement(MeasurementLocationUuid, MeasurementTimestampUtc);
        CREATE UNIQUE INDEX IF NOT EXISTS UX_FactMeasurement_LocationTimestamp
            ON FactMeasurement(MeasurementLocationUuid, MeasurementTimestampUtc)
            WHERE MeasurementUuid IS NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS UX_FactMeasurement_LocationTimestampMeasurementUuid
            ON FactMeasurement(MeasurementLocationUuid, MeasurementTimestampUtc, MeasurementUuid)
            WHERE MeasurementUuid IS NOT NULL;
        CREATE INDEX IF NOT EXISTS IX_FactMeasurement_InfoSourceKey
            ON FactMeasurement(InfoSourceKey);

        CREATE INDEX IF NOT EXISTS IX_DiscoveryPayload_EntityKindEntityUuid
            ON DiscoveryPayload(EntityKind, EntityUuid);
        """
    )


def _create_reporting_views(connection: sqlite3.Connection) -> None:
    _execute_schema_script(
        connection,
        """
        CREATE VIEW IF NOT EXISTS vw_powerbi_measurement_catalog AS
        SELECT
            site.SiteUuid,
            site.SiteName,
            site.SiteTypeUuid,
            site.InfoSourceUuid AS SiteInfoSourceUuid,
            site_type.ShortName AS SiteTypeName,
            site_type.InfoSourceUuid AS SiteTypeInfoSourceUuid,
            segment.SegmentUuid,
            segment.SegmentName,
            segment.SegmentTypeUuid,
            segment.InfoSourceUuid AS SegmentInfoSourceUuid,
            segment_type.ShortName AS SegmentTypeName,
            segment_type.InfoSourceUuid AS SegmentTypeInfoSourceUuid,
            location.MeasurementLocationUuid,
            location.MeasurementLocationName,
            location.MeasurementLocationTypeUuid,
            location.ValueClass,
            location.InfoSourceUuid AS MeasurementLocationInfoSourceUuid,
            location_type.ShortName AS MeasurementLocationTypeName,
            location_type.InfoSourceUuid AS MeasurementLocationTypeInfoSourceUuid,
            location.DefaultUnitKey,
            location.DefaultUnitUuid,
            default_unit.ShortName AS DefaultUnitName,
            default_unit.ConversionScale AS DefaultUnitConversionScale,
            default_unit.ConversionOffset AS DefaultUnitConversionOffset,
            default_unit.InfoSourceUuid AS DefaultUnitInfoSourceUuid,
            location.UomQuantityKey,
            location.UomQuantityUuid,
            quantity.ShortName AS UomQuantityName,
            quantity.ReferenceUnitKey,
            quantity.ReferenceUnitUuid,
            reference_unit.ShortName AS ReferenceUnitName,
            location.FirstSeenUtc,
            location.LastSeenUtc
        FROM DimMeasurementLocation location
        LEFT JOIN DimSegment segment
            ON segment.SegmentKey = location.SegmentKey
        LEFT JOIN DimSite site
            ON site.SiteKey = segment.SiteKey
        LEFT JOIN DimSiteType site_type
            ON site_type.SiteTypeKey = site.SiteTypeKey
        LEFT JOIN DimSegmentType segment_type
            ON segment_type.SegmentTypeKey = segment.SegmentTypeKey
        LEFT JOIN DimMeasurementLocationType location_type
            ON location_type.MeasurementLocationTypeKey = location.MeasurementLocationTypeKey
        LEFT JOIN DimUnit default_unit
            ON default_unit.UnitKey = location.DefaultUnitKey
        LEFT JOIN DimUomQuantity quantity
            ON quantity.UomQuantityKey = location.UomQuantityKey
        LEFT JOIN DimUnit reference_unit
            ON reference_unit.UnitKey = quantity.ReferenceUnitKey;

        CREATE VIEW IF NOT EXISTS vw_powerbi_measurement_timeseries AS
        SELECT
            fact.MeasurementFactKey,
            fact.MeasurementUuid,
            fact.MeasurementTimestampUtc,
            fact.MeasurementLocationUuid,
            site.SiteName,
            site.InfoSourceUuid AS SiteInfoSourceUuid,
            segment.SegmentName,
            segment.InfoSourceUuid AS SegmentInfoSourceUuid,
            location.MeasurementLocationName,
            location.ValueClass,
            location.InfoSourceUuid AS MeasurementLocationInfoSourceUuid,
            location_type.ShortName AS MeasurementLocationTypeName,
            location_type.InfoSourceUuid AS MeasurementLocationTypeInfoSourceUuid,
            fact.UnitKey AS StoredUnitKey,
            fact.UnitUuid AS StoredUnitUuid,
            stored_unit.ShortName AS StoredUnitName,
            stored_unit.ConversionScale AS StoredUnitConversionScale,
            stored_unit.ConversionOffset AS StoredUnitConversionOffset,
            location.DefaultUnitKey,
            location.DefaultUnitUuid,
            default_unit.ShortName AS DefaultUnitName,
            default_unit.ConversionScale AS DefaultUnitConversionScale,
            default_unit.ConversionOffset AS DefaultUnitConversionOffset,
            location.UomQuantityKey,
            location.UomQuantityUuid,
            quantity.ShortName AS UomQuantityName,
            quantity.ReferenceUnitKey,
            quantity.ReferenceUnitUuid,
            reference_unit.ShortName AS ReferenceUnitName,
            fact.NumericValue,
            fact.InfoSourceUuid AS MeasurementInfoSourceUuid
        FROM FactMeasurement fact
        LEFT JOIN DimMeasurementLocation location
            ON location.MeasurementLocationKey = fact.MeasurementLocationKey
        LEFT JOIN DimSegment segment
            ON segment.SegmentKey = location.SegmentKey
        LEFT JOIN DimSite site
            ON site.SiteKey = segment.SiteKey
        LEFT JOIN DimMeasurementLocationType location_type
            ON location_type.MeasurementLocationTypeKey = location.MeasurementLocationTypeKey
        LEFT JOIN DimUnit stored_unit
            ON stored_unit.UnitKey = fact.UnitKey
        LEFT JOIN DimUnit default_unit
            ON default_unit.UnitKey = location.DefaultUnitKey
        LEFT JOIN DimUomQuantity quantity
            ON quantity.UomQuantityKey = location.UomQuantityKey
        LEFT JOIN DimUnit reference_unit
            ON reference_unit.UnitKey = quantity.ReferenceUnitKey;

        CREATE VIEW IF NOT EXISTS vw_grafana_measurements AS
        SELECT
            fact.MeasurementTimestampUtc AS time,
            fact.MeasurementFactKey AS measurement_fact_key,
            fact.MeasurementUuid AS measurement_uuid,
            fact.MeasurementLocationUuid AS measurement_location_uuid,
            site.SiteName AS site_name,
            segment.SegmentName AS segment_name,
            location.MeasurementLocationName AS measurement_location_name,
            location_type.ShortName AS measurement_location_type,
            location.ValueClass AS value_class,
            fact.UnitKey AS stored_unit_key,
            fact.UnitUuid AS stored_unit_uuid,
            stored_unit.ShortName AS stored_unit_name,
            stored_unit.ConversionScale AS stored_unit_conversion_scale,
            stored_unit.ConversionOffset AS stored_unit_conversion_offset,
            location.DefaultUnitKey AS default_unit_key,
            location.DefaultUnitUuid AS default_unit_uuid,
            default_unit.ShortName AS default_unit_name,
            default_unit.ConversionScale AS default_unit_conversion_scale,
            default_unit.ConversionOffset AS default_unit_conversion_offset,
            location.UomQuantityKey AS uom_quantity_key,
            location.UomQuantityUuid AS uom_quantity_uuid,
            quantity.ShortName AS uom_quantity_name,
            quantity.ReferenceUnitKey AS reference_unit_key,
            quantity.ReferenceUnitUuid AS reference_unit_uuid,
            reference_unit.ShortName AS reference_unit_name,
            fact.NumericValue AS value,
            fact.InfoSourceUuid AS info_source_uuid
        FROM FactMeasurement fact
        LEFT JOIN DimMeasurementLocation location
            ON location.MeasurementLocationKey = fact.MeasurementLocationKey
        LEFT JOIN DimSegment segment
            ON segment.SegmentKey = location.SegmentKey
        LEFT JOIN DimSite site
            ON site.SiteKey = segment.SiteKey
        LEFT JOIN DimMeasurementLocationType location_type
            ON location_type.MeasurementLocationTypeKey = location.MeasurementLocationTypeKey
        LEFT JOIN DimUnit stored_unit
            ON stored_unit.UnitKey = fact.UnitKey
        LEFT JOIN DimUnit default_unit
            ON default_unit.UnitKey = location.DefaultUnitKey
        LEFT JOIN DimUomQuantity quantity
            ON quantity.UomQuantityKey = location.UomQuantityKey
        LEFT JOIN DimUnit reference_unit
            ON reference_unit.UnitKey = quantity.ReferenceUnitKey;
        """
    )


def _record_current_schema_version(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO SchemaVersion(version, description)
        VALUES (?, 'Current first-release local discovery schema')
        """,
        (CURRENT_SCHEMA_VERSION,),
    )


def _ensure_schema_version_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS SchemaVersion (
            version INTEGER PRIMARY KEY,
            appliedUtc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            description TEXT NOT NULL
        )
        """
    )


def _get_current_schema_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT COALESCE(MAX(version), 0) FROM SchemaVersion").fetchone()
    return int(row[0] or 0)


def _execute_schema_script(connection: sqlite3.Connection, script: str) -> None:
    statement_lines: list[str] = []
    for line in script.splitlines():
        statement_lines.append(line)
        statement = "\n".join(statement_lines).strip()
        if statement and sqlite3.complete_statement(statement):
            connection.execute(statement)
            statement_lines.clear()

    trailing_statement = "\n".join(statement_lines).strip()
    if trailing_statement:
        raise RuntimeError(f"Incomplete SQLite schema statement: {trailing_statement}")


def _remove_failed_new_database(path: Path) -> None:
    for candidate in (
        path,
        path.with_name(path.name + "-journal"),
        path.with_name(path.name + "-wal"),
        path.with_name(path.name + "-shm"),
    ):
        try:
            candidate.unlink(missing_ok=True)
        except OSError:
            logger.warning("Failed to remove incomplete new database file path=%s", candidate, exc_info=True)


def repair_measure_fact_units(db_path: str | Path = DEFAULT_DATABASE_PATH) -> FactMeasurementUnitRepairResult:
    """Backfill missing stored units for repairable Measure facts."""
    path = Path(db_path)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        result = _repair_measure_fact_units(connection)
        connection.commit()
    return result


def _repair_measure_fact_units(connection: sqlite3.Connection) -> FactMeasurementUnitRepairResult:
    if not _table_exists(connection, "FactMeasurement") or not _table_exists(connection, "DimMeasurementLocation"):
        return FactMeasurementUnitRepairResult(repaired_count=0, unresolved_count=0)
    fact_columns = _table_columns(connection, "FactMeasurement")
    location_columns = _table_columns(connection, "DimMeasurementLocation")
    required_fact_columns = {"MeasurementLocationKey", "UnitKey", "UnitUuid"}
    required_location_columns = {"MeasurementLocationKey", "ValueClass", "DefaultUnitKey", "DefaultUnitUuid"}
    if not required_fact_columns.issubset(fact_columns) or not required_location_columns.issubset(location_columns):
        return FactMeasurementUnitRepairResult(repaired_count=0, unresolved_count=0)

    repairable_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM FactMeasurement fact
        JOIN DimMeasurementLocation location
          ON location.MeasurementLocationKey = fact.MeasurementLocationKey
        WHERE location.ValueClass = 'Measure'
          AND (fact.UnitKey IS NULL OR fact.UnitUuid IS NULL)
          AND location.DefaultUnitKey IS NOT NULL
          AND location.DefaultUnitUuid IS NOT NULL
        """
    ).fetchone()[0]
    connection.execute(
        """
        UPDATE FactMeasurement
        SET
            UnitKey = COALESCE(UnitKey, (
                SELECT location.DefaultUnitKey
                FROM DimMeasurementLocation location
                WHERE location.MeasurementLocationKey = FactMeasurement.MeasurementLocationKey
            )),
            UnitUuid = COALESCE(UnitUuid, (
                SELECT location.DefaultUnitUuid
                FROM DimMeasurementLocation location
                WHERE location.MeasurementLocationKey = FactMeasurement.MeasurementLocationKey
            ))
        WHERE (UnitKey IS NULL OR UnitUuid IS NULL)
          AND EXISTS (
              SELECT 1
              FROM DimMeasurementLocation location
              WHERE location.MeasurementLocationKey = FactMeasurement.MeasurementLocationKey
                AND location.ValueClass = 'Measure'
                AND location.DefaultUnitKey IS NOT NULL
                AND location.DefaultUnitUuid IS NOT NULL
          )
        """
    )
    unresolved_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM FactMeasurement fact
        JOIN DimMeasurementLocation location
          ON location.MeasurementLocationKey = fact.MeasurementLocationKey
        WHERE location.ValueClass = 'Measure'
          AND (fact.UnitKey IS NULL OR fact.UnitUuid IS NULL)
        """
    ).fetchone()[0]
    return FactMeasurementUnitRepairResult(
        repaired_count=int(repairable_count or 0),
        unresolved_count=int(unresolved_count or 0),
    )


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
