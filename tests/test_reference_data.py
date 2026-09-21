from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app, settings
from app.models import ReferenceDataEntry
from app.services.measurement_discovery_service import MeasurementDiscoveryService
from tests.fake_discovery_client import MOTOR_DE, MockDiscoveryClient
from app.services.reference_data_service import ReferenceDataService, entry_matches_value
from app.services.segment_discovery_service import SegmentDiscoveryService
from app.storage.database import initialize_database
from app.storage.reference_data_seed import ReferenceDataSeeder


REFERENCE_XML = Path("docs/CCOM Reference Data.xml")


def loaded_reference_data(path: Path = REFERENCE_XML) -> ReferenceDataService:
    service = ReferenceDataService(str(path), "CCOM Reference Data")
    service.load()
    return service


def write_reference_xml(path: Path) -> None:
    path.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<CCOMData xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.mimosa.org/ccom4">
    <Entity xsi:type="SegmentType">
        <UUID>segment-type-pump-train</UUID>
        <InfoSource><UUID>info-source-one</UUID></InfoSource>
        <Created>2026-01-01T00:00:00</Created>
        <EffectiveStatusType><UUID>status-active</UUID></EffectiveStatusType>
        <ShortName>Pump Train</ShortName>
        <FullName>Pump Train Full Name</FullName>
    </Entity>
    <Entity xsi:type="MeasurementLocationType">
        <UUID>location-type-bearing</UUID>
        <ShortName>Bearing</ShortName>
    </Entity>
    <Entity xsi:type="MeasurementSourceType">
        <UUID>measurement-type-vibration</UUID>
        <ShortName>Vibration</ShortName>
    </Entity>
    <Entity xsi:type="UnitOfMeasure">
        <UUID>unit-mm-s</UUID>
        <ShortName>mm/s</ShortName>
        <FullName>Millimeters per second</FullName>
        <UOMQuantity><UUID>uom-quantity-velocity</UUID></UOMQuantity>
    </Entity>
    <Entity xsi:type="SiteType">
        <UUID>site-type-plant</UUID>
        <ShortName>Plant</ShortName>
    </Entity>
    <Entity xsi:type="UOMQuantity">
        <UUID>uom-quantity-velocity</UUID>
        <ShortName>Velocity</ShortName>
        <ReferenceUnitOfMeasure><UUID>unit-mm-s</UUID></ReferenceUnitOfMeasure>
    </Entity>
    <Entity xsi:type="AssetType">
        <UUID>asset-type-motor</UUID>
        <ShortName>Motor</ShortName>
        <Description>Should not be loaded for portal filters yet</Description>
    </Entity>
