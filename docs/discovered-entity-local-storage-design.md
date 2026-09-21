# Discovered Entity Local Storage Design

This document describes the local SQLite storage model for the Discovery Portal. The current public-release schema version is 17. The Portal creates the current schema directly for fresh databases and rejects older pre-release schema versions below 17 rather than applying a public migration chain. Earlier internal schema iterations shaped the current model, but `app/storage/database.py` is the authoritative source for the current schema.

## Modeling Correction

Site, Segment, and MeasurementLocation are discovered catalog entities. They describe the CCOM discovery hierarchy and are suitable for dimensional tables.

Measurement is different. A Measurement is primarily an observed numeric value over time associated with a MeasurementLocation. It should be modeled as time-series fact data, not as a catalog entity, unless later CCOM metadata requires a separate measurement catalog.

The target analytic hierarchy is:

```text
DimSite
  -> DimSegment
    -> DimMeasurementLocation
      -> FactMeasurement
```

In practical terms:

- MeasurementLocation is the discovered point, sensor, or location where values are observed.
- Measurement is the observed value at a timestamp.
- Measurement facts should reference discovered locations and seeded reference dimensions by key or UUID.
- Names and type labels should be resolved through dimensions where possible instead of duplicated in every fact row.

## Design Goals

The local storage model should be friendly to both Power BI and Grafana:

- Preserve the natural discovery hierarchy from Site to Segment to MeasurementLocation.
- Store high-volume measurement observations in a narrow fact table.
- Seed stable CCOM reference data into dimensions.
- Keep raw request/response payloads available for traceability without forcing reports to parse JSON.
- Prefer stable UUID-based joins to repeated display strings.
- Support simple flattened views for reporting tools.

## Reference Dimensions

The following dimensions are seeded automatically from `docs/CCOM Reference Data.xml` during portal startup. The current demo schema stores only the fields needed by the portal workflow. It does not store CCOM `FullName` values.

`InfoSourceUuid` is stored as a provenance reference. Not every `InfoSourceUuid` resolves to `DimInfoSource`; the XML can reference other entity types, such as `Document`, through an `InfoSource` field. `DimInfoSource` stores only top-level XML entities whose `xsi:type` is `InfoSource`.

Runtime discovery follows the same rule. A discovered `infoSource.UUID` is retained on the discovered/reference row, and `DimInfoSource` is upserted only when the response also includes a usable short name such as `infoSource.shortNames[0].text`.

### DimSiteType

Seeded from CCOM `SiteType`.

Implemented demo columns:

- `SiteTypeKey`
- `SiteTypeUuid`
- `ShortName`
- `IsMobile`
- `InfoSourceUuid`
- `InfoSourceKey`

### DimSegmentType

Seeded from CCOM `SegmentType`.

Implemented demo columns:

- `SegmentTypeKey`
- `SegmentTypeUuid`
- `ShortName`
- `InfoSourceUuid`
- `InfoSourceKey`

The demo stores only `ShortName` for SegmentType. It does not persist derived hierarchy levels from comma-separated names.

### DimMeasurementLocationType

Seeded from CCOM `MeasurementLocationType`.

Implemented demo columns:

- `MeasurementLocationTypeKey`
- `MeasurementLocationTypeUuid`
- `ShortName`
- `UomQuantityUuid`
- `InfoSourceUuid`
- `InfoSourceKey`

`UOMQuantity` is an explicit relationship in the XML for many MeasurementLocationType records and should be modeled as a foreign key when available.

### DimUnit

Seeded from CCOM `UnitOfMeasure`.

Implemented demo columns:

- `UnitKey`
- `UnitUuid`
- `ShortName`
- `UomQuantityUuid`
- `UomQuantityKey`
- `ConversionScale`
- `ConversionOffset`
- `InfoSourceUuid`
- `InfoSourceKey`

`ConversionScale` and `ConversionOffset` are stored from the XML when present. They remain metadata only; this phase does not add unit-conversion calculations.

### DimUomQuantity

Seeded from CCOM `UOMQuantity`.

Implemented demo columns:

