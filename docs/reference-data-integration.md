# CCOM Reference Data integration

The Discovery Portal uses the canonical CCOM Reference Data XML file to initialize SQLite reference dimensions. After a database has been seeded, type-filter dropdowns below the Sites step query SQLite instead of parsing the XML file.

## Canonical XML location

Default file:

```text
docs/CCOM Reference Data.xml
```

The file path can be overridden with environment variables:

- `REFERENCE_DATA_PATH`
- `REFERENCE_DATA_LOAD_MODE` is retained for compatibility but normal startup seeding now uses the database seed marker, not a runtime load mode.

`REFERENCE_DATA_SHEET` is retained for compatibility with existing configuration but is ignored by the XML loader.

## XML fields used

The loader reads each CCOM `Entity` node and groups records by `xsi:type`. It normalizes these XML fields into `ReferenceDataEntry` fields:

- `xsi:type` -> `class_name`
- `UUID` -> `uuid`
- `ShortName` -> `short_name`
- `FullName` -> `full_name`
- `Description` -> `description`
- `Type.UUID` or `Type` -> `type`
- `UOMQuantity.UUID` or `UOMQuantity` -> `uom_quantity`
- `ReferenceUnitOfMeasure.UUID` or `ReferenceUnitOfMeasure` -> `reference_unit_of_measure`
- `Created` -> `created`
- `LastEdited` -> `last_edited`
- `InfoSource.UUID` -> `info_source_uuid`
- `EffectiveStatusType.UUID` -> `effective_status_type_uuid`

Display names prefer `ShortName`, then `FullName`, then `UUID`.

## Dropdowns populated from SQLite

The current portal exposes these seeded reference classes in the guided workflow:

- Segments page: `DimSegmentType`
- Measurement Locations page: `DimMeasurementLocationType`
- Measurements page: no reference-data filters in Stage 1 preview; Unit is displayed from the selected Measurement Location context.

The Sites page does not use reference-data filters in this phase.

The XML file also includes `SiteType`, `UnitOfMeasure`, and `UOMQuantity`. These are seeded into SQLite for reporting and future workflow use.

## Startup behavior

At application startup, the portal initializes the SQLite schema and checks `ReferenceDataImport`.

If a successful import marker exists for the supported import version and the required reference dimensions contain rows, startup does not open, hash, or parse the XML file.

If the database is new or unseeded, the configured XML file is required. The import runs transactionally, populates supported reference dimensions, and inserts the successful `ReferenceDataImport` marker only after all required reference dimensions have rows.

If the XML file is missing or invalid for an unseeded database, startup fails clearly and rolls back the import. No fallback or sample reference rows are created.

## Filtering behavior

Dropdown option values use reference-data UUIDs read from SQLite. Discovery responses may provide UUIDs or display labels depending on the connector payload shape, so filter matching accepts:

- selected UUID
- selected display name
- selected short name
- selected full name
- direct text match

This keeps filtering tolerant while the portal normalizes real MCEGold discovery payloads.

## SQLite reference seeding

The XML file is the canonical initialization source for reference dimensions seeded into the local SQLite schema. Seeded dimensions include:

- `DimSiteType`
- `DimSegmentType`
- `DimMeasurementLocationType`
- `DimUnit`
- `DimUomQuantity`
- `DimInfoSource`

Rows are upserted by UUID during initialization. Seeding is once per database for the supported import version; this task does not add automatic hash- or timestamp-based refresh. Deleting the database causes the next startup to recreate it and seed reference data again. No synthetic Sites, Segments, Measurement Locations, or Measurement facts are inserted automatically.
