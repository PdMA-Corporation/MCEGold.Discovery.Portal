import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.main import app, settings
from app.services.reference_data_service import ReferenceDataService
from app.storage.database import initialize_database
from app.storage.reference_data_repository import (
    get_measurement_location_type_entries,
    get_segment_type_entries,
)
from app.storage.reference_data_seed import (
    ReferenceDataInitializationError,
    ReferenceDataSeeder,
    seed_reference_data,
)


REFERENCE_XML = Path("docs/CCOM Reference Data.xml")
EXPECTED_REFERENCE_COUNTS = {
    "DimSiteType": 6,
    "DimSegmentType": 1063,
    "DimMeasurementLocationType": 258,
    "DimUnit": 306,
    "DimUomQuantity": 90,
}
WATTS_UNIT_UUID = "47d65798-ab41-40a7-8ad7-bd8dc437f5e1"
KILOWATTS_UNIT_UUID = "83278856-e2f4-4f48-bcce-59f2ad41620e"
POWER_UOM_QUANTITY_UUID = "6cb7fb47-3a8d-466a-b1a2-33a68cdaa433"
DOCUMENT_INFO_SOURCE_UUIDS = {
    "06f32010-a99a-430d-bf98-57ac65450a9c",
    "763e053d-c741-476a-bba9-0be8be006046",
}
MIMOSA_INFO_SOURCE_UUID = "cf3f3a8a-1e42-4f15-9288-9cf2241e163d"


def loaded_reference_data(path: Path = REFERENCE_XML) -> ReferenceDataService:
    reference_data = ReferenceDataService(str(path), "CCOM Reference Data")
    reference_data.load()
    return reference_data


def write_minimal_reference_xml(
    path: Path,
    *,
    site_name: str = "Site Type One",
    segment_name: str = "Segment Type One",
    location_name: str = "Location Type One",
    unit_name: str = "Unit One",
    quantity_name: str = "Quantity One",
    include_unresolved_info_source: bool = False,
) -> None:
    info_source = "<InfoSource><UUID>document-source</UUID></InfoSource>" if include_unresolved_info_source else ""
    path.write_text(
        f"""<?xml version="1.0" encoding="utf-8"?>
<CCOMData xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.mimosa.org/ccom4">
    <Entity xsi:type="SiteType"><UUID>site-type-one</UUID>{info_source}<ShortName>{site_name}</ShortName></Entity>
    <Entity xsi:type="SegmentType"><UUID>segment-type-one</UUID><ShortName>{segment_name}</ShortName></Entity>
    <Entity xsi:type="MeasurementLocationType"><UUID>location-type-one</UUID><ShortName>{location_name}</ShortName><UOMQuantity><UUID>quantity-one</UUID></UOMQuantity></Entity>
    <Entity xsi:type="UOMQuantity"><UUID>quantity-one</UUID><ShortName>{quantity_name}</ShortName><ReferenceUnitOfMeasure><UUID>unit-one</UUID></ReferenceUnitOfMeasure></Entity>
    <Entity xsi:type="UnitOfMeasure"><UUID>unit-one</UUID><ShortName>{unit_name}</ShortName><UOMQuantity><UUID>quantity-one</UUID></UOMQuantity></Entity>
</CCOMData>
""",
        encoding="utf-8",
    )


def table_count(connection: sqlite3.Connection, table_name: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def reference_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table_name: table_count(connection, table_name)
        for table_name in EXPECTED_REFERENCE_COUNTS
    }


def business_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table_name: table_count(connection, table_name)
        for table_name in ("DimSite", "DimSegment", "DimMeasurementLocation", "FactMeasurement")
    }


def import_count(connection: sqlite3.Connection) -> int:
    return table_count(connection, "ReferenceDataImport")


