import sqlite3

from app.storage.database import CURRENT_SCHEMA_VERSION, initialize_database
from scripts.inspect_database_schema import collect_schema_report


def test_collect_schema_report_includes_core_database_metadata(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    report = collect_schema_report(db_path)

    assert report["schema_version"] == CURRENT_SCHEMA_VERSION
    assert any(table["name"] == "FactMeasurement" for table in report["tables"])
    assert any(view["name"] == "vw_grafana_measurements" and view["sql"] for view in report["views"])
    assert any(
        index["name"] == "UX_FactMeasurement_LocationTimestamp" and index["unique"]
        for index in report["indexes"]
    )

    fact_table = next(table for table in report["tables"] if table["name"] == "FactMeasurement")
    assert fact_table["primary_key"] == ["MeasurementFactKey"]
    assert fact_table["row_count"] == 0
    assert not any(foreign_key["table"] == "DiscoveryRun" for foreign_key in fact_table["foreign_keys"])
    assert {
        foreign_key["from"]
        for foreign_key in fact_table["foreign_keys"]
    } == {"InfoSourceKey", "UnitKey", "MeasurementLocationKey"}


def test_collect_schema_report_does_not_modify_database(tmp_path) -> None:
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        before = connection.execute("PRAGMA data_version").fetchone()[0]
        version_count_before = connection.execute("SELECT COUNT(*) FROM SchemaVersion").fetchone()[0]

    collect_schema_report(db_path)

    with sqlite3.connect(db_path) as connection:
        after = connection.execute("PRAGMA data_version").fetchone()[0]
        version_count_after = connection.execute("SELECT COUNT(*) FROM SchemaVersion").fetchone()[0]

    assert after == before
    assert version_count_after == version_count_before