- `UomQuantityKey`
- `UomQuantityUuid`
- `ShortName`
- `ReferenceUnitUuid`
- `ReferenceUnitKey`
- `InfoSourceUuid`
- `InfoSourceKey`

`ReferenceUnitOfMeasure` is an explicit relationship in the XML and can be resolved to `DimUnit` after units are loaded.

## Discovery and Runtime Tables

### DiscoveryPayload

Raw request/response traceability table. It is independent of discovery-run metadata in the simplified demo schema.

Implemented demo columns:

- `SourcePayloadKey`
- `EntityKind`
- `EntityUuid`
- `RequestType`
- `PayloadJson`
- `ReceivedUtc`

`EntityKind` examples: `Site`, `Segment`, `MeasurementLocation`, `Measurement`.

The active demo store does not populate `DiscoveryPayload`, and the discovered entity tables do not include `SourcePayloadKey` links.

### DimSite

Discovered from GetSites/showSites.

Implemented demo columns:

- `SiteKey`
- `SiteUuid`
- `SiteName`
- `SiteTypeKey`
- `SiteTypeUuid`
- `InfoSourceUuid`
- `InfoSourceKey`
- `FirstSeenUtc`
- `LastSeenUtc`

### DimSegment

Discovered from GetSegments/showSegments.

Implemented demo columns:

- `SegmentKey`
- `SegmentUuid`
- `SiteKey`
- `SiteUuid`
- `SegmentName`
- `SegmentTypeKey`
- `SegmentTypeUuid`
- `InfoSourceUuid`
- `InfoSourceKey`
- `FirstSeenUtc`
- `LastSeenUtc`

### DimMeasurementLocation

Discovered from GetMeasurementLocations/showMeasurementLocations.

Implemented demo columns:

- `MeasurementLocationKey`
- `MeasurementLocationUuid`
- `SegmentKey`
- `SegmentUuid`
- `MeasurementLocationName`
- `MeasurementLocationTypeKey`
- `MeasurementLocationTypeUuid`
- `DefaultUnitKey`
- `DefaultUnitUuid`
- `UomQuantityKey`
- `UomQuantityUuid`
- `ValueClass`
- `InfoSourceUuid`
- `InfoSourceKey`
- `FirstSeenUtc`
- `LastSeenUtc`

MeasurementLocation is the catalog object that represents the point, sensor, or logical location where measurements are observed.

### FactMeasurement

Observed numeric time-series data from GetMeasurements/showMeasurements.

Implemented demo columns:

- `MeasurementFactKey`
- `MeasurementLocationKey`
- `MeasurementLocationUuid`
- `UnitKey`
- `UnitUuid`
- `MeasurementTimestampUtc`
- `NumericValue`
- `InfoSourceKey`
- `InfoSourceUuid`
- `InsertedUtc`

The demo model keeps CCOM UUIDs for traceability and uses local integer keys as authoritative joins. `MeasurementLocationKey` relates the fact to `DimMeasurementLocation`. `UnitKey` and `UnitUuid` identify the unit in which the fact was stored when `ValueClass = Measure`. If a Measure fact does not carry an explicit unit, the importer inherits `DimMeasurementLocation.DefaultUnitKey` and `DefaultUnitUuid`. `Percentage` and `Number` facts are always unitless.

`FactMeasurement` is numeric-only for the current demo. `TextValue` is no longer part of the active schema.

`DimMeasurementLocation.ValueClass` owns the value-class semantics:

- `Measure` requires a default unit and UOM quantity when known from discovery.
- `Percentage` has no unit or UOM quantity, and the numeric value is stored exactly as received. For this demo, percentages are expected as percentage points.
- `Number` has no unit or UOM quantity.

`DimUomQuantity.ReferenceUnitKey` is the reference/base unit pivot. `DimUnit.ConversionScale` and `DimUnit.ConversionOffset` are persisted as metadata only. SQLite, the portal, and the database views do not calculate converted display values or reference values; Power BI and Grafana perform any conversion/reporting calculations.

Measurement facts are idempotent by:

```text
MeasurementLocationUuid + MeasurementTimestampUtc
```

Re-importing the same location and timestamp updates the existing row. `DiscoveryRunId` represents the local discovery execution when available. `SourceRequestId` is intentionally omitted from the educational demo.

