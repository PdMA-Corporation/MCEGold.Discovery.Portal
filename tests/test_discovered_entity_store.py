import sqlite3
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.api.routes import (
    persist_discovered_measurements,
    persist_discovered_measurement_locations,
    persist_discovered_segments,
    persist_discovered_sites,
)
from app.models import Measurement, MeasurementLocation, Segment, Site
from app.storage import discovered_entity_store
from app.storage.database import initialize_database
from app.storage.discovered_entity_store import DiscoveredEntityStore


def open_initialized_database(tmp_path):
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def site(
    site_uuid: str = "site-1",
    site_name: str = "Installation Site",
    site_type: str = "Office Building",
) -> Site:
    return Site(
        site_uuid=site_uuid,
        site_name=site_name,
        site_type=site_type,
        status="Active",
        region="",
        description="",
    )


def segment(
    segment_uuid: str = "segment-1",
    site_uuid: str = "site-1",
    segment_name: str = "Compressor",
    segment_type_uuid: str | None = "segment-type-compressor",
) -> Segment:
    return Segment(
        segment_uuid=segment_uuid,
        site_uuid=site_uuid,
        segment_name=segment_name,
        segment_type="Compressor",
        segment_type_uuid=segment_type_uuid,
        status="Active",
        description="",
    )


def measurement_location(
    location_uuid: str = "location-1",
    segment_uuid: str = "segment-1",
    location_name: str = "Average Current, Stator",
    type_uuid: str = "location-type-current",
    unit_uuid: str | None = "unit-amps",
) -> MeasurementLocation:
    return MeasurementLocation(
        location_uuid=location_uuid,
        segment_uuid=segment_uuid,
        location_name=location_name,
        location_type="Average Current",
        type_uuid=type_uuid,
        value_class="Measure",
        unit="Amperes",
        unit_uuid=unit_uuid,
        uom_quantity="Electric Current",
        uom_quantity_uuid="uom-current" if unit_uuid else None,
        reference_unit_uuid=unit_uuid,
        conversion_scale=1.0,
        conversion_offset=0.0,
        status="Active",
        description="",
    )


def measurement(
    measurement_uuid: str = "measurement-1",
    location_uuid: str = "location-1",
    value: float = 42.5,
    timestamp_utc: datetime | None = None,
) -> Measurement:
    return Measurement(
        measurement_uuid=measurement_uuid,
        location_uuid=location_uuid,
        measurement_name="Average Current",
        measurement_type="Measure",
        value=value,
        unit="Amperes",
        unit_uuid="unit-amps",
        timestamp_utc=timestamp_utc or datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        status="Good",
    )