def test_fresh_database_seeds_reference_data_from_canonical_xml(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    result = ReferenceDataSeeder(db_path, loaded_reference_data()).seed()

    assert result.seeded
    assert result.counts == EXPECTED_REFERENCE_COUNTS
    with sqlite3.connect(db_path) as connection:
        assert reference_counts(connection) == EXPECTED_REFERENCE_COUNTS
        assert import_count(connection) == 1
        info_sources = connection.execute(
            "SELECT InfoSourceUuid, ShortName FROM DimInfoSource ORDER BY InfoSourceUuid"
        ).fetchall()
        metadata = connection.execute(
            """
            SELECT SourceFileName, SourceFileHash, EntityCount, ImportVersion
            FROM ReferenceDataImport
            """
        ).fetchone()
    assert metadata[0].endswith("CCOM Reference Data.xml")
    assert metadata[1]
    assert metadata[2] == sum(EXPECTED_REFERENCE_COUNTS.values())
    assert metadata[3] == 3
    assert info_sources == [(MIMOSA_INFO_SOURCE_UUID, "MIMOSA CCOM Reference Database")]
    assert not DOCUMENT_INFO_SOURCE_UUIDS & {row[0] for row in info_sources}
    with sqlite3.connect(db_path) as connection:
        full_name_columns = {
            row[1]
            for table_name in (
                "DimSiteType",
                "DimSegmentType",
                "DimMeasurementLocationType",
                "DimUnit",
                "DimUomQuantity",
            )
            for row in connection.execute(f"PRAGMA table_info({table_name})")
        }
    assert "FullName" not in full_name_columns


def test_repeated_startup_does_not_duplicate_reference_rows(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)
    reference_data = loaded_reference_data()

    first = ReferenceDataSeeder(db_path, reference_data).seed()
    second = ReferenceDataSeeder(db_path, reference_data).seed()

    assert first.seeded
    assert not second.seeded
    assert second.reason == "already_seeded"
    with sqlite3.connect(db_path) as connection:
        assert reference_counts(connection) == EXPECTED_REFERENCE_COUNTS
        assert import_count(connection) == 1


def test_changed_hash_does_not_reseed_already_seeded_database(tmp_path) -> None:
    xml_path = tmp_path / "reference.xml"
    write_minimal_reference_xml(xml_path, site_name="Site One")
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    seed_reference_data(db_path, loaded_reference_data(xml_path))
    write_minimal_reference_xml(xml_path, site_name="Site One Updated")
    result = seed_reference_data(db_path, loaded_reference_data(xml_path))

    assert not result.seeded
    assert result.reason == "already_seeded"
    with sqlite3.connect(db_path) as connection:
        short_name = connection.execute(
            "SELECT ShortName FROM DimSiteType WHERE SiteTypeUuid = 'site-type-one'"
        ).fetchone()[0]
        assert import_count(connection) == 1
    assert short_name == "Site One"


def test_uuid_upsert_updates_existing_reference_row(tmp_path) -> None:
    xml_path = tmp_path / "reference.xml"
    write_minimal_reference_xml(xml_path, segment_name="Drive, Motor")
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    ReferenceDataSeeder(db_path, loaded_reference_data(xml_path)).seed()
    write_minimal_reference_xml(xml_path, segment_name="Drive, Generator")
    second = ReferenceDataSeeder(db_path, loaded_reference_data(xml_path)).seed()

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT ShortName
            FROM DimSegmentType
            WHERE SegmentTypeUuid = 'segment-type-one'
            """
        ).fetchone()
        count = connection.execute(
            "SELECT COUNT(*) FROM DimSegmentType WHERE SegmentTypeUuid = 'segment-type-one'"
        ).fetchone()[0]

    assert not second.seeded
    assert row == ("Drive, Motor",)
    assert count == 1


def test_unresolved_info_source_uuid_does_not_break_reference_seeding(tmp_path) -> None:
    xml_path = tmp_path / "reference.xml"
    write_minimal_reference_xml(
        xml_path,
        site_name="Document Sourced Site Type",
        include_unresolved_info_source=True,
    )
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    result = ReferenceDataSeeder(db_path, loaded_reference_data(xml_path)).seed()

    assert result.seeded
    with sqlite3.connect(db_path) as connection:
        info_source_count = table_count(connection, "DimInfoSource")
        site_type = connection.execute(
            """
            SELECT InfoSourceUuid, InfoSourceKey
            FROM DimSiteType
            WHERE SiteTypeUuid = 'site-type-one'
            """
        ).fetchone()

    assert info_source_count == 0
    assert site_type == ("document-source", None)


def test_reference_seed_does_not_delete_discovered_data(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO DimSite(SiteUuid, SiteName, FirstSeenUtc, LastSeenUtc)
            VALUES ('discovered-site', 'Discovered Site', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
            """
        )
        connection.commit()

    seed_reference_data(db_path, loaded_reference_data())

    with sqlite3.connect(db_path) as connection:
        discovered_count = connection.execute(
            "SELECT COUNT(*) FROM DimSite WHERE SiteUuid = 'discovered-site'"
        ).fetchone()[0]
        assert reference_counts(connection) == EXPECTED_REFERENCE_COUNTS
    assert discovered_count == 1


def test_seed_fails_clearly_when_unseeded_database_reference_xml_is_missing(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)
    reference_data = ReferenceDataService(str(tmp_path / "missing.xml"), "CCOM Reference Data")

    with pytest.raises(ReferenceDataInitializationError, match="required to initialize"):
        seed_reference_data(db_path, reference_data)

    with sqlite3.connect(db_path) as connection:
        assert import_count(connection) == 0
        assert reference_counts(connection) == {
            "DimSiteType": 0,
            "DimSegmentType": 0,
            "DimMeasurementLocationType": 0,
            "DimUnit": 0,
            "DimUomQuantity": 0,
        }


