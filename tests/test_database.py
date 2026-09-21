import sqlite3

import pytest

import app.storage.database as database_storage
from app.storage.database import (
    CURRENT_SCHEMA_VERSION,
    UnsupportedDatabaseSchemaError,
    initialize_database,
    repair_measure_fact_units,
)


REQUIRED_TABLES = {
    "SchemaVersion",
    "ReferenceDataImport",
    "DimSiteType",
    "DimSegmentType",
    "DimMeasurementLocationType",
    "DimUomQuantity",
    "DimUnit",
    "DimInfoSource",
    "DimSite",
    "DimSegment",
    "DimMeasurementLocation",
    "FactMeasurement",
    "DiscoveryPayload",
    "ApplicationSetting",
    "CollectorRuntimeStatus",
}

REQUIRED_INDEXES = {
    "IX_DimSite_SiteUuid",
    "IX_DimSegment_SegmentUuid",
    "IX_DimSegment_SiteUuid",
    "IX_DimMeasurementLocation_MeasurementLocationUuid",
    "IX_DimMeasurementLocation_SegmentUuid",
    "IX_FactMeasurement_MeasurementTimestampUtc",
    "IX_FactMeasurement_LocationTimestamp",
    "UX_FactMeasurement_LocationTimestamp",
    "UX_FactMeasurement_LocationTimestampMeasurementUuid",
    "IX_DiscoveryPayload_EntityKindEntityUuid",
    "IX_DimInfoSource_InfoSourceUuid",
    "IX_DimMeasurementLocation_InfoSourceKey",
    "IX_DimMeasurementLocation_DefaultUnitKey",
    "IX_DimMeasurementLocation_UomQuantityKey",
    "IX_DimUnit_UomQuantityKey",
    "IX_DimUnit_InfoSourceKey",
    "IX_DimUomQuantity_ReferenceUnitKey",
    "IX_DimUomQuantity_InfoSourceKey",
    "IX_FactMeasurement_InfoSourceKey",
    "IX_DimMeasurementLocationType_InfoSourceKey",
    "IX_DimSegment_InfoSourceKey",
    "IX_DimSegmentType_InfoSourceKey",
    "IX_DimSite_InfoSourceKey",
    "IX_DimSiteType_InfoSourceKey",
}

REQUIRED_VIEWS = {
    "vw_powerbi_measurement_catalog",
    "vw_powerbi_measurement_timeseries",
    "vw_grafana_measurements",
}

APPLICATION_SETTING_DEFAULTS = {
    "Collector.Enabled": ("true", "Boolean"),
    "Collector.PollingIntervalSeconds": ("15", "Integer"),
    "DataRetention.Enabled": ("false", "Boolean"),
    "DataRetention.Days": ("90", "Integer"),
    "EnergyCost.CurrencyUomUuid": (None, "Uuid"),
    "EnergyCost.RatePerKwh": (None, "Decimal"),
}


def test_initialize_database_creates_current_release_schema_directly(tmp_path) -> None:
    db_path = tmp_path / "data" / "discovery_portal.db"

    result = initialize_database(db_path)

    assert result.db_path == db_path
    assert result.current_version == CURRENT_SCHEMA_VERSION
    assert result.migrations_applied == ()
    assert db_path.exists()

    with sqlite3.connect(db_path) as connection:
        schema_versions = connection.execute(
            "SELECT version, description FROM SchemaVersion ORDER BY version"
        ).fetchall()
        tables = _sqlite_object_names(connection, "table")
        indexes = _sqlite_object_names(connection, "index")
        views = _sqlite_object_names(connection, "view")

    assert schema_versions == [(CURRENT_SCHEMA_VERSION, "Current first-release local discovery schema")]
    assert REQUIRED_TABLES.issubset(tables)
    assert REQUIRED_INDEXES.issubset(indexes)
    assert REQUIRED_VIEWS.issubset(views)