</CCOMData>
""",
        encoding="utf-8",
    )


def test_reference_data_entry_creation() -> None:
    entry = ReferenceDataEntry(
        class_name="SiteType",
        uuid="site-type-plant",
        short_name="Plant",
        full_name="Industrial Plant",
    )

    assert entry.display_name == "Plant"


def test_reference_data_service_loads_needed_classes(tmp_path: Path) -> None:
    xml_path = tmp_path / "reference.xml"
    write_reference_xml(xml_path)

    service = ReferenceDataService(str(xml_path), "CCOM Reference Data")
    service.load()

    assert service.is_loaded()
    assert service.get_classes_loaded() == [
        "MeasurementLocationType",
        "MeasurementSourceType",
        "SegmentType",
        "UnitOfMeasure",
    ]
    assert len(service.get_segment_types()) == 1
    assert len(service.get_measurement_location_types()) == 1
    assert len(service.get_measurement_types()) == 1
    assert len(service.get_units_of_measure()) == 1
    assert service.get_segment_types()[0].created == "2026-01-01T00:00:00"
    assert service.get_segment_types()[0].info_source_uuid == "info-source-one"
    assert service.get_segment_types()[0].effective_status_type_uuid == "status-active"
    assert service.get_units_of_measure()[0].uom_quantity == "uom-quantity-velocity"
    assert "AssetType" not in service.get_classes_loaded()


def test_reference_data_service_fuzzy_mapping(tmp_path: Path) -> None:
    xml_path = tmp_path / "reference.xml"
    write_reference_xml(xml_path)

    service = ReferenceDataService(
        str(xml_path),
        "CCOM Reference Data",
        class_mapping={
            "segment_types": ["MissingSegmentClass"],
            "measurement_location_types": ["MissingLocationClass"],
            "measurement_types": ["MissingMeasurementClass"],
            "units_of_measure": ["MissingUnitClass"],
        },
    )
    service.load()

    assert service.get_segment_types()[0].class_name == "SegmentType"
    assert service.get_measurement_location_types()[0].class_name == "MeasurementLocationType"
    assert service.get_measurement_types()[0].class_name == "MeasurementSourceType"
    assert service.get_units_of_measure()[0].class_name == "UnitOfMeasure"


def test_reference_data_xml_contains_seedable_dimension_classes() -> None:
    service = ReferenceDataService(str(REFERENCE_XML), "CCOM Reference Data")
    service.load()

    assert service.is_loaded()
    assert service.get_entries_by_class("SiteType")
    assert service.get_entries_by_class("SegmentType")
    assert service.get_entries_by_class("MeasurementLocationType")
    assert service.get_entries_by_class("UnitOfMeasure")
    assert service.get_entries_by_class("UOMQuantity")
    assert all(entry.uuid for entry in service.get_entries_by_class("SiteType"))
    assert all(entry.short_name for entry in service.get_entries_by_class("SiteType"))


def test_missing_reference_file_does_not_crash() -> None:
    service = ReferenceDataService("missing-reference-file.xml", "CCOM Reference Data")
    service.load()

    assert service.status == "missing"
    assert not service.is_loaded()


def test_page_renders_from_seeded_sqlite_when_reference_file_is_missing(tmp_path) -> None:
    db_path = tmp_path / "seeded.db"
    initialize_database(db_path)
    ReferenceDataSeeder(db_path, loaded_reference_data()).seed()
    original_settings_path = settings.discovery_database_path
    original_reference_path = settings.reference_data_path
    try:
        object.__setattr__(settings, "discovery_database_path", str(db_path))
        object.__setattr__(settings, "reference_data_path", str(tmp_path / "missing.xml"))
        with TestClient(app) as client:
            response = client.get("/")
    finally:
        object.__setattr__(settings, "discovery_database_path", original_settings_path)
        object.__setattr__(settings, "reference_data_path", original_reference_path)

    assert response.status_code == 200
    assert "Reference Data Loaded" in response.text


def test_dropdown_filter_matching_by_uuid_and_display_name() -> None:
    entries = [
        ReferenceDataEntry(
            class_name="SegmentType",
            uuid="segment-type-pump-train",
            short_name="Pump Train",
            full_name="Pump Train Full Name",
        )
    ]

    assert entry_matches_value("Pump Train", "segment-type-pump-train", entries)
    assert entry_matches_value("Pump Train", "Pump Train", entries)
    assert SegmentDiscoveryService(MockDiscoveryClient()).get_segments(
        "11111111-1111-4111-8111-111111111111",
        segment_type="segment-type-pump-train",
        segment_type_entries=entries,
    )


def test_measurement_filter_matching_by_uuid() -> None:
    entries = [
        ReferenceDataEntry(
            class_name="MeasurementSourceType",
            uuid="measurement-type-vibration",
            short_name="Vibration",
        )
    ]

    results = MeasurementDiscoveryService(MockDiscoveryClient()).get_measurements(
        MOTOR_DE,
        measurement_type="measurement-type-vibration",
        measurement_type_entries=entries,
    )

    assert results
    assert all(item.measurement_type == "Vibration" for item in results)


def test_reference_data_api_endpoints(tmp_path) -> None:
    original_database = getattr(app.state, "database", None)
    original_settings_path = settings.discovery_database_path
    db_path = tmp_path / "reference-api.db"
    try:
        object.__setattr__(settings, "discovery_database_path", str(db_path))
        with TestClient(app) as client:
            status = client.get("/api/reference-data/status")
            segment_types = client.get("/api/reference-data/segment-types")
    finally:
        object.__setattr__(settings, "discovery_database_path", original_settings_path)
        if original_database is not None:
            app.state.database = original_database

    assert status.status_code == 200
    assert segment_types.status_code == 200
    assert {"uuid", "shortName", "fullName", "displayName", "className", "description"} <= set(
        segment_types.json()[0]
    )