def test_seeded_database_does_not_access_missing_reference_xml(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)
    ReferenceDataSeeder(db_path, loaded_reference_data()).seed()
    reference_data = ReferenceDataService(str(tmp_path / "missing.xml"), "CCOM Reference Data")

    result = ReferenceDataSeeder(db_path, reference_data).seed()

    assert not result.seeded
    assert result.reason == "already_seeded"
    with sqlite3.connect(db_path) as connection:
        assert import_count(connection) == 1
        assert reference_counts(connection) == EXPECTED_REFERENCE_COUNTS


def test_startup_imports_authoritative_reference_data_without_business_data(tmp_path) -> None:
    db_path = tmp_path / "startup.db"
    original_db_path = settings.discovery_database_path
    original_reference_path = settings.reference_data_path
    try:
        object.__setattr__(settings, "discovery_database_path", str(db_path))
        object.__setattr__(settings, "reference_data_path", str(REFERENCE_XML))

        with TestClient(app) as client:
            response = client.get("/")
    finally:
        object.__setattr__(settings, "discovery_database_path", original_db_path)
        object.__setattr__(settings, "reference_data_path", original_reference_path)

    assert response.status_code == 200
    with sqlite3.connect(db_path) as connection:
        assert reference_counts(connection) == EXPECTED_REFERENCE_COUNTS
        assert import_count(connection) == 1
        assert business_counts(connection) == {
            "DimSite": 0,
            "DimSegment": 0,
            "DimMeasurementLocation": 0,
            "FactMeasurement": 0,
        }
        assert connection.execute(
            "SELECT COUNT(*) FROM DimSegment WHERE SegmentUuid = 'segment-1' OR SegmentName = 'Recovered Segment'"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM DimMeasurementLocation WHERE MeasurementLocationUuid = 'location-1'"
        ).fetchone()[0] == 0


def test_repeated_startup_does_not_duplicate_reference_import(tmp_path) -> None:
    db_path = tmp_path / "startup.db"
    original_db_path = settings.discovery_database_path
    original_reference_path = settings.reference_data_path
    try:
        object.__setattr__(settings, "discovery_database_path", str(db_path))
        object.__setattr__(settings, "reference_data_path", str(REFERENCE_XML))

        with TestClient(app) as client:
            assert client.get("/").status_code == 200
        with TestClient(app) as client:
            assert client.get("/").status_code == 200
    finally:
        object.__setattr__(settings, "discovery_database_path", original_db_path)
        object.__setattr__(settings, "reference_data_path", original_reference_path)

    with sqlite3.connect(db_path) as connection:
        assert reference_counts(connection) == EXPECTED_REFERENCE_COUNTS
        assert import_count(connection) == 1
        assert business_counts(connection) == {
            "DimSite": 0,
            "DimSegment": 0,
            "DimMeasurementLocation": 0,
            "FactMeasurement": 0,
        }


def test_startup_fails_when_unseeded_reference_xml_is_missing(tmp_path) -> None:
    db_path = tmp_path / "startup.db"
    original_db_path = settings.discovery_database_path
    original_reference_path = settings.reference_data_path
    try:
        object.__setattr__(settings, "discovery_database_path", str(db_path))
        object.__setattr__(settings, "reference_data_path", str(tmp_path / "missing.xml"))

        with pytest.raises(ReferenceDataInitializationError, match="required to initialize"):
            with TestClient(app):
                pass
    finally:
        object.__setattr__(settings, "discovery_database_path", original_db_path)
        object.__setattr__(settings, "reference_data_path", original_reference_path)

    assert db_path.exists()
    with sqlite3.connect(db_path) as connection:
        assert import_count(connection) == 0


def test_seeded_startup_succeeds_when_reference_xml_is_missing(tmp_path) -> None:
    db_path = tmp_path / "startup.db"
    initialize_database(db_path)
    ReferenceDataSeeder(db_path, loaded_reference_data()).seed()
    original_db_path = settings.discovery_database_path
    original_reference_path = settings.reference_data_path
    try:
        object.__setattr__(settings, "discovery_database_path", str(db_path))
        object.__setattr__(settings, "reference_data_path", str(tmp_path / "missing.xml"))

        with TestClient(app) as client:
            response = client.get("/api/reference-data/segment-types")
    finally:
        object.__setattr__(settings, "discovery_database_path", original_db_path)
        object.__setattr__(settings, "reference_data_path", original_reference_path)

    assert response.status_code == 200
    assert len(response.json()) == EXPECTED_REFERENCE_COUNTS["DimSegmentType"]