def fetch_sites(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    return list(connection.execute("SELECT * FROM DimSite ORDER BY SiteUuid"))


def fetch_segments(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    return list(connection.execute("SELECT * FROM DimSegment ORDER BY SegmentUuid"))


def fetch_measurement_locations(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    return list(
        connection.execute(
            "SELECT * FROM DimMeasurementLocation ORDER BY MeasurementLocationUuid"
        )
    )


def fetch_measurements(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    return list(connection.execute("SELECT * FROM FactMeasurement ORDER BY MeasurementFactKey"))


def seed_site(connection: sqlite3.Connection, site_uuid: str = "site-1") -> None:
    DiscoveredEntityStore(connection).save_site(site(site_uuid=site_uuid))


def seed_site_and_segment(
    connection: sqlite3.Connection,
    *,
    site_uuid: str = "site-1",
    segment_uuid: str = "segment-1",
) -> None:
    store = DiscoveredEntityStore(connection)
    store.save_site(site(site_uuid=site_uuid))
    store.save_segment(segment(segment_uuid=segment_uuid, site_uuid=site_uuid))


def seed_measurement_location(connection: sqlite3.Connection) -> None:
    seed_site_and_segment(connection)
    DiscoveredEntityStore(connection).save_measurement_location(measurement_location())


def test_save_site_inserts_new_site(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)

    DiscoveredEntityStore(connection).save_site(site())

    rows = fetch_sites(connection)
    assert len(rows) == 1
    assert rows[0]["SiteUuid"] == "site-1"
    assert rows[0]["SiteName"] == "Installation Site"
    assert rows[0]["SiteTypeUuid"] is None
    assert rows[0]["FirstSeenUtc"]
    assert rows[0]["LastSeenUtc"]


def test_save_site_updates_existing_site(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    store = DiscoveredEntityStore(connection)
    store.save_site(site(site_name="Installation Site"))

    store.save_site(site(site_name="Updated Site"))

    rows = fetch_sites(connection)
    assert len(rows) == 1
    assert rows[0]["SiteName"] == "Updated Site"


def test_save_site_does_not_duplicate_site_uuid(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    store = DiscoveredEntityStore(connection)

    store.save_site(site())
    store.save_site(site())

    count = connection.execute(
        "SELECT COUNT(*) FROM DimSite WHERE SiteUuid = 'site-1'"
    ).fetchone()[0]
    assert count == 1


def test_save_sites_handles_multiple_sites(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)

    DiscoveredEntityStore(connection).save_sites(
        [
            site(site_uuid="site-1", site_name="Installation Site"),
            site(site_uuid="site-2", site_name="Warehouse Site"),
        ]
    )

    rows = fetch_sites(connection)
    assert [row["SiteUuid"] for row in rows] == ["site-1", "site-2"]


def test_save_site_leaves_optional_values_null(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    sparse_site = SimpleNamespace(site_uuid="site-1", site_name="Installation Site")

    DiscoveredEntityStore(connection).save_site(sparse_site)

    row = fetch_sites(connection)[0]
    assert row["SiteTypeUuid"] is None
    assert "DiscoveryRunKey" not in row.keys()


def test_persistence_failure_does_not_affect_caller(monkeypatch) -> None:
    class FailingStore:
        def __init__(self, connection) -> None:
            pass

        def save_sites(self, sites) -> None:
            raise RuntimeError("database unavailable")

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, statement):
            return None

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(database=SimpleNamespace(db_path="unused.db"))
        )
    )
    monkeypatch.setattr("app.api.routes.sqlite3.connect", lambda path: FakeConnection())
    monkeypatch.setattr("app.api.routes.DiscoveredEntityStore", FailingStore)

    persist_discovered_sites(request, [site()])


def test_save_segment_inserts_new_segment(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site(connection)

    DiscoveredEntityStore(connection).save_segment(segment())

    rows = fetch_segments(connection)
    assert len(rows) == 1
    assert rows[0]["SegmentUuid"] == "segment-1"
    assert rows[0]["SegmentName"] == "Compressor"
    assert rows[0]["SegmentTypeUuid"] == "segment-type-compressor"
    assert rows[0]["SiteUuid"] == "site-1"
    assert rows[0]["SiteKey"] is not None
    assert rows[0]["FirstSeenUtc"]
    assert rows[0]["LastSeenUtc"]


def test_save_segment_updates_existing_segment(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site(connection)
    store = DiscoveredEntityStore(connection)
    store.save_segment(segment(segment_name="Compressor"))

    store.save_segment(segment(segment_name="Updated Compressor"))

    rows = fetch_segments(connection)
    assert len(rows) == 1
    assert rows[0]["SegmentName"] == "Updated Compressor"


def test_save_segment_does_not_duplicate_segment_uuid(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site(connection)
    store = DiscoveredEntityStore(connection)

    store.save_segment(segment())
    store.save_segment(segment())

    count = connection.execute(
        "SELECT COUNT(*) FROM DimSegment WHERE SegmentUuid = 'segment-1'"
    ).fetchone()[0]
    assert count == 1


def test_save_segments_handles_multiple_segments(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site(connection)

    DiscoveredEntityStore(connection).save_segments(
        [
            segment(segment_uuid="segment-1", segment_name="Compressor"),
            segment(segment_uuid="segment-2", segment_name="Pump Train"),
        ]
    )

    rows = fetch_segments(connection)
    assert [row["SegmentUuid"] for row in rows] == ["segment-1", "segment-2"]


def test_save_segment_stores_site_uuid_relationship(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site(connection, site_uuid="site-parent")

    DiscoveredEntityStore(connection).save_segment(
        segment(segment_uuid="segment-1", site_uuid="site-parent")
    )

    rows = fetch_segments(connection)
    assert rows[0]["SiteUuid"] == "site-parent"
    assert rows[0]["SiteKey"] is not None


def test_save_segment_requires_persisted_parent_site(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    sparse_segment = SimpleNamespace(segment_uuid="segment-1", segment_name="Compressor")

    with pytest.raises(ValueError, match="parent SiteUuid"):
        DiscoveredEntityStore(connection).save_segment(sparse_segment)

    with pytest.raises(ValueError, match="parent site missing-site"):
        DiscoveredEntityStore(connection).save_segment(segment(site_uuid="missing-site"))


def test_segment_persistence_failure_does_not_affect_caller(monkeypatch) -> None:
    class FailingStore:
        def __init__(self, connection) -> None:
            pass

        def save_segments(self, segments) -> None:
            raise RuntimeError("database unavailable")

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, statement):
            return None

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(database=SimpleNamespace(db_path="unused.db"))
        )
    )
    monkeypatch.setattr("app.api.routes.sqlite3.connect", lambda path: FakeConnection())
    monkeypatch.setattr("app.api.routes.DiscoveredEntityStore", FailingStore)

    persist_discovered_segments(request, [segment()])


def test_save_measurement_location_inserts_new_location(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site_and_segment(connection)

    DiscoveredEntityStore(connection).save_measurement_location(
        measurement_location().model_dump()
    )

    rows = fetch_measurement_locations(connection)
    assert len(rows) == 1
    assert rows[0]["MeasurementLocationUuid"] == "location-1"
    assert rows[0]["MeasurementLocationName"] == "Average Current, Stator"
    assert rows[0]["MeasurementLocationTypeUuid"] == "location-type-current"
    assert "SiteUuid" not in rows[0].keys()
    assert "SiteKey" not in rows[0].keys()
    assert rows[0]["SegmentUuid"] == "segment-1"
    assert rows[0]["SegmentKey"] is not None
    assert rows[0]["DefaultUnitUuid"] == "unit-amps"
    assert rows[0]["UomQuantityUuid"] == "uom-current"
    assert rows[0]["FirstSeenUtc"]
    assert rows[0]["LastSeenUtc"]


def test_save_measurement_location_updates_existing_location(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site_and_segment(connection)
    store = DiscoveredEntityStore(connection)
    store.save_measurement_location(measurement_location(location_name="Average Current"))

    store.save_measurement_location(measurement_location(location_name="Updated Current"))

    rows = fetch_measurement_locations(connection)
    assert len(rows) == 1
    assert rows[0]["MeasurementLocationName"] == "Updated Current"


def test_save_measurement_location_does_not_duplicate_uuid(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site_and_segment(connection)
    store = DiscoveredEntityStore(connection)

    store.save_measurement_location(measurement_location())
    store.save_measurement_location(measurement_location())

    count = connection.execute(
        "SELECT COUNT(*) FROM DimMeasurementLocation WHERE MeasurementLocationUuid = 'location-1'"
    ).fetchone()[0]
    assert count == 1


def test_save_measurement_locations_handles_multiple_locations(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site_and_segment(connection)

    DiscoveredEntityStore(connection).save_measurement_locations(
        [
            measurement_location(location_uuid="location-1"),
            measurement_location(location_uuid="location-2", location_name="Temperature"),
        ]
    )

    rows = fetch_measurement_locations(connection)
    assert [row["MeasurementLocationUuid"] for row in rows] == ["location-1", "location-2"]


def test_save_measurement_location_stores_segment_relationship(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site_and_segment(connection, site_uuid="site-parent", segment_uuid="segment-parent")

    DiscoveredEntityStore(connection).save_measurement_location(
        measurement_location(segment_uuid="segment-parent").model_dump() | {"site_uuid": "ignored-site-context"}
    )

    row = fetch_measurement_locations(connection)[0]
    assert "SiteUuid" not in row.keys()
    assert "SiteKey" not in row.keys()
    assert row["SegmentUuid"] == "segment-parent"
    assert row["SegmentKey"] is not None


def test_save_measurement_location_requires_persisted_parent_segment(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    sparse_location = SimpleNamespace(
        location_uuid="location-1",
        location_name="Average Current",
    )

    with pytest.raises(ValueError, match="parent SegmentUuid"):
        DiscoveredEntityStore(connection).save_measurement_location(sparse_location)

    with pytest.raises(ValueError, match="parent segment missing-segment"):
        DiscoveredEntityStore(connection).save_measurement_location(
            measurement_location(segment_uuid="missing-segment")
        )


def test_save_measurement_location_keeps_percentage_and_number_unitless(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site_and_segment(connection)
    store = DiscoveredEntityStore(connection)

    store.save_measurement_locations(
        [
            measurement_location(
                location_uuid="percentage-location",
                unit_uuid="unit-percent",
            ).model_copy(update={"value_class": "Percentage"}),
            measurement_location(
                location_uuid="number-location",
                unit_uuid="unit-count",
            ).model_copy(update={"value_class": "Number"}),
        ]
    )

    rows = {
        row["MeasurementLocationUuid"]: row
        for row in fetch_measurement_locations(connection)
    }
    assert rows["percentage-location"]["DefaultUnitUuid"] is None
    assert rows["percentage-location"]["UomQuantityUuid"] is None
    assert rows["number-location"]["DefaultUnitUuid"] is None
    assert rows["number-location"]["UomQuantityUuid"] is None


def test_save_measurement_location_persists_info_source_reference_dimensions(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site_and_segment(connection)
    store = DiscoveredEntityStore(connection)
    location = measurement_location().model_dump() | {
        "site_uuid": "site-1",
        "info_source_uuid": "info-location",
        "info_source_short_name": "Location Source",
        "measurement_location_type_info_source_uuid": "info-location-type",
        "measurement_location_type_info_source_short_name": "Location Type Source",
        "unit_info_source_uuid": "info-unit",
        "unit_info_source_short_name": "Unit Source",
        "uom_quantity_uuid": "quantity-electric-current",
        "uom_quantity_info_source_uuid": "info-quantity",
        "uom_quantity_info_source_short_name": "Quantity Source",
    }

    store.save_measurement_location(location)

    connection.row_factory = sqlite3.Row
    info_sources = {
        row["InfoSourceUuid"]: row
        for row in connection.execute("SELECT * FROM DimInfoSource")
    }
    stored_location = connection.execute(
        "SELECT * FROM DimMeasurementLocation WHERE MeasurementLocationUuid = 'location-1'"
    ).fetchone()
    location_type = connection.execute(
        "SELECT * FROM DimMeasurementLocationType WHERE MeasurementLocationTypeUuid = 'location-type-current'"
    ).fetchone()
    unit = connection.execute(
        "SELECT * FROM DimUnit WHERE UnitUuid = 'unit-amps'"
    ).fetchone()
    uom_quantity = connection.execute(
        "SELECT * FROM DimUomQuantity WHERE UomQuantityUuid = 'quantity-electric-current'"
    ).fetchone()

    assert set(info_sources) == {"info-location", "info-location-type", "info-unit", "info-quantity"}
    assert info_sources["info-unit"]["ShortName"] == "Unit Source"
    assert stored_location["InfoSourceUuid"] == "info-location"
    assert stored_location["InfoSourceKey"] == info_sources["info-location"]["InfoSourceKey"]
    assert location_type["InfoSourceUuid"] == "info-location-type"
    assert location_type["InfoSourceKey"] == info_sources["info-location-type"]["InfoSourceKey"]
    assert unit["InfoSourceUuid"] == "info-unit"
    assert uom_quantity["InfoSourceUuid"] == "info-quantity"


def test_save_measurement_location_uuid_only_info_sources_do_not_create_placeholders(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site_and_segment(connection)
    store = DiscoveredEntityStore(connection)
    location = measurement_location().model_dump() | {
        "info_source_uuid": "info-location",
        "measurement_location_type_info_source_uuid": "info-location-type",
        "unit_info_source_uuid": "info-unit",
        "uom_quantity_uuid": "quantity-electric-current",
        "uom_quantity_info_source_uuid": "info-quantity",
    }

    store.save_measurement_location(location)
    store.save_measurement_location(location)

    connection.row_factory = sqlite3.Row
    counts = {
        table_name: connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        for table_name in (
            "DimInfoSource",
            "DimMeasurementLocation",
            "DimMeasurementLocationType",
            "DimUnit",
            "DimUomQuantity",
        )
    }
    stored_location = connection.execute(
        "SELECT InfoSourceUuid, InfoSourceKey FROM DimMeasurementLocation"
    ).fetchone()
    location_type = connection.execute(
        "SELECT InfoSourceUuid, InfoSourceKey FROM DimMeasurementLocationType"
    ).fetchone()
    unit = connection.execute("SELECT InfoSourceUuid FROM DimUnit").fetchone()
    uom_quantity = connection.execute("SELECT InfoSourceUuid FROM DimUomQuantity").fetchone()

    assert counts == {
        "DimInfoSource": 0,
        "DimMeasurementLocation": 1,
        "DimMeasurementLocationType": 1,
        "DimUnit": 1,
        "DimUomQuantity": 1,
    }
    assert dict(stored_location) == {"InfoSourceUuid": "info-location", "InfoSourceKey": None}
    assert dict(location_type) == {"InfoSourceUuid": "info-location-type", "InfoSourceKey": None}
    assert unit["InfoSourceUuid"] == "info-unit"
    assert uom_quantity["InfoSourceUuid"] == "info-quantity"


def test_measurement_location_persistence_failure_does_not_affect_caller(monkeypatch) -> None:
    class FailingStore:
        def __init__(self, connection) -> None:
            pass

        def save_measurement_locations(self, locations) -> None:
            raise RuntimeError("database unavailable")

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, statement):
            return None

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(database=SimpleNamespace(db_path="unused.db"))
        )
    )
    monkeypatch.setattr("app.api.routes.sqlite3.connect", lambda path: FakeConnection())
    monkeypatch.setattr("app.api.routes.DiscoveredEntityStore", FailingStore)

    persist_discovered_measurement_locations(request, [measurement_location()], "site-1")


def test_save_measurement_inserts_numeric_measurement(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_measurement_location(connection)

    DiscoveredEntityStore(connection).save_measurement(
        measurement().model_dump() | {"unit_uuid": "unit-amps"}
    )

    rows = fetch_measurements(connection)
    assert len(rows) == 1
    assert rows[0]["MeasurementTimestampUtc"] == "2026-01-01T12:00:00Z"
    assert rows[0]["MeasurementLocationUuid"] == "location-1"
    assert rows[0]["UnitUuid"] == "unit-amps"
    assert rows[0]["NumericValue"] == 42.5
    assert rows[0]["InsertedUtc"]
    assert "QualityCode" not in rows[0].keys()


def test_save_measurement_inherits_measure_location_default_unit(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site_and_segment(connection)
    store = DiscoveredEntityStore(connection)
    store.save_measurement_location(measurement_location())

    current_measurement = measurement().model_dump()
    current_measurement["unit_uuid"] = None
    store.save_measurement(current_measurement)

    row = fetch_measurements(connection)[0]
    location = fetch_measurement_locations(connection)[0]
    assert row["UnitUuid"] == "unit-amps"
    assert row["UnitKey"] == location["DefaultUnitKey"]


def test_save_measurement_rejects_incompatible_measure_unit(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site_and_segment(connection)
    store = DiscoveredEntityStore(connection)
    store.save_measurement_location(measurement_location())
    connection.execute(
        """
        INSERT INTO DimUomQuantity(UomQuantityUuid, ShortName)
        VALUES ('other-quantity', 'Other Quantity')
        """
    )
    other_quantity_key = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
    connection.execute(
        """
        INSERT INTO DimUnit(UnitUuid, ShortName, UomQuantityUuid, UomQuantityKey)
        VALUES ('unit-other', 'Other Unit', 'other-quantity', ?)
        """,
        (other_quantity_key,),
    )
    connection.commit()

    with pytest.raises(ValueError, match="does not belong"):
        store.save_measurement(measurement().model_dump() | {"unit_uuid": "unit-other"})


def test_save_measurement_rejects_percentage_unit(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_site_and_segment(connection)
    store = DiscoveredEntityStore(connection)
    store.save_measurement_location(
        measurement_location(unit_uuid=None).model_copy(update={"value_class": "Percentage"})
    )

    with pytest.raises(ValueError, match="must not carry a unit"):
        store.save_measurement(
            measurement().model_dump()
            | {
                "measurement_type": "Percentage",
                "unit_uuid": "unit-amps",
            }
        )


def test_save_measurement_inserts_named_runtime_info_source(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_measurement_location(connection)
    current_measurement = measurement().model_dump() | {
        "unit_uuid": "unit-amps",
        "info_source_uuid": "info-measurement",
        "info_source_short_name": "Measurement Runtime Source",
        "unit_info_source_uuid": "info-unit",
        "unit_info_source_short_name": "Unit Runtime Source",
    }

    DiscoveredEntityStore(connection).save_measurement(current_measurement)

    connection.row_factory = sqlite3.Row
    info_sources = {
        row["InfoSourceUuid"]: row["ShortName"]
        for row in connection.execute("SELECT InfoSourceUuid, ShortName FROM DimInfoSource")
    }
    assert info_sources == {
        "info-measurement": "Measurement Runtime Source",
        "info-unit": "Unit Runtime Source",
    }


def test_save_measurement_updates_named_info_source_and_preserves_first_seen(monkeypatch, tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_measurement_location(connection)
    store = DiscoveredEntityStore(connection)
    times = iter(
        [
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:05:00Z",
            "2026-01-01T00:05:00Z",
        ]
    )
    monkeypatch.setattr(discovered_entity_store, "_utc_now", lambda: next(times))

    store.save_measurement(
        measurement().model_dump()
        | {
            "info_source_uuid": "info-measurement",
            "info_source_short_name": "Original Source",
        }
    )
    store.save_measurement(
        measurement().model_dump()
        | {
            "info_source_uuid": "info-measurement",
            "info_source_short_name": "Updated Source",
        }
    )

    row = connection.execute(
        """
        SELECT ShortName, FirstSeenUtc, LastSeenUtc
        FROM DimInfoSource
        WHERE InfoSourceUuid = 'info-measurement'
        """
    ).fetchone()

    assert tuple(row) == ("Updated Source", "2026-01-01T00:00:00Z", "2026-01-01T00:05:00Z")


def test_save_measurement_uuid_only_info_source_does_not_create_placeholder(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_measurement_location(connection)

    DiscoveredEntityStore(connection).save_measurement(
        measurement().model_dump()
        | {
            "info_source_uuid": "info-measurement",
            "unit_info_source_uuid": "info-unit",
        }
    )

    assert connection.execute("SELECT COUNT(*) FROM DimInfoSource").fetchone()[0] == 0


def test_save_measurement_inserts_text_measurement(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_measurement_location(connection)
    text_measurement = SimpleNamespace(
        measurement_uuid="measurement-text-1",
        location_uuid="location-1",
        segment_uuid="segment-1",
        timestamp_utc="2026-01-01T12:05:00Z",
        text_value="Running",
    )

    with pytest.raises(ValueError, match="NumericValue is required"):
        DiscoveredEntityStore(connection).save_measurement(text_measurement)


def test_save_measurements_allows_same_location_at_different_timestamps(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_measurement_location(connection)

    DiscoveredEntityStore(connection).save_measurements(
        [
            measurement(timestamp_utc=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)),
            measurement(
                measurement_uuid="measurement-2",
                timestamp_utc=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
            ),
        ]
    )

    rows = fetch_measurements(connection)
    assert len(rows) == 2
    assert [row["MeasurementTimestampUtc"] for row in rows] == [
        "2026-01-01T12:00:00Z",
        "2026-01-01T12:01:00Z",
    ]


def test_save_measurements_allows_same_timestamp_for_different_locations(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_measurement_location(connection)
    DiscoveredEntityStore(connection).save_measurement_location(
        measurement_location(location_uuid="location-2")
    )

    DiscoveredEntityStore(connection).save_measurements(
        [
            measurement(location_uuid="location-1"),
            measurement(measurement_uuid="measurement-2", location_uuid="location-2"),
        ]
    )

    rows = fetch_measurements(connection)
    assert len(rows) == 2
    assert [row["MeasurementLocationUuid"] for row in rows] == ["location-1", "location-2"]


def test_save_measurement_ignores_quality_code_fields(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_measurement_location(connection)
    store = DiscoveredEntityStore(connection)
    current_measurement = measurement().model_dump() | {"unit_uuid": "unit-amps"}

    store.save_measurement(current_measurement)
    store.save_measurement(current_measurement | {"quality_code": "Reviewed", "QualityCode": "Good"})

    rows = fetch_measurements(connection)
    assert len(rows) == 1
    assert rows[0]["NumericValue"] == 42.5
    assert "QualityCode" not in rows[0].keys()


def test_save_measurement_changed_value_still_updates_same_location_and_timestamp(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_measurement_location(connection)
    store = DiscoveredEntityStore(connection)

    store.save_measurement(measurement(value=42.5).model_dump())
    store.save_measurement(measurement(value=99.9).model_dump())

    rows = fetch_measurements(connection)
    assert len(rows) == 1
    assert rows[0]["NumericValue"] == 99.9


def test_save_measurement_leaves_optional_values_null(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    seed_measurement_location(connection)
    sparse_measurement = SimpleNamespace(
        measurement_uuid="measurement-sparse",
        measurement_location_uuid="location-1",
        segment_uuid="segment-1",
        measurement_timestamp_utc="2026-01-01T12:00:00Z",
        numeric_value=10.0,
        value_class="Number",
    )

    DiscoveredEntityStore(connection).save_measurement(sparse_measurement)

    row = fetch_measurements(connection)[0]
    assert row["UnitUuid"] is None
    assert "QualityCode" not in row.keys()


def test_measurement_persistence_failure_does_not_affect_caller(monkeypatch) -> None:
    class FailingStore:
        def __init__(self, connection) -> None:
            pass

        def save_measurements(self, measurements) -> None:
            raise RuntimeError("database unavailable")

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, statement):
            return None

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(database=SimpleNamespace(db_path="unused.db"))
        )
    )
    monkeypatch.setattr("app.api.routes.sqlite3.connect", lambda path: FakeConnection())
    monkeypatch.setattr("app.api.routes.DiscoveredEntityStore", FailingStore)

    persist_discovered_measurements(request, [measurement()], measurement_location())


def test_grafana_view_returns_persisted_numeric_measurement(tmp_path) -> None:
    connection = open_initialized_database(tmp_path)
    site_key = connection.execute(
        """
        INSERT INTO DimSite(SiteUuid, SiteName, FirstSeenUtc, LastSeenUtc)
        VALUES ('site-1', 'Installation Site', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
        """
    ).lastrowid
    segment_key = connection.execute(
        """
        INSERT INTO DimSegment(SegmentUuid, SegmentName, SiteUuid, SiteKey, FirstSeenUtc, LastSeenUtc)
        VALUES ('segment-1', 'Compressor', 'site-1', ?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
        """,
        (site_key,),
    ).lastrowid
    unit_key = connection.execute(
        """
        INSERT INTO DimUnit(UnitUuid, ShortName)
        VALUES ('unit-amps', 'Amperes')
        """
    ).lastrowid
    location_type_key = connection.execute(
        """
        INSERT INTO DimMeasurementLocationType(MeasurementLocationTypeUuid, ShortName)
        VALUES ('location-type-current', 'Average Current')
        """
    ).lastrowid
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
    connection.commit()

    DiscoveredEntityStore(connection).save_measurement(
        measurement().model_dump() | {"unit_uuid": "unit-amps"}
    )

    connection.row_factory = sqlite3.Row
    row = connection.execute("SELECT * FROM vw_grafana_measurements").fetchone()
    assert row["time"] == "2026-01-01T12:00:00Z"
    assert row["site_name"] == "Installation Site"
    assert row["segment_name"] == "Compressor"
    assert row["measurement_location_name"] == "Average Current, Stator"
    assert row["measurement_location_type"] == "Average Current"
    assert row["stored_unit_name"] == "Amperes"
    assert row["value"] == 42.5