## Snowflake Relationships

Recommended relationships:

```text
DimSiteType
  -> DimSite
    -> DimSegment
      -> DimMeasurementLocation
        -> FactMeasurement

DimSegmentType
  -> DimSegment

DimMeasurementLocationType
  -> DimMeasurementLocation

DimUomQuantity
  -> DimMeasurementLocationType
  -> DimMeasurementLocation
  -> DimUnit

DimUnit
  -> FactMeasurement
```

This produces a readable snowflake model while keeping the high-volume measurement data in one fact table.

## Proposed Views

### vw_grafana_measurements

Grafana should get a narrow, time-series-friendly view.

Required columns:

- `time`
- `site_name`
- `segment_name`
- `measurement_location_name`
- `measurement_location_type`
- `unit_name`
- `value`

Suggested SQL shape:

```sql
CREATE VIEW vw_grafana_measurements AS
SELECT
    fm.MeasurementTimestampUtc AS time,
    site.SiteName AS site_name,
    segment.SegmentName AS segment_name,
    location.MeasurementLocationName AS measurement_location_name,
    location_type.ShortName AS measurement_location_type,
    unit.ShortName AS unit_name,
    fm.NumericValue AS value
FROM FactMeasurement fm
JOIN DimMeasurementLocation location
    ON location.MeasurementLocationUuid = fm.MeasurementLocationUuid
JOIN DimSegment segment
    ON segment.SegmentKey = location.SegmentKey
JOIN DimSite site
    ON site.SiteKey = segment.SiteKey
LEFT JOIN DimMeasurementLocationType location_type
    ON location_type.MeasurementLocationTypeKey = location.MeasurementLocationTypeKey
LEFT JOIN DimUnit unit
    ON unit.UnitUuid = fm.UnitUuid;
```

### vw_powerbi_measurement_catalog

Power BI catalog view for discovered sites, segments, and measurement locations.

Suggested columns:

- `SiteUuid`
- `SiteName`
- `SiteType`
- `SegmentUuid`
- `SegmentName`
- `SegmentType`
- `MeasurementLocationUuid`
- `MeasurementLocationName`
- `MeasurementLocationType`
- `DefaultUnitName`
- `UomQuantityName`
- `ValueClass`
- `IsActive`

### vw_powerbi_measurement_timeseries

Power BI fact view for observed measurement values.

Suggested columns:

- `MeasurementTimestampUtc`
- `SiteName`
- `SegmentName`
- `MeasurementLocationName`
- `MeasurementLocationType`
- `UnitName`
- `UomQuantityName`
- `NumericValue`
- `InfoSourceName`

Power BI can import the flattened view for simple reports, or advanced models can import the underlying dimensions and fact table directly.

## XML Seeding Strategy

Implemented Phase 3 strategy:

1. Create schema tables in migrations.
2. Load CCOM reference dimensions from `docs/CCOM Reference Data.xml` during startup.
3. Track XML source metadata in `ReferenceDataImport`.
4. Store file path, SHA-256 file hash, import timestamp, entity count, and import version.
5. Upsert dimension rows by UUID.
6. Never delete discovered dimensions or measurement facts during reference-data reload.

Reference data should be reloadable when the XML changes. Structural migrations should not hard-code all reference records.

The canonical seeded reference dimensions are:

- `DimSiteType`
- `DimSegmentType`
- `DimMeasurementLocationType`
- `DimUnit`
- `DimUomQuantity`
- `DimInfoSource`

`DimInfoSource` is populated only from parsed XML entities where `xsi:type="InfoSource"`. Referenced UUID-only provenance values are retained on their source dimensions as `InfoSourceUuid`, but the seeder does not create placeholder `DimInfoSource` rows for them.

CLI discovery requests use the `Full` payload profile because InfoSource display names are only available when the backend returns the fuller runtime payload shape. The beginner Portal UI does not need to display InfoSource values by default; the metadata is captured for traceability and downstream reporting.

Reference dimensions describe stable CCOM master/reference values. Discovered data tables describe customer-specific runtime entities returned by connector discovery requests:

- `DimSite`
- `DimSegment`
- `DimMeasurementLocation`
- `FactMeasurement`

Normal portal startup initializes the database schema and imports authoritative CCOM reference dimensions only when the database is new or otherwise unseeded. It does not insert demo Sites, Segments, Measurement Locations, or Measurement facts. Business data comes from discovery responses and explicit measurement import flows.

Startup reference-data seeding uses `ReferenceDataImport` as the authoritative marker. When a successful marker exists for the supported import version and required reference tables contain rows, startup skips opening, hashing, and parsing `docs/CCOM Reference Data.xml`. When the database is unseeded, the configured XML file is required and imported transactionally; missing or invalid XML fails initialization without writing a successful marker or partial reference rows.

The XML file is canonical for database initialization. Spreadsheet exports are human-readable reference material only and are not used by the Portal seeder. Deleting the SQLite database recreates the schema and reseeds reference data on the next startup.

Segment Type and Measurement Location Type comboboxes query SQLite reference dimensions after startup:

- `DimSegmentType`
- `DimMeasurementLocationType`

They do not parse the XML file during normal requests.

## Phase 2 Step 1 Persistence

The first persistence step introduces a small `DiscoveredEntityStore` for discovered entity writes. This is not a general repository layer; it only encapsulates SQLite persistence for discovered entities as each workflow slice is implemented.

Current Phase 2 Step 1 flow:

```text
Route
  -> CLI Discovery Client
  -> DiscoveredEntityStore
  -> SQLite
```

Implemented in this step:

- `save_site(site)`
- `save_sites(sites)`
- `DimSite` upsert by `SiteUuid`
- persistence failures are logged and do not block page rendering

Future Phase 2 steps will extend the store for:

- Segments
- Measurement Locations
- Measurements

Background synchronization and cache invalidation remain deferred. Startup XML seeding is implemented in Phase 3.

## Phase 2 Step 2 Segment Persistence

GetSegments persistence extends `DiscoveredEntityStore` without adding a broader repository abstraction.

Current Phase 2 Step 2 flow:

```text
GetSegments
  -> Normalize
  -> save_segments()
  -> Render page
```

Implemented in this step:

- `save_segment(segment)`
- `save_segments(segments)`
- `DimSegment` upsert by `SegmentUuid`
- requires a persisted parent `DimSite`
- stores normalized `SiteUuid` and resolved `SiteKey`
- persistence failures are logged and do not block page rendering

Future Phase 2 steps will add Measurement Location and Measurement persistence.

## Phase 2 Step 3 Measurement Location Persistence

GetMeasurementLocations persistence continues the same direct store pattern.

Current Phase 2 Step 3 flow:

```text
GetMeasurementLocations
  -> Normalize
  -> save_measurement_locations()
  -> Render page
```

Implemented in this step:

- `save_measurement_location(location)`
- `save_measurement_locations(locations)`
- `DimMeasurementLocation` upsert by `MeasurementLocationUuid`
- requires a persisted parent `DimSegment`
- stores normalized `SegmentUuid`, resolved `SegmentKey`, type UUID, and unit/UOM metadata when available
- does not store direct `SiteUuid` or `SiteKey`; site is reached through `DimSegment`
- persistence failures are logged and do not block page rendering

## Phase 2 Step 4 Measurement Fact Persistence

GetMeasurements persistence stores observed values in `FactMeasurement`. Measurement remains time-series fact data associated with a `DimMeasurementLocation`; no `DimMeasurement` catalog table is introduced.

Current Phase 2 Step 4 flow:

```text
GetMeasurements
  -> Normalize
  -> save_measurements()
  -> FactMeasurement
  -> Grafana/Power BI views
```

Implemented in this step:

- `save_measurement(measurement)`
- `save_measurements(measurements)`
- inserts `MeasurementTimestampUtc`, `MeasurementLocationUuid`, unit UUID, numeric value, info source, and insert timestamp when available
- treats `MeasurementLocationUuid + MeasurementTimestampUtc` as the unique demo fact identity
- re-importing the same location and timestamp updates the existing fact row, even when the value changes
- keeps CCOM UUIDs in the fact while using local dimension keys for joins
- stores no raw JSON in `FactMeasurement`
- persistence failures are logged and do not block page rendering