def test_reference_parser_reads_unit_conversion_metadata_from_xml() -> None:
    reference_data = loaded_reference_data()
    units = {
        entry.uuid: entry
        for entry in reference_data.get_all_entries()
        if entry.class_name == "UnitOfMeasure"
    }

    watts = units[WATTS_UNIT_UUID]
    kilowatts = units[KILOWATTS_UNIT_UUID]

    assert watts.short_name == "Watts"
    assert watts.uom_quantity == POWER_UOM_QUANTITY_UUID
    assert watts.conversion_scale == "1"
    assert watts.conversion_offset == "0"
    assert kilowatts.short_name == "Kilowatts"
    assert kilowatts.uom_quantity == POWER_UOM_QUANTITY_UUID
    assert kilowatts.conversion_scale == "0.001"
    assert kilowatts.conversion_offset == "0"


def test_unit_conversion_metadata_is_seeded_without_conversion_logic(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    ReferenceDataSeeder(db_path, loaded_reference_data()).seed()

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT UnitUuid, ShortName, UomQuantityUuid, ConversionScale, ConversionOffset
            FROM DimUnit
            WHERE UnitUuid IN (?, ?)
            ORDER BY UnitUuid
            """,
            (WATTS_UNIT_UUID, KILOWATTS_UNIT_UUID),
        ).fetchall()
        non_null_conversion_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM DimUnit
            WHERE ConversionScale IS NOT NULL
              AND ConversionOffset IS NOT NULL
            """
        ).fetchone()[0]

    assert rows == [
        (WATTS_UNIT_UUID, "Watts", POWER_UOM_QUANTITY_UUID, 1.0, 0.0),
        (KILOWATTS_UNIT_UUID, "Kilowatts", POWER_UOM_QUANTITY_UUID, 0.001, 0.0),
    ]
    assert non_null_conversion_count == 249


def test_seeder_version_change_triggers_reload_when_hash_is_unchanged(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)
    reference_data = loaded_reference_data()

    ReferenceDataSeeder(db_path, reference_data).seed()
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE ReferenceDataImport SET ImportVersion = 1"
        )
        connection.execute(
            "UPDATE DimUnit SET ConversionScale = NULL WHERE UnitUuid = ?",
            (KILOWATTS_UNIT_UUID,),
        )
        connection.commit()

    result = ReferenceDataSeeder(db_path, reference_data).seed()

    assert result.seeded
    with sqlite3.connect(db_path) as connection:
        restored_scale = connection.execute(
            "SELECT ConversionScale FROM DimUnit WHERE UnitUuid = ?",
            (KILOWATTS_UNIT_UUID,),
        ).fetchone()[0]
        latest_import_version = connection.execute(
            "SELECT MAX(ImportVersion) FROM ReferenceDataImport"
        ).fetchone()[0]
        assert import_count(connection) == 2

    assert restored_scale == 0.001
    assert latest_import_version == 3


def test_invalid_reference_file_rolls_back_without_success_marker(tmp_path) -> None:
    xml_path = tmp_path / "invalid.xml"
    xml_path.write_text("<not-closed", encoding="utf-8")
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    with pytest.raises(ReferenceDataInitializationError, match="failed to load"):
        ReferenceDataSeeder(db_path, ReferenceDataService(str(xml_path), "CCOM Reference Data")).seed()

    with sqlite3.connect(db_path) as connection:
        assert import_count(connection) == 0
        assert reference_counts(connection) == {
            "DimSiteType": 0,
            "DimSegmentType": 0,
            "DimMeasurementLocationType": 0,
            "DimUnit": 0,
            "DimUomQuantity": 0,
        }


def test_segment_type_options_read_from_sqlite_with_deterministic_order(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.executemany(
            "INSERT INTO DimSegmentType(SegmentTypeUuid, ShortName) VALUES (?, ?)",
            [("segment-type-b", "Pump"), ("segment-type-a", "Motor"), ("segment-type-c", "Motor")],
        )
        connection.commit()

    entries = get_segment_type_entries(db_path)

    assert [(entry.uuid, entry.short_name) for entry in entries] == [
        ("segment-type-a", "Motor"),
        ("segment-type-c", "Motor"),
        ("segment-type-b", "Pump"),
    ]


def test_measurement_location_type_options_read_from_sqlite_with_deterministic_order(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.executemany(
            "INSERT INTO DimMeasurementLocationType(MeasurementLocationTypeUuid, ShortName) VALUES (?, ?)",
            [("location-type-b", "Velocity"), ("location-type-a", "Current"), ("location-type-c", "Current")],
        )
        connection.commit()

    entries = get_measurement_location_type_entries(db_path)

    assert [(entry.uuid, entry.short_name) for entry in entries] == [
        ("location-type-a", "Current"),
        ("location-type-c", "Current"),
        ("location-type-b", "Velocity"),
    ]

