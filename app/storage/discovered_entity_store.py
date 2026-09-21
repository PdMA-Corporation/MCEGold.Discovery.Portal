from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Iterable, Any


class DiscoveredEntityStore:
    """Small SQLite persistence helper for discovered catalog entities."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.row_factory = sqlite3.Row

    def save_site(self, site: Any) -> None:
        self.save_sites([site])

    def save_sites(self, sites: Iterable[Any]) -> None:
        prepared = [self._prepare_site(site) for site in sites]
        if not prepared:
            return

        try:
            self._save_info_sources(info_source for item in prepared for info_source in item["info_sources"])
            self._save_site_types(item["site_type"] for item in prepared)
            rows = [
                self._site_row(
                    item["source"],
                    item["info_source"],
                    self._info_source_key(item["info_source"]["uuid"]) if item["info_source"] else None,
                )
                for item in prepared
            ]
            self.connection.executemany(
                """
                INSERT INTO DimSite (
                    SiteUuid,
                    SiteName,
                    SiteTypeUuid,
                    SiteTypeKey,
                    InfoSourceUuid,
                    InfoSourceKey,
                    FirstSeenUtc,
                    LastSeenUtc
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(SiteUuid) DO UPDATE SET
                    SiteName = excluded.SiteName,
                    SiteTypeUuid = excluded.SiteTypeUuid,
                    SiteTypeKey = excluded.SiteTypeKey,
                    InfoSourceUuid = COALESCE(excluded.InfoSourceUuid, DimSite.InfoSourceUuid),
                    InfoSourceKey = COALESCE(excluded.InfoSourceKey, DimSite.InfoSourceKey),
                    LastSeenUtc = excluded.LastSeenUtc
                """,
                rows,
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def save_segment(self, segment: Any) -> None:
        self.save_segments([segment])

    def save_segments(self, segments: Iterable[Any]) -> None:
        prepared = [self._prepare_segment(segment) for segment in segments]
        if not prepared:
            return

        try:
            self._save_info_sources(info_source for item in prepared for info_source in item["info_sources"])
            self._save_segment_types(item["segment_type"] for item in prepared)
            rows = [
                self._segment_row(
                    item["source"],
                    item["info_source"],
                    self._info_source_key(item["info_source"]["uuid"]) if item["info_source"] else None,
                )
                for item in prepared
            ]
            self.connection.executemany(
                """
                INSERT INTO DimSegment (
                    SegmentUuid,
                    SegmentName,
                    SegmentTypeUuid,
                    SegmentTypeKey,
                    SiteUuid,
                    SiteKey,
                    InfoSourceUuid,
                    InfoSourceKey,
                    FirstSeenUtc,
                    LastSeenUtc
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(SegmentUuid) DO UPDATE SET
                    SegmentName = excluded.SegmentName,
                    SegmentTypeUuid = excluded.SegmentTypeUuid,
                    SegmentTypeKey = excluded.SegmentTypeKey,
                    SiteUuid = excluded.SiteUuid,
                    SiteKey = excluded.SiteKey,
                    InfoSourceUuid = COALESCE(excluded.InfoSourceUuid, DimSegment.InfoSourceUuid),
                    InfoSourceKey = COALESCE(excluded.InfoSourceKey, DimSegment.InfoSourceKey),
                    LastSeenUtc = excluded.LastSeenUtc
                """,
                rows,
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def save_measurement_location(self, location: Any) -> None:
        self.save_measurement_locations([location])

    def save_measurement_locations(self, locations: Iterable[Any]) -> None:
        prepared = [self._prepare_measurement_location(location) for location in locations]
        if not prepared:
            return

        try:
            self._save_info_sources(info_source for item in prepared for info_source in item["info_sources"])
            self._save_measurement_location_reference_dimensions(prepared)
            rows = [
                self._measurement_location_row(item["source"], item["location_info_source"])
                for item in prepared
            ]
            self.connection.executemany(
                """
                INSERT INTO DimMeasurementLocation (
                    MeasurementLocationUuid,
                    MeasurementLocationName,
                    MeasurementLocationTypeUuid,
                    MeasurementLocationTypeKey,
                    SegmentUuid,
                    SegmentKey,
                    ValueClass,
                    DefaultUnitUuid,
                    DefaultUnitKey,
                    UomQuantityUuid,
                    UomQuantityKey,
                    InfoSourceUuid,
                    InfoSourceKey,
                    FirstSeenUtc,
                    LastSeenUtc
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(MeasurementLocationUuid) DO UPDATE SET
                    MeasurementLocationName = excluded.MeasurementLocationName,
                    MeasurementLocationTypeUuid = excluded.MeasurementLocationTypeUuid,
                    MeasurementLocationTypeKey = excluded.MeasurementLocationTypeKey,
                    SegmentUuid = excluded.SegmentUuid,
                    SegmentKey = excluded.SegmentKey,
                    ValueClass = excluded.ValueClass,
                    DefaultUnitUuid = excluded.DefaultUnitUuid,
                    DefaultUnitKey = excluded.DefaultUnitKey,
                    UomQuantityUuid = excluded.UomQuantityUuid,
                    UomQuantityKey = excluded.UomQuantityKey,
                    InfoSourceUuid = COALESCE(excluded.InfoSourceUuid, DimMeasurementLocation.InfoSourceUuid),
                    InfoSourceKey = COALESCE(excluded.InfoSourceKey, DimMeasurementLocation.InfoSourceKey),
                    LastSeenUtc = excluded.LastSeenUtc
                """,
                rows,
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def save_measurement(self, measurement: Any) -> None:
        self.save_measurements([measurement])

    def save_measurements(self, measurements: Iterable[Any]) -> None:
        prepared = [
            {
                "source": measurement,
                "info_sources": [
                    info_source
                    for info_source in (
                        self._info_source_from_value(measurement),
                        self._info_source_from_value(measurement, prefix="unit"),
                    )
                    if info_source
                ],
            }
            for measurement in measurements
        ]
        if not prepared:
            return

        try:
            self._save_info_sources(info_source for item in prepared for info_source in item["info_sources"])
            rows = [self._measurement_row(item["source"]) for item in prepared]
            if not rows:
                return
            self.connection.executemany(
                """
                INSERT INTO FactMeasurement (
                    MeasurementUuid,
                    MeasurementLocationKey,
                    MeasurementLocationUuid,
                    UnitKey,
                    UnitUuid,
                    MeasurementTimestampUtc,
                    NumericValue,
                    InfoSourceKey,
                    InfoSourceUuid,
                    InsertedUtc
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(MeasurementLocationUuid, MeasurementTimestampUtc, MeasurementUuid)
                    WHERE MeasurementUuid IS NOT NULL
                DO UPDATE SET
                    MeasurementLocationKey = excluded.MeasurementLocationKey,
                    UnitKey = excluded.UnitKey,
                    UnitUuid = excluded.UnitUuid,
                    NumericValue = excluded.NumericValue,
                    InfoSourceKey = COALESCE(excluded.InfoSourceKey, FactMeasurement.InfoSourceKey),
                    InfoSourceUuid = COALESCE(excluded.InfoSourceUuid, FactMeasurement.InfoSourceUuid),
                    InsertedUtc = excluded.InsertedUtc
                """,
                rows,
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def _prepare_site(self, site: Any) -> dict[str, Any]:
        info_source = self._info_source_from_value(site)
        site_type = self._reference_dimension_from_value(
            site,
            uuid_names=("site_type_uuid", "SiteTypeUuid", "siteTypeUuid", "SiteTypeUUID"),
            short_name_names=("site_type", "SiteType", "SiteTypeName"),
            info_source_prefix="site_type",
        )
        return {
            "source": site,
            "info_source": info_source,
            "site_type": site_type,
            "info_sources": [
                source
                for source in (info_source, site_type.get("info_source") if site_type else None)
                if source
            ],
        }

    def _site_row(
        self,
        site: Any,
        info_source: dict[str, Any] | None,
        info_source_key: int | None,
    ) -> tuple[str, str, str | None, int | None, str | None, int | None, str, str]:
        now = _utc_now()
        site_uuid = _value(site, "site_uuid", "SiteUuid", "SiteUUID", "uuid", "UUID")
        if not site_uuid:
            raise ValueError("Site is missing SiteUuid.")
        site_name = _value(site, "site_name", "SiteName", "name", "Name") or str(site_uuid)
        site_type_uuid = _value(site, "site_type_uuid", "SiteTypeUuid", "siteTypeUuid", "SiteTypeUUID")
        site_type_key = self._dimension_key("DimSiteType", "SiteTypeKey", "SiteTypeUuid", site_type_uuid)
        return (
            str(site_uuid),
            str(site_name),
            str(site_type_uuid) if site_type_uuid else None,
            site_type_key,
            info_source["uuid"] if info_source else None,
            info_source_key,
            now,
            now,
        )

    def _prepare_segment(self, segment: Any) -> dict[str, Any]:
        info_source = self._info_source_from_value(segment)
        segment_type = self._reference_dimension_from_value(
            segment,
            uuid_names=("segment_type_uuid", "SegmentTypeUuid", "segmentTypeUuid", "SegmentTypeUUID"),
            short_name_names=("segment_type", "SegmentType", "SegmentTypeName"),
            info_source_prefix="segment_type",
        )
        return {
            "source": segment,
            "info_source": info_source,
            "segment_type": segment_type,
            "info_sources": [
                source
                for source in (info_source, segment_type.get("info_source") if segment_type else None)
                if source
            ],
        }

    def _segment_row(
        self,
        segment: Any,
        info_source: dict[str, Any] | None,
        info_source_key: int | None,
    ) -> tuple[str, str, str | None, int | None, str, int, str | None, int | None, str, str]:
        now = _utc_now()
        segment_uuid = _value(segment, "segment_uuid", "SegmentUuid", "SegmentUUID", "uuid", "UUID")
        if not segment_uuid:
            raise ValueError("Segment is missing SegmentUuid.")
        segment_name = _value(segment, "segment_name", "SegmentName", "name", "Name") or str(segment_uuid)
        segment_type_uuid = _value(
            segment,
            "segment_type_uuid",
            "SegmentTypeUuid",
            "segmentTypeUuid",
            "SegmentTypeUUID",
        )
        site_uuid = _value(segment, "site_uuid", "SiteUuid", "SiteUUID", "siteUuid")
        if not site_uuid:
            raise ValueError("Segment is missing parent SiteUuid.")
        site_key = self._dimension_key("DimSite", "SiteKey", "SiteUuid", site_uuid)
        if site_key is None:
            raise ValueError(f"Segment parent site {site_uuid} has not been persisted.")
        segment_type_key = self._dimension_key(
            "DimSegmentType",
            "SegmentTypeKey",
            "SegmentTypeUuid",
            segment_type_uuid,
        )
        return (
            str(segment_uuid),
            str(segment_name),
            str(segment_type_uuid) if segment_type_uuid else None,
            segment_type_key,
            str(site_uuid),
            site_key,
            info_source["uuid"] if info_source else None,
            info_source_key,
            now,
            now,
        )

    def _prepare_measurement_location(self, location: Any) -> dict[str, Any]:
        location_info_source = self._info_source_from_value(location)
        location_type = self._reference_dimension_from_value(
            location,
            uuid_names=("type_uuid", "measurement_location_type_uuid", "MeasurementLocationTypeUuid"),
            short_name_names=("location_type", "measurement_location_type", "MeasurementLocationTypeName"),
            info_source_prefix="measurement_location_type",
        )
        unit = self._reference_dimension_from_value(
            location,
            uuid_names=("unit_uuid", "UnitUuid", "UnitUUID", "unitUuid"),
            short_name_names=("unit", "UnitName", "unit_name"),
            info_source_prefix="unit",
        )
        uom_quantity = self._reference_dimension_from_value(
            location,
            uuid_names=("uom_quantity_uuid", "UomQuantityUuid", "UOMQuantityUuid"),
            short_name_names=("uom_quantity", "UomQuantity", "UOMQuantity"),
            info_source_prefix="uom_quantity",
        )
        info_sources = [
            location_info_source,
            location_type.get("info_source") if location_type else None,
            unit.get("info_source") if unit else None,
            uom_quantity.get("info_source") if uom_quantity else None,
        ]
        return {
            "source": location,
            "location_info_source": location_info_source,
            "info_sources": [info_source for info_source in info_sources if info_source],
            "location_type": location_type,
            "unit": unit,
            "uom_quantity": uom_quantity,
        }

    def _measurement_location_row(
        self, location: Any, info_source: dict[str, Any] | None
    ) -> tuple[Any, ...]:
        now = _utc_now()
        location_uuid = _value(
            location,
            "location_uuid",
            "measurement_location_uuid",
            "MeasurementLocationUuid",
            "MeasurementLocationUUID",
            "uuid",
            "UUID",
        )
        if not location_uuid:
            raise ValueError("Measurement location is missing MeasurementLocationUuid.")
        location_name = (
            _value(location, "location_name", "measurement_location_name", "MeasurementLocationName", "name", "Name")
            or str(location_uuid)
        )
        location_type_uuid = _value(
            location,
            "type_uuid",
            "measurement_location_type_uuid",
            "MeasurementLocationTypeUuid",
            "measurementLocationTypeUuid",
        )
        segment_uuid = _value(location, "segment_uuid", "SegmentUuid", "SegmentUUID", "segmentUuid")
        if not segment_uuid:
            raise ValueError("Measurement location is missing parent SegmentUuid.")
        segment_key = self._dimension_key("DimSegment", "SegmentKey", "SegmentUuid", segment_uuid)
        if segment_key is None:
            raise ValueError(f"Measurement location parent segment {segment_uuid} has not been persisted.")
        value_class = _value(location, "value_class", "ValueClass", "valueClass")
        unit_uuid = _value(location, "unit_uuid", "UnitUuid", "UnitUUID", "unitUuid")
        uom_quantity_uuid = _value(location, "uom_quantity_uuid", "UomQuantityUuid", "UOMQuantityUuid")
        location_type_key = self._dimension_key(
            "DimMeasurementLocationType",
            "MeasurementLocationTypeKey",
            "MeasurementLocationTypeUuid",
            location_type_uuid,
        )
        unit_key = self._dimension_key("DimUnit", "UnitKey", "UnitUuid", unit_uuid)
        uom_quantity_key = self._dimension_key(
            "DimUomQuantity",
            "UomQuantityKey",
            "UomQuantityUuid",
            uom_quantity_uuid,
        )
        info_source_key = self._info_source_key(info_source["uuid"]) if info_source else None
        normalized_value_class = str(value_class) if value_class else None
        if normalized_value_class in {"Percentage", "Number"}:
            unit_uuid = None
            unit_key = None
            uom_quantity_uuid = None
            uom_quantity_key = None
        return (
            str(location_uuid),
            str(location_name),
            str(location_type_uuid) if location_type_uuid else None,
            location_type_key,
            str(segment_uuid) if segment_uuid else None,
            segment_key,
            normalized_value_class,
            str(unit_uuid) if unit_uuid else None,
            unit_key,
            str(uom_quantity_uuid) if uom_quantity_uuid else None,
            uom_quantity_key,
            info_source["uuid"] if info_source else None,
            info_source_key,
            now,
            now,
        )

    def _save_info_sources(self, info_sources: Iterable[dict[str, Any] | None]) -> None:
        rows = []
        now = _utc_now()
        seen: set[str] = set()
        for info_source in info_sources:
            if not info_source or not info_source.get("uuid"):
                continue
            if not _has_info_source_metadata(info_source):
                continue
            uuid = str(info_source["uuid"])
            if uuid in seen:
                continue
            seen.add(uuid)
            rows.append(
                (
                    uuid,
                    info_source.get("short_name"),
                    now,
                    now,
                )
            )
        if not rows:
            return
        self.connection.executemany(
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
            rows,
        )

    def _save_measurement_location_reference_dimensions(self, prepared: list[dict[str, Any]]) -> None:
        self._save_measurement_location_types(item["location_type"] for item in prepared)
        self._save_uom_quantities(item["uom_quantity"] for item in prepared)
        self._save_units(item["unit"] for item in prepared)
        self._save_uom_quantities(item["uom_quantity"] for item in prepared)

    def _save_site_types(self, values: Iterable[dict[str, Any] | None]) -> None:
        rows = []
        for value in values:
            if value and value.get("uuid"):
                info_source = value.get("info_source")
                rows.append((
                    value["uuid"],
                    value.get("short_name") or value["uuid"],
                    info_source["uuid"] if info_source else None,
                    self._info_source_key(info_source["uuid"]) if info_source else None,
                ))
        if not rows:
            return
        self.connection.executemany(
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

    def _save_segment_types(self, values: Iterable[dict[str, Any] | None]) -> None:
        rows = []
        for value in values:
            if value and value.get("uuid"):
                info_source = value.get("info_source")
                rows.append((
                    value["uuid"],
                    value.get("short_name") or value["uuid"],
                    info_source["uuid"] if info_source else None,
                    self._info_source_key(info_source["uuid"]) if info_source else None,
                ))
        if not rows:
            return
        self.connection.executemany(
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

    def _save_measurement_location_types(self, values: Iterable[dict[str, Any] | None]) -> None:
        rows = []
        for value in values:
            if value and value.get("uuid"):
                info_source = value.get("info_source")
                rows.append((value["uuid"], value.get("short_name") or value["uuid"], info_source["uuid"] if info_source else None, self._info_source_key(info_source["uuid"]) if info_source else None))
        if not rows:
            return
        self.connection.executemany(
            """
            INSERT INTO DimMeasurementLocationType (
                MeasurementLocationTypeUuid,
                ShortName,
                InfoSourceUuid,
                InfoSourceKey
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(MeasurementLocationTypeUuid) DO UPDATE SET
                ShortName = excluded.ShortName,
                InfoSourceUuid = COALESCE(excluded.InfoSourceUuid, DimMeasurementLocationType.InfoSourceUuid),
                InfoSourceKey = COALESCE(excluded.InfoSourceKey, DimMeasurementLocationType.InfoSourceKey)
            """,
            rows,
        )

    def _save_units(self, values: Iterable[dict[str, Any] | None]) -> None:
        rows = []
        for value in values:
            if value and value.get("uuid"):
                info_source = value.get("info_source")
                rows.append(
                    (
                        value["uuid"],
                        value.get("short_name") or value["uuid"],
                        value.get("uom_quantity_uuid"),
                        self._dimension_key(
                            "DimUomQuantity",
                            "UomQuantityKey",
                            "UomQuantityUuid",
                            value.get("uom_quantity_uuid"),
                        ),
                        value.get("conversion_scale"),
                        value.get("conversion_offset"),
                        info_source["uuid"] if info_source else None,
                        self._info_source_key(info_source["uuid"]) if info_source else None,
                    )
                )
        if not rows:
            return
        self.connection.executemany(
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

    def _save_uom_quantities(self, values: Iterable[dict[str, Any] | None]) -> None:
        rows = []
        for value in values:
            if value and value.get("uuid"):
                info_source = value.get("info_source")
                rows.append(
                    (
                        value["uuid"],
                        value.get("short_name") or value["uuid"],
                        value.get("reference_unit_uuid"),
                        self._dimension_key("DimUnit", "UnitKey", "UnitUuid", value.get("reference_unit_uuid")),
                        info_source["uuid"] if info_source else None,
                        self._info_source_key(info_source["uuid"]) if info_source else None,
                    )
                )
        if not rows:
            return
        self.connection.executemany(
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

    def _info_source_key(self, info_source_uuid: str | None) -> int | None:
        if not info_source_uuid:
            return None
        row = self.connection.execute(
            "SELECT InfoSourceKey FROM DimInfoSource WHERE InfoSourceUuid = ?",
            (str(info_source_uuid),),
        ).fetchone()
        return int(row[0]) if row else None

    def _dimension_key(
        self,
        table_name: str,
        key_column: str,
        uuid_column: str,
        uuid: Any,
    ) -> int | None:
        if not uuid:
            return None
        row = self.connection.execute(
            f"SELECT {key_column} FROM {table_name} WHERE {uuid_column} = ?",
            (str(uuid),),
        ).fetchone()
        return int(row[0]) if row else None

    def _reference_dimension_from_value(
        self,
        source: Any,
        uuid_names: tuple[str, ...],
        short_name_names: tuple[str, ...],
        info_source_prefix: str,
    ) -> dict[str, Any] | None:
        uuid = _value(source, *uuid_names)
        if not uuid:
            return None
        info_source = self._info_source_from_value(source, prefix=info_source_prefix)
        return {
            "uuid": str(uuid),
            "short_name": _value(source, *short_name_names),
            "uom_quantity_uuid": _value(source, "uom_quantity_uuid", "UomQuantityUuid", "UOMQuantityUuid"),
            "reference_unit_uuid": _value(source, "reference_unit_uuid", "ReferenceUnitUuid", "referenceUnitUuid"),
            "conversion_scale": _value(source, "conversion_scale", "ConversionScale", "conversionScale"),
            "conversion_offset": _value(source, "conversion_offset", "ConversionOffset", "conversionOffset"),
            "info_source": info_source,
        }

    def _info_source_from_value(self, source: Any, prefix: str | None = None) -> dict[str, Any] | None:
        uuid_names = ["info_source_uuid", "InfoSourceUuid", "infoSourceUuid"]
        short_name_names = ["info_source_short_name", "InfoSourceShortName", "infoSourceShortName"]
        if prefix:
            uuid_names = [f"{prefix}_info_source_uuid", *uuid_names]
            short_name_names = [f"{prefix}_info_source_short_name", *short_name_names]
        uuid = _value(source, *uuid_names)
        if not uuid:
            return None
        return {
            "uuid": str(uuid),
            "short_name": _value(source, *short_name_names),
        }

    def _measurement_row(
        self, measurement: Any
    ) -> tuple[Any, ...]:
        timestamp = _value(
            measurement,
            "timestamp_utc",
            "measurement_timestamp_utc",
            "MeasurementTimestampUtc",
            "timestamp",
            "Timestamp",
        )
        if not timestamp:
            raise ValueError("Measurement is missing MeasurementTimestampUtc.")
        measurement_uuid = _value(measurement, "measurement_uuid", "MeasurementUuid", "MeasurementUUID", "uuid", "UUID")
        measurement_uuid_text = str(measurement_uuid).strip() if measurement_uuid is not None else ""
        if not measurement_uuid_text:
            raise ValueError("Measurement is missing MeasurementUuid.")
        location_uuid = _value(
            measurement,
            "location_uuid",
            "measurement_location_uuid",
            "MeasurementLocationUuid",
            "MeasurementLocationUUID",
        )
        if not location_uuid:
            raise ValueError("Measurement is missing MeasurementLocationUuid.")

        value_class = str(
            _value(measurement, "measurement_type", "value_class", "ValueClass", "valueClass")
            or "Measure"
        )
        unit_uuid = _value(measurement, "unit_uuid", "UnitUuid", "UnitUUID", "unitUuid")
        unit_name = _value(measurement, "unit", "UnitName", "unit_name")
        if unit_uuid and self._dimension_key("DimUnit", "UnitKey", "UnitUuid", unit_uuid) is None:
            self.connection.execute(
                """
                INSERT OR IGNORE INTO DimUnit(UnitUuid, ShortName)
                VALUES (?, ?)
                """,
                (str(unit_uuid), str(unit_name or unit_uuid)),
            )
        location = self._measurement_location_context(str(location_uuid))
        if not location:
            now = _utc_now()
            segment_uuid = _value(measurement, "segment_uuid", "SegmentUuid", "SegmentUUID", "segmentUuid")
            if not segment_uuid:
                raise ValueError("Measurement location is missing parent SegmentUuid.")
            segment_key = self._dimension_key("DimSegment", "SegmentKey", "SegmentUuid", segment_uuid)
            if segment_key is None:
                raise ValueError(f"Measurement location parent segment {segment_uuid} has not been persisted.")
            self.connection.execute(
                """
                INSERT INTO DimMeasurementLocation (
                    MeasurementLocationUuid,
                    MeasurementLocationName,
                    SegmentUuid,
                    SegmentKey,
                    ValueClass,
                    DefaultUnitUuid,
                    DefaultUnitKey,
                    FirstSeenUtc,
                    LastSeenUtc
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(location_uuid),
                    str(_value(measurement, "measurement_name", "MeasurementName") or location_uuid),
                    str(segment_uuid),
                    segment_key,
                    value_class,
                    str(unit_uuid) if unit_uuid and value_class == "Measure" else None,
                    self._dimension_key("DimUnit", "UnitKey", "UnitUuid", unit_uuid) if value_class == "Measure" else None,
                    now,
                    now,
                ),
            )
            location = self._measurement_location_context(str(location_uuid))
        if not location:
            raise ValueError(f"Measurement location {location_uuid} has not been persisted.")
        value_class = str(value_class or location["ValueClass"] or "Measure")
        if not unit_uuid and value_class == "Measure":
            unit_uuid = location["DefaultUnitUuid"]
        numeric_value = _value(measurement, "numeric_value", "NumericValue", "value", "Value")
        if numeric_value in (None, ""):
            raise ValueError("NumericValue is required for measurement persistence.")
        info_source = self._info_source_from_value(measurement)
        info_source_key = self._info_source_key(info_source["uuid"]) if info_source else None
        location_uuid_text = str(location_uuid)
        unit_uuid_text = str(unit_uuid) if unit_uuid else None
        unit_key = self._dimension_key("DimUnit", "UnitKey", "UnitUuid", unit_uuid_text)
        if value_class == "Measure":
            if unit_key is None:
                raise ValueError("Measure fact requires an explicit unit or measurement-location default unit.")
            location_uom_key = location["UomQuantityKey"]
            unit_uom_key = self._unit_uom_quantity_key(unit_key)
            if location_uom_key and unit_uom_key and int(location_uom_key) != int(unit_uom_key):
                raise ValueError("Measure fact unit does not belong to the measurement-location UOM quantity.")
        elif value_class in {"Percentage", "Number"}:
            if unit_uuid_text:
                raise ValueError(f"{value_class} fact must not carry a unit.")
            unit_key = None
        else:
            unit_key = None
            unit_uuid_text = None
        return (
            measurement_uuid_text,
            int(location["MeasurementLocationKey"]),
            location_uuid_text,
            unit_key,
            unit_uuid_text,
            _format_timestamp_utc(timestamp),
            float(numeric_value),
            info_source_key,
            info_source["uuid"] if info_source else None,
            _utc_now(),
        )

    def _measurement_location_context(self, location_uuid: str) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT
                MeasurementLocationKey,
                MeasurementLocationUuid,
                ValueClass,
                DefaultUnitUuid,
                DefaultUnitKey,
                UomQuantityKey
            FROM DimMeasurementLocation
            WHERE MeasurementLocationUuid = ?
            """,
            (location_uuid,),
        ).fetchone()

    def _unit_uom_quantity_key(self, unit_key: int) -> int | None:
        row = self.connection.execute(
            "SELECT UomQuantityKey FROM DimUnit WHERE UnitKey = ?",
            (unit_key,),
        ).fetchone()
        return int(row[0]) if row and row[0] is not None else None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _format_timestamp_utc(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)
        return value.isoformat(timespec="seconds").replace("+00:00", "Z")
    return str(value)


def _value(source: Any, *names: str) -> Any:
    for name in names:
        if isinstance(source, dict) and name in source:
            value = source[name]
        else:
            value = getattr(source, name, None)
        if value not in (None, ""):
            return value
    return None


def _has_info_source_metadata(info_source: dict[str, Any]) -> bool:
    return info_source.get("short_name") not in (None, "")