def test_failed_fresh_initialization_removes_new_database_file(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "data" / "discovery_portal.db"

    def fail_after_schema_created(connection: sqlite3.Connection) -> None:
        raise RuntimeError("injected fresh initialization failure")

    monkeypatch.setattr(database_storage, "_create_current_indexes", fail_after_schema_created)

    with pytest.raises(RuntimeError, match="injected fresh initialization failure"):
        initialize_database(db_path)

    assert not db_path.exists()


def test_failed_fresh_initialization_can_be_retried_successfully(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "data" / "discovery_portal.db"
    create_current_indexes = database_storage._create_current_indexes

    def fail_once(connection: sqlite3.Connection) -> None:
        monkeypatch.setattr(database_storage, "_create_current_indexes", create_current_indexes)
        raise RuntimeError("injected fresh initialization failure")

    monkeypatch.setattr(database_storage, "_create_current_indexes", fail_once)

    with pytest.raises(RuntimeError, match="injected fresh initialization failure"):
        initialize_database(db_path)

    result = initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        schema_versions = connection.execute("SELECT version FROM SchemaVersion").fetchall()
        tables = _sqlite_object_names(connection, "table")

    assert result.current_version == CURRENT_SCHEMA_VERSION
    assert schema_versions == [(CURRENT_SCHEMA_VERSION,)]
    assert REQUIRED_TABLES.issubset(tables)


def test_existing_database_is_not_deleted_when_initialization_fails(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    def fail_existing_startup(connection: sqlite3.Connection) -> None:
        raise RuntimeError("injected existing initialization failure")

    monkeypatch.setattr(database_storage, "_create_current_indexes", fail_existing_startup)

    with pytest.raises(RuntimeError, match="injected existing initialization failure"):
        initialize_database(db_path)

    assert db_path.exists()
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT MAX(version) FROM SchemaVersion").fetchone()[0] == CURRENT_SCHEMA_VERSION


def test_current_schema_preserves_expected_dimension_and_fact_columns(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        assert _table_columns(connection, "DimUnit") == [
            "UnitKey",
            "UnitUuid",
            "ShortName",
            "UomQuantityUuid",
            "UomQuantityKey",
            "ConversionScale",
            "ConversionOffset",
            "InfoSourceUuid",
            "InfoSourceKey",
        ]
        assert _table_columns(connection, "DimUomQuantity") == [
            "UomQuantityKey",
            "UomQuantityUuid",
            "ShortName",
            "ReferenceUnitUuid",
            "ReferenceUnitKey",
            "InfoSourceUuid",
            "InfoSourceKey",
        ]
        assert _table_columns(connection, "DimMeasurementLocation") == [
            "MeasurementLocationKey",
            "MeasurementLocationUuid",
            "MeasurementLocationName",
            "MeasurementLocationTypeUuid",
            "MeasurementLocationTypeKey",
            "SegmentUuid",
            "SegmentKey",
            "ValueClass",
            "DefaultUnitUuid",
            "DefaultUnitKey",
            "UomQuantityUuid",
            "UomQuantityKey",
            "InfoSourceUuid",
            "InfoSourceKey",
            "FirstSeenUtc",
            "LastSeenUtc",
        ]
        assert _table_columns(connection, "FactMeasurement") == [
            "MeasurementFactKey",
            "MeasurementUuid",
            "MeasurementLocationKey",
            "MeasurementLocationUuid",
            "UnitKey",
            "UnitUuid",
            "MeasurementTimestampUtc",
            "NumericValue",
            "InfoSourceKey",
            "InfoSourceUuid",
            "InsertedUtc",
        ]


def test_application_setting_defaults_are_seeded_and_preserve_custom_values(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE ApplicationSetting SET SettingValue = 'false' WHERE SettingKey = 'Collector.Enabled'"
        )
        connection.execute("DELETE FROM ApplicationSetting WHERE SettingKey = 'DataRetention.Days'")
        connection.commit()

    result = initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        settings = {
            row[0]: (row[1], row[2])
            for row in connection.execute(
                """
                SELECT SettingKey, SettingValue, ValueType
                FROM ApplicationSetting
                ORDER BY SettingKey
                """
            )
        }

    assert result.current_version == CURRENT_SCHEMA_VERSION
    assert settings["Collector.Enabled"] == ("false", "Boolean")
    assert settings["DataRetention.Days"] == ("90", "Integer")
    assert set(settings) == set(APPLICATION_SETTING_DEFAULTS)


def test_initialize_database_is_idempotent_and_preserves_data(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO DimSiteType(SiteTypeUuid, ShortName, IsMobile)
            VALUES ('site-type-1', 'Office Building', 0)
            """
        )
        connection.commit()

    result = initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        site_type_count = connection.execute(
            "SELECT COUNT(*) FROM DimSiteType WHERE SiteTypeUuid = 'site-type-1'"
        ).fetchone()[0]
        version_count = connection.execute("SELECT COUNT(*) FROM SchemaVersion").fetchone()[0]

    assert result.current_version == CURRENT_SCHEMA_VERSION
    assert result.migrations_applied == ()
    assert site_type_count == 1
    assert version_count == 1


def test_collector_runtime_status_table_and_constraints(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        columns = {row[1]: row[2] for row in connection.execute("PRAGMA table_info(CollectorRuntimeStatus)")}

        for runtime_state in ("Running", "Idle", "Error"):
            connection.execute(
                """
                INSERT INTO CollectorRuntimeStatus (
                    CollectorId,
                    InstanceId,
                    StartedUtc,
                    LastHeartbeatUtc,
                    RuntimeState
                )
                VALUES (?, 'instance-1', '2026-08-20T12:00:00Z', '2026-08-20T12:00:01Z', ?)
                """,
                (f"collector-{runtime_state}", runtime_state),
            )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO CollectorRuntimeStatus (
                    CollectorId,
                    InstanceId,
                    StartedUtc,
                    LastHeartbeatUtc,
                    RuntimeState
                )
                VALUES ('collector-bad-state', 'instance-1', '2026-08-20T12:00:00Z', '2026-08-20T12:00:01Z', 'Offline')
                """
            )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO CollectorRuntimeStatus (
                    CollectorId,
                    InstanceId,
                    StartedUtc,
                    LastHeartbeatUtc,
                    RuntimeState,
                    LastError
                )
                VALUES ('collector-long-error', 'instance-1', '2026-08-20T12:00:00Z', '2026-08-20T12:00:01Z', 'Error', ?)
                """,
                ("x" * 2049,),
            )

    assert columns == {
        "CollectorId": "TEXT",
        "InstanceId": "TEXT",
        "StartedUtc": "TEXT",
        "LastHeartbeatUtc": "TEXT",
        "RuntimeState": "TEXT",
        "LastPollUtc": "TEXT",
        "LastPublicationUtc": "TEXT",
        "LastErrorUtc": "TEXT",
        "LastError": "TEXT",
    }


def test_measurement_fact_unique_indexes_support_release_identity(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        location_key = _insert_number_location(connection)
        connection.execute(
            """
            INSERT INTO FactMeasurement(
                MeasurementLocationKey,
                MeasurementLocationUuid,
                MeasurementTimestampUtc,
                NumericValue,
                InsertedUtc
            )
            VALUES (?, 'location-1', '2026-01-01T00:00:00Z', 1.0, '2026-01-01T00:00:01Z')
            """,
            (location_key,),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO FactMeasurement(
                    MeasurementLocationKey,
                    MeasurementLocationUuid,
                    MeasurementTimestampUtc,
                    NumericValue,
                    InsertedUtc
                )
                VALUES (?, 'location-1', '2026-01-01T00:00:00Z', 2.0, '2026-01-01T00:00:02Z')
                """,
                (location_key,),
            )

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
            VALUES ('measurement-1', ?, 'location-1', '2026-01-01T00:00:00Z', 3.0, '2026-01-01T00:00:03Z')
            """,
            (location_key,),
        )
        with pytest.raises(sqlite3.IntegrityError):
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
                VALUES ('measurement-1', ?, 'location-1', '2026-01-01T00:00:00Z', 4.0, '2026-01-01T00:00:04Z')
                """,
                (location_key,),
            )


def test_repair_measure_fact_units_backfills_only_repairable_measure_rows(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        quantity_key = connection.execute(
            """
            INSERT INTO DimUomQuantity(UomQuantityUuid, ShortName)
            VALUES ('quantity-1', 'Quantity 1')
            """
        ).lastrowid
        default_unit_key = connection.execute(
            """
            INSERT INTO DimUnit(UnitUuid, ShortName, UomQuantityUuid, UomQuantityKey)
            VALUES ('unit-default', 'Default Unit', 'quantity-1', ?)
            """,
            (quantity_key,),
        ).lastrowid
        explicit_unit_key = connection.execute(
            """
            INSERT INTO DimUnit(UnitUuid, ShortName, UomQuantityUuid, UomQuantityKey)
            VALUES ('unit-explicit', 'Explicit Unit', 'quantity-1', ?)
            """,
            (quantity_key,),
        ).lastrowid
        repairable_location_key = connection.execute(
            """
            INSERT INTO DimMeasurementLocation(
                MeasurementLocationUuid,
                MeasurementLocationName,
                ValueClass,
                DefaultUnitUuid,
                DefaultUnitKey,
                UomQuantityUuid,
                UomQuantityKey,
                FirstSeenUtc,
                LastSeenUtc
            )
            VALUES ('measure-repairable', 'Repairable Measure', 'Measure', 'unit-default', ?, 'quantity-1', ?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
            """,
            (default_unit_key, quantity_key),
        ).lastrowid
        unresolved_location_key = connection.execute(
            """
            INSERT INTO DimMeasurementLocation(
                MeasurementLocationUuid,
                MeasurementLocationName,
                ValueClass,
                FirstSeenUtc,
                LastSeenUtc
            )
            VALUES ('measure-unresolved', 'Unresolved Measure', 'Measure', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
            """
        ).lastrowid
        percentage_location_key = connection.execute(
            """
            INSERT INTO DimMeasurementLocation(
                MeasurementLocationUuid,
                MeasurementLocationName,
                ValueClass,
                FirstSeenUtc,
                LastSeenUtc
            )
            VALUES ('percentage-1', 'Percentage', 'Percentage', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
            """
        ).lastrowid
        connection.executemany(
            """
            INSERT INTO FactMeasurement(
                MeasurementLocationKey,
                MeasurementLocationUuid,
                UnitKey,
                UnitUuid,
                MeasurementTimestampUtc,
                NumericValue,
                InsertedUtc
            )
            VALUES (?, ?, ?, ?, ?, ?, '2026-01-01T00:00:01Z')
            """,
            [
                (repairable_location_key, "measure-repairable", None, None, "2026-01-01T00:00:00Z", 1.0),
                (
                    repairable_location_key,
                    "measure-repairable",
                    explicit_unit_key,
                    "unit-explicit",
                    "2026-01-01T00:01:00Z",
                    2.0,
                ),
                (unresolved_location_key, "measure-unresolved", None, None, "2026-01-01T00:00:00Z", 3.0),
                (percentage_location_key, "percentage-1", None, None, "2026-01-01T00:00:00Z", 4.0),
            ],
        )
        connection.commit()

    first_result = repair_measure_fact_units(db_path)
    second_result = repair_measure_fact_units(db_path)

    with sqlite3.connect(db_path) as connection:
        rows = {
            (row[0], row[1]): row[2:]
            for row in connection.execute(
                """
                SELECT MeasurementLocationUuid, MeasurementTimestampUtc, UnitKey, UnitUuid
                FROM FactMeasurement
                ORDER BY MeasurementLocationUuid, MeasurementTimestampUtc
                """
            )
        }

    assert first_result.repaired_count == 1
    assert first_result.unresolved_count == 1
    assert second_result.repaired_count == 0
    assert second_result.unresolved_count == 1
    assert rows[("measure-repairable", "2026-01-01T00:00:00Z")] == (default_unit_key, "unit-default")
    assert rows[("measure-repairable", "2026-01-01T00:01:00Z")] == (explicit_unit_key, "unit-explicit")
    assert rows[("measure-unresolved", "2026-01-01T00:00:00Z")] == (None, None)
    assert rows[("percentage-1", "2026-01-01T00:00:00Z")] == (None, None)


def test_existing_older_database_fails_without_modifying_schema(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE SchemaVersion (
                version INTEGER PRIMARY KEY,
                appliedUtc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                description TEXT NOT NULL
            )
            """
        )
        connection.execute("INSERT INTO SchemaVersion(version, description) VALUES (16, 'pre-release')")
        connection.execute("CREATE TABLE LegacyData(id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO LegacyData(value) VALUES ('keep me')")
        connection.commit()

    with pytest.raises(UnsupportedDatabaseSchemaError, match="older than supported"):
        initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        assert _sqlite_object_names(connection, "table") == {"LegacyData", "SchemaVersion"}
        assert connection.execute("SELECT value FROM LegacyData").fetchone()[0] == "keep me"
        assert connection.execute("SELECT MAX(version) FROM SchemaVersion").fetchone()[0] == 16


def test_existing_database_without_schema_version_fails_without_modifying_schema(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE ExistingData(id INTEGER PRIMARY KEY)")
        connection.commit()

    with pytest.raises(UnsupportedDatabaseSchemaError, match="does not contain SchemaVersion"):
        initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        assert _sqlite_object_names(connection, "table") == {"ExistingData"}


def test_existing_newer_database_fails_without_modifying_schema(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE SchemaVersion (
                version INTEGER PRIMARY KEY,
                appliedUtc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                description TEXT NOT NULL
            )
            """
        )
        connection.execute("INSERT INTO SchemaVersion(version, description) VALUES (18, 'future')")
        connection.commit()

    with pytest.raises(UnsupportedDatabaseSchemaError, match="newer than supported"):
        initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        assert _sqlite_object_names(connection, "table") == {"SchemaVersion"}
        assert connection.execute("SELECT MAX(version) FROM SchemaVersion").fetchone()[0] == 18


def test_database_views_are_queryable(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        for view_name in REQUIRED_VIEWS:
            assert connection.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()[0] == 0


def test_grafana_measurements_view_returns_timeseries_shape(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO DimSiteType(SiteTypeUuid, ShortName)
            VALUES ('site-type-office', 'Office Building')
            """
        )
        site_type_key = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            """
            INSERT INTO DimSegmentType(SegmentTypeUuid, ShortName)
            VALUES ('segment-type-compressor', 'Compressor')
            """
        )
        segment_type_key = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            """
            INSERT INTO DimMeasurementLocationType(MeasurementLocationTypeUuid, ShortName)
            VALUES ('location-type-current', 'Average Current')
            """
        )
        location_type_key = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            """
            INSERT INTO DimUnit(UnitUuid, ShortName)
            VALUES ('unit-amps', 'Amperes')
            """
        )
        unit_key = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            """
            INSERT INTO DimSite(
                SiteUuid,
                SiteName,
                SiteTypeUuid,
                SiteTypeKey,
                FirstSeenUtc,
                LastSeenUtc
            )
            VALUES (
                'site-1',
                'Installation Site',
                'site-type-office',
                ?,
                '2026-01-01T00:00:00Z',
                '2026-01-01T00:00:00Z'
            )
            """,
            (site_type_key,),
        )
        site_key = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            """
            INSERT INTO DimSegment(
                SegmentUuid,
                SegmentName,
                SegmentTypeUuid,
                SegmentTypeKey,
                SiteUuid,
                SiteKey,
                FirstSeenUtc,
                LastSeenUtc
            )
            VALUES (
                'segment-1',
                'Compressor',
                'segment-type-compressor',
                ?,
                'site-1',
                ?,
                '2026-01-01T00:00:00Z',
                '2026-01-01T00:00:00Z'
            )
            """,
            (segment_type_key, site_key),
        )
        segment_key = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            """
            INSERT INTO DimMeasurementLocation(
                MeasurementLocationUuid,
                MeasurementLocationName,
                MeasurementLocationTypeUuid,
                MeasurementLocationTypeKey,
                SegmentUuid,
                SegmentKey,
                ValueClass,
                DefaultUnitUuid,
                DefaultUnitKey,
                FirstSeenUtc,
                LastSeenUtc
            )
            VALUES (
                'location-1',
                'Average Current, Stator',
                'location-type-current',
                ?,
                'segment-1',
                ?,
                'Measure',
                'unit-amps',
                ?,
                '2026-01-01T00:00:00Z',
                '2026-01-01T00:00:00Z'
            )
            """,
            (location_type_key, segment_key, unit_key),
        )
        location_key = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            """
            INSERT INTO FactMeasurement(
                MeasurementLocationKey,
                MeasurementLocationUuid,
                UnitKey,
                UnitUuid,
                MeasurementTimestampUtc,
                NumericValue,
                InsertedUtc
            )
            VALUES (
                ?,
                'location-1',
                ?,
                'unit-amps',
                '2026-01-01T00:00:00Z',
                42.5,
                '2026-01-01T00:00:01Z'
            )
            """,
            (location_key, unit_key),
        )
        connection.commit()

        row = connection.execute(
            """
            SELECT
                time,
                site_name,
                segment_name,
                measurement_location_name,
                measurement_location_type,
                stored_unit_name,
                value
            FROM vw_grafana_measurements
            """
        ).fetchone()

    assert row == (
        "2026-01-01T00:00:00Z",
        "Installation Site",
        "Compressor",
        "Average Current, Stator",
        "Average Current",
        "Amperes",
        42.5,
    )


def _insert_number_location(connection: sqlite3.Connection) -> int:
    return connection.execute(
        """
        INSERT INTO DimMeasurementLocation(
            MeasurementLocationUuid,
            MeasurementLocationName,
            ValueClass,
            FirstSeenUtc,
            LastSeenUtc
        )
        VALUES ('location-1', 'Location 1', 'Number', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
        """
    ).lastrowid


def _sqlite_object_names(connection: sqlite3.Connection, object_type: str) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = ?
              AND name NOT LIKE 'sqlite_%'
            """,
            (object_type,),
        )
    }


def _table_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")]