Schema version 3 defines a unique index on `FactMeasurement(MeasurementLocationUuid, MeasurementTimestampUtc)`. During migration, any pre-existing duplicate facts for the same location and timestamp are consolidated by keeping the latest fact row. `save_measurements()` uses that index with `ON CONFLICT DO UPDATE` to keep repeated imports idempotent for the demo model.

Schema version 4 removes `SourcePayloadKey` from `DimSite`, `DimSegment`, `DimMeasurementLocation`, and `FactMeasurement`. Raw payload linking is deferred until a future audit-focused phase.

Schema version 5 simplified `FactMeasurement` for the initial demo by removing local join keys and retaining UUID traceability.

Schema version 8 removes placeholder `DimInfoSource` rows that were created from UUID-only references. It preserves the raw `InfoSourceUuid` provenance values on reference and discovered dimensions while clearing unresolved local `InfoSourceKey` links.

Schema version 9 restores explicit measurement semantics: `DimMeasurementLocation` stores `ValueClass`, `DefaultUnitUuid`/`DefaultUnitKey`, and `UomQuantityUuid`/`UomQuantityKey`; `FactMeasurement` uses `MeasurementFactKey`, `MeasurementLocationKey`, `UnitKey`, and `InfoSourceKey`; `TextValue` is removed from active fact storage.

Schema version 10 removes demo-unused metadata from dimension tables while preserving business rows and reporting views. `LastViewedUtc` and dimension-level `DiscoveryRunKey` are removed from `DimSite`, `DimSegment`, and `DimMeasurementLocation`; `DiscoveryRunKey` is also removed from `DimInfoSource`. Reference dimensions no longer store `CreatedUtc` or `LastEditedUtc`.

Schema version 11 removes redundant `SiteUuid` and `SiteKey` columns from `DimMeasurementLocation`. `DimSegment.SiteKey` is backfilled from `DimSegment.SiteUuid`, `DimMeasurementLocation.SegmentKey` is backfilled from `DimMeasurementLocation.SegmentUuid`, and reporting views join site data through `DimMeasurementLocation -> DimSegment -> DimSite`.

Earlier pre-release schema work removed demo-unused `EffectiveStatusTypeUuid`, `DiscoveryRun`, `DiscoveryRunKey`, and extracted type hierarchy columns. `DiscoveryPayload` remains available for raw JSON payload audit rows without a run foreign key. `DimMeasurementLocationType.UomQuantityUuid` is retained because the canonical XML maps many measurement location types to a UOM quantity and the demo uses that metadata for unit/default-unit relationships.

Schema version 14 removes the unused `QualityCode` column from `FactMeasurement`. Quality values may appear in future CCOM payloads, but the current demo does not import, display, query, or expose them in Power BI or Grafana views.

## Values Seeded From XML

Seed from XML:

- Site types
- Segment types
- Measurement location types
- Units
- UOM quantities
- Optional health, severity, priority, region, attribute, asset, and event dimensions

Keep dynamic/discovered:

- Sites
- Segments
- Measurement locations
- Discovery runs
- Raw payloads
- Measurement observations
- Runtime source request IDs
- Runtime data quality indicators

## Risks and Limitations

- The XML does not include explicit parent/category/domain elements for SegmentType or MeasurementLocationType.
- Comma-derived hierarchy levels are useful but not authoritative.
- The XML appears single-language; no localization attributes were found.
- The XML has entity-level timestamps but no clear root version number.
- Some references point to IDs not represented as full entities in this file, such as enumeration items and included statuses.
- Reference dimensions should be designed to tolerate missing joins and unknown UUIDs from live connector data.

## Recommendation

The XML is part of the local storage architecture as a seeded reference-data source. It is well suited for dimension tables because UUIDs are stable identifiers and the values represent CCOM master/reference data.

The immediate storage model should prioritize:

- `DimSite`
- `DimSegment`
- `DimMeasurementLocation`
- `FactMeasurement`
- seeded dimensions for site type, segment type, measurement location type, unit, and UOM quantity

Measurement should remain a time-series fact, not a discovered entity catalog table.

