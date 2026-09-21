from __future__ import annotations

import sqlite3
from pathlib import Path

from app.models import ReferenceDataEntry
from app.storage.reference_data_seed import REFERENCE_DATA_SEEDER_VERSION, REFERENCE_TABLES


def get_reference_data_status(db_path: str | Path) -> dict[str, object]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        latest = connection.execute(
            """
            SELECT SourceFileName, ImportedUtc, EntityCount, ImportVersion
            FROM ReferenceDataImport
            WHERE ImportVersion >= ?
            ORDER BY ReferenceDataImportKey DESC
            LIMIT 1
            """,
            (REFERENCE_DATA_SEEDER_VERSION,),
        ).fetchone()
        counts = _reference_counts(connection)

    is_loaded = latest is not None and all(count > 0 for count in counts.values())
    return {
        "status": "loaded" if is_loaded else "unseeded",
        "isLoaded": is_loaded,
        "filePath": latest["SourceFileName"] if latest else None,
        "sheetName": None,
        "warning": None if is_loaded else "Reference data has not been seeded.",
        "classesLoaded": {},
        "importVersion": latest["ImportVersion"] if latest else None,
        "importTimestamp": latest["ImportedUtc"] if latest else None,
        "entityCount": latest["EntityCount"] if latest else 0,
        "counts": {
            "siteTypes": counts["DimSiteType"],
            "segmentTypes": counts["DimSegmentType"],
            "measurementLocationTypes": counts["DimMeasurementLocationType"],
            "measurementTypes": 0,
            "unitsOfMeasure": counts["DimUnit"],
            "uomQuantities": counts["DimUomQuantity"],
        },
    }


def get_segment_type_entries(db_path: str | Path) -> list[ReferenceDataEntry]:
    return _reference_entries(
        db_path,
        class_name="SegmentType",
        uuid_column="SegmentTypeUuid",
        name_column="ShortName",
        table_name="DimSegmentType",
    )


def get_measurement_location_type_entries(db_path: str | Path) -> list[ReferenceDataEntry]:
    return _reference_entries(
        db_path,
        class_name="MeasurementLocationType",
        uuid_column="MeasurementLocationTypeUuid",
        name_column="ShortName",
        table_name="DimMeasurementLocationType",
    )


def get_unit_of_measure_entries(db_path: str | Path) -> list[ReferenceDataEntry]:
    return _reference_entries(
        db_path,
        class_name="UnitOfMeasure",
        uuid_column="UnitUuid",
        name_column="ShortName",
        table_name="DimUnit",
    )


def get_currency_unit_entries(db_path: str | Path) -> list[ReferenceDataEntry]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT unit.UnitUuid, unit.ShortName
            FROM DimUnit unit
            JOIN DimUomQuantity quantity
                ON quantity.UomQuantityKey = unit.UomQuantityKey
            WHERE quantity.ShortName = 'Currency'
            ORDER BY unit.ShortName, unit.UnitUuid
            """
        ).fetchall()
    return [
        ReferenceDataEntry(class_name="UnitOfMeasure", uuid=row[0], short_name=row[1])
        for row in rows
    ]


def _reference_entries(
    db_path: str | Path,
    *,
    class_name: str,
    uuid_column: str,
    name_column: str,
    table_name: str,
) -> list[ReferenceDataEntry]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT {uuid_column}, {name_column}
            FROM {table_name}
            ORDER BY {name_column}, {uuid_column}
            """
        ).fetchall()
    return [
        ReferenceDataEntry(class_name=class_name, uuid=row[0], short_name=row[1])
        for row in rows
    ]


def _reference_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table_name: int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
        for table_name in REFERENCE_TABLES
    }
