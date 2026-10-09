# Discovery Portal CLI filter manifest

## Scope and authority

This manifest maps the current MCEGold connector CLI short-form request contract to the Discovery Portal. It is documentation only; no portal runtime behavior was changed.

The authoritative implementation is the combination of:

- `ConnectorPostRequestOptions` and `ConnectorRequestFilters` (input model)
- `RequestInputLoader` (JSON rules)
- `ConnectorRequestValidator` (per-request validation)
- `ConnectorRequestMapper` and the existing BOD builders (mapped criteria)
- `RequestTypeNames` and staged request dispatch (CLI exposure)

The CLI implements seven request types. Its actual command form is `request post --type <kebab-name> --input <path>`; the connector operation dispatched underneath is shown separately below.

## Contract-wide rules

- `requestType` is required, uses the PascalCase enum value, and must match the CLI `--type` value.
- `maxItems`, `lastNData`, and all filters are optional. A document containing only the matching `requestType` is valid.
- `maxItems` and `lastNData` deserialize as nullable signed 16-bit integers. Supported uses therefore accept `0..32767`.
- Every exposed UUID is a single value and must parse as a UUID.
- Date/time strings must parse as `DateTimeOffset`. Paired lower bounds must not exceed upper bounds.
- Unknown JSON properties are rejected (`UnmappedMemberHandling.Disallow`). Property matching is case-insensitive, but the examples use camelCase.
- Every short-form filter is single-valued in this version, even when the underlying criteria property is a list.
- The shared DTO exposes more properties than every mapper uses. A property is considered supported here only when it is valid for that request and actually mapped. For example, `lastNData` is not listed for Sites, Segments, Assets, or Measurement Locations because those mappers ignore it.

## Portal workflow summary

| Portal Level | Request Type | CLI Command | Supported CLI Filters | Local-Only UI Filters | Recommended Phase 2 UI Filters | Future Filters |
|---|---|---|---|---|---|---|
| Site | `GetSites` | `request post --type get-sites` → `PostGetSitesRequest` | `siteUuid`; top-level `maxItems` | Site type, status, name search | Exact site UUID, result limit; optionally retain local-only fields as clearly local post-response filters | A true site-type filter requires CLI support; underlying default TypeUUID is not exposed |
| Segment | `GetSegments` | `request post --type get-segments` → `PostGetSegmentsRequest` | `siteUuid`, `segmentUuid`, `typeUuid`; `maxItems` | Segment type *name*, status, name search | Parent site UUID, exact segment UUID, segment type UUID, result limit | Asset context later; `assetUuid` is not a GetSegments short-form filter |
| Measurement Location | `GetMeasurementLocations` | `request post --type get-measurement-locations` → `PostGetMeasurementLocationsRequest` | `siteUuid`, `segmentUuid`, `measurementLocationUuid`, `typeUuid`; `maxItems` | Location type *name*, status, name search | Parent segment UUID, ancestor site UUID, exact location UUID, type UUID, result limit | Asset UUID is not wired by the current mapper |
| Measurements | `GetMeasurements` | `request post --type get-measurements` → `PostGetMeasurementsRequest` | `measurementLocationUuid`, `segmentUuid`, `recordedFrom`, `recordedTo`; `maxItems`, `lastNData` | Stage 1 preview only | Parent location UUID, ancestor segment UUID, recorded range, result limit | Portal Stage 1 shows only Max Items and maps it to both `maxItems` and `lastNData`; no type, unit, status, text, analytics, or independent `lastNData` UI |
| Future Asset | `GetAssets` | `request post --type get-assets` → `PostGetAssetsRequest` | `assetUuid`, `siteUuid`, `typeUuid`, `serialNumber`; `maxItems` | Not in current portal | None in current workflow | Add at Segment level after relationship UX is defined |
| Future Assessments | `GetAssessments` | `request post --type get-assessments` → `PostGetAssessmentsRequest` | Asset/health type UUID, assessed range, health range; limits | Not in current portal | None in current workflow | Assessment exploration |
| Future Asset Events | `GetAssetSegmentEvents` | `request post --type get-asset-segment-events` → `PostGetAssetSegmentEventsRequest` | Event/site/segment/asset IDs, serial, installed state, installed/removed ranges; limits | Not in current portal | None in current workflow | Asset relationship/history exploration |

## Supported request types

### GetSites

```json
{
  "requestType": "GetSites",
  "maxItems": 25,
  "filters": { "siteUuid": "<uuid>" }
}
```

CLI: `request post --type get-sites`; connector operation: `PostGetSitesRequest`; Python sample: `samples/python/06_post_request.py`; payload: `payloads/requests/get-sites.example.json`.

| Field | Type | Required | Cardinality | Validation | Mapped target |
|---|---|---:|---|---|---|
| `requestType` | enum string | Yes | Single | `GetSites`; must match `--type` | Dispatch only |
| `maxItems` | integer | No | Single | `0..32767` | `DataArea.Get.MaxItems` |
| `filters.siteUuid` | UUID | No | Single | Valid UUID | `DataArea.SitesCriteria[0].UUID.UUIDFilter.Value` |

`filters.typeUuid` is explicitly rejected for this request even though the underlying GetSites criteria starts with a default TypeUUID filter. Site type is therefore not a configurable CLI short-form filter.

### GetSegments

```json
{
  "requestType": "GetSegments",
  "maxItems": 25,
  "filters": {
    "siteUuid": "<uuid>",
    "segmentUuid": "<uuid>",
    "typeUuid": "<uuid>"
  }
}
```

CLI: `request post --type get-segments`; connector operation: `PostGetSegmentsRequest`; Python sample: `samples/python/06_post_request.py`; payload: `payloads/requests/get-segments.example.json`.

| Field | Type | Required | Cardinality | Validation | Mapped target |
|---|---|---:|---|---|---|
| `requestType` | enum string | Yes | Single | `GetSegments`; must match `--type` | Dispatch only |
| `maxItems` | integer | No | Single | `0..32767` | `DataArea.Get.MaxItems` |
| `filters.siteUuid` | UUID | No | Single | Valid UUID | `DataArea.SegmentsCriteria[0].SiteUUID[0].Value` |
| `filters.segmentUuid` | UUID | No | Single | Valid UUID | `DataArea.SegmentsCriteria[0].UUID.UUIDFilter.Value` |
| `filters.typeUuid` | UUID | No | Single | Valid UUID | `DataArea.SegmentsCriteria[0].TypeUUID.UUIDFilter.Value` |

The parent site filter maps directly to the portal workflow. The portal may display segment type labels, while the connector filter is specifically a UUID.

### GetAssets

```json
{
  "requestType": "GetAssets",
  "maxItems": 25,
  "filters": {
    "assetUuid": "<uuid>",
    "siteUuid": "<uuid>",
    "typeUuid": "<uuid>",
    "serialNumber": "DEMO-ASSET-001"
  }
}
```

CLI: `request post --type get-assets`; connector operation: `PostGetAssetsRequest`; Python sample: `samples/python/06_post_request.py`; payload: `payloads/requests/get-assets.example.json`.

| Field | Type | Required | Cardinality | Validation | Mapped target |
|---|---|---:|---|---|---|
| `requestType` | enum string | Yes | Single | `GetAssets`; must match `--type` | Dispatch only |
| `maxItems` | integer | No | Single | `0..32767` | `DataArea.Get.MaxItems` |
| `filters.assetUuid` | UUID | No | Single | Valid UUID | `DataArea.AssetsCriteria[0].UUID.UUIDFilter.Value` |
| `filters.siteUuid` | UUID | No | Single | Valid UUID | `DataArea.AssetsCriteria[0].SiteUUID[0].Value` |
| `filters.typeUuid` | UUID | No | Single | Valid UUID | `DataArea.AssetsCriteria[0].TypeUUID.UUIDFilter.Value` |
| `filters.serialNumber` | string | No | Single | Non-blank values are trimmed | `DataArea.AssetsCriteria[0].SerialNumber[0].Value` |

This request is implemented but intentionally outside the current portal workflow.

### GetMeasurementLocations

```json
{
  "requestType": "GetMeasurementLocations",
  "maxItems": 25,
  "filters": {
    "measurementLocationUuid": "<uuid>",
    "siteUuid": "<uuid>",
    "segmentUuid": "<uuid>",
    "typeUuid": "<uuid>"
  }
}
```

CLI: `request post --type get-measurement-locations`; connector operation: `PostGetMeasurementLocationsRequest`; Python sample: `samples/python/06_post_request.py`; payload: `payloads/requests/get-measurement-locations.example.json`.

| Field | Type | Required | Cardinality | Validation | Mapped target |
|---|---|---:|---|---|---|
| `requestType` | enum string | Yes | Single | `GetMeasurementLocations`; must match `--type` | Dispatch only |
| `maxItems` | integer | No | Single | `0..32767` | `DataArea.Get.MaxItems` |
| `filters.measurementLocationUuid` | UUID | No | Single | Valid UUID | `DataArea.MeasurementLocationsCriteria[0].UUID.UUIDFilter.Value` |
| `filters.siteUuid` | UUID | No | Single | Valid UUID | `DataArea.MeasurementLocationsCriteria[0].SiteUUID[0].Value` |
| `filters.segmentUuid` | UUID | No | Single | Valid UUID | `DataArea.MeasurementLocationsCriteria[0].SegmentUUID.UUIDFilter.Value` |
| `filters.typeUuid` | UUID | No | Single | Valid UUID | `DataArea.MeasurementLocationsCriteria[0].TypeUUID.UUIDFilter.Value` |

`assetUuid` is intentionally absent: the current criteria mapper does not wire it through. The portal's parent segment context and exact/type UUID filters are directly supported.

### GetMeasurements

```json
{
  "requestType": "GetMeasurements",
  "maxItems": 100,
  "lastNData": 10,
  "filters": {
    "measurementLocationUuid": "<uuid>",
    "segmentUuid": "<uuid>",
    "recordedFrom": "2026-01-01T00:00:00Z",
    "recordedTo": "2026-01-02T00:00:00Z"
  }
}
```

CLI: `request post --type get-measurements`; connector operation: `PostGetMeasurementsRequest`; Python sample: `samples/python/06_post_request.py`; payload: `payloads/requests/get-measurements.example.json`.

| Field | Type | Required | Cardinality | Validation | Mapped target |
|---|---|---:|---|---|---|
| `requestType` | enum string | Yes | Single | `GetMeasurements`; must match `--type` | Dispatch only |
| `maxItems` | integer | No | Single | `0..32767` | `DataArea.Get.MaxItems` |
| `lastNData` | integer | No | Single | `0..32767` | `ApplicationArea.UserArea.LastNData` |
| `filters.measurementLocationUuid` | UUID | No | Single | Valid UUID | `DataArea.MeasurementsCriteria[0].MeasurementLocationUUID.UUIDFilter.Value` |
| `filters.segmentUuid` | UUID | No | Single | Valid UUID | `DataArea.MeasurementsCriteria[0].SegmentUUID.UUIDFilter.Value` |
| `filters.recordedFrom` | date-time | No | Single | Parseable; not later than `recordedTo` | `DataArea.MeasurementsCriteria[0].Recorded[MinInclusive].Value` |
| `filters.recordedTo` | date-time | No | Single | Parseable; not earlier than `recordedFrom` | `DataArea.MeasurementsCriteria[0].Recorded[MaxInclusive].Value` |

The CLI intentionally does not expose measurement type, unit, measurement UUID, site UUID, asset UUID, text, numeric, or status filters.

### GetAssessments

```json
{
  "requestType": "GetAssessments",
  "maxItems": 50,
  "lastNData": 5,
  "filters": {
    "assetUuid": "<uuid>",
    "healthLevelTypeUuid": "<uuid>",
    "assessedFrom": "2026-01-01T00:00:00Z",
    "assessedTo": "2026-01-31T23:59:59Z",
    "healthLevelMin": 0.0,
    "healthLevelMax": 100.0
  }
}
```

CLI: `request post --type get-assessments`; connector operation: `PostGetAssessmentsRequest`; Python sample: `samples/python/06_post_request.py`; payload: `payloads/requests/get-assessments.example.json`.

| Field | Type | Required | Cardinality | Validation | Mapped target |
|---|---|---:|---|---|---|
| `requestType` | enum string | Yes | Single | `GetAssessments`; must match `--type` | Dispatch only |
| `maxItems` | integer | No | Single | `0..32767` | `DataArea.Get.MaxItems` |
| `lastNData` | integer | No | Single | `0..32767` | `ApplicationArea.UserArea.LastNData` |
| `filters.assetUuid` | UUID | No | Single | Valid UUID | `DataArea.AssessmentsCriteria[0].AssetUUID.UUIDFilter.Value` |
| `filters.healthLevelTypeUuid` | UUID | No | Single | Valid UUID | `DataArea.AssessmentsCriteria[0].HealthLevelTypeUUID.UUIDFilter.Value` |
| `filters.assessedFrom` | date-time | No | Single | Parseable; ≤ `assessedTo`; normalized to UTC | `DataArea.AssessmentsCriteria[0].Assessed[MinInclusive].Value` |
| `filters.assessedTo` | date-time | No | Single | Parseable; ≥ `assessedFrom`; normalized to UTC | `DataArea.AssessmentsCriteria[0].Assessed[MaxInclusive].Value` |
| `filters.healthLevelMin` | number | No | Single | Finite; ≤ `healthLevelMax` | `DataArea.AssessmentsCriteria[0].HealthLevelPrecise[MinInclusive].Value` |
| `filters.healthLevelMax` | number | No | Single | Finite; ≥ `healthLevelMin` | `DataArea.AssessmentsCriteria[0].HealthLevelPrecise[MaxInclusive].Value` |

Site, segment, measurement-location, assessment UUID, status, and severity filters are not exposed.

### GetAssetSegmentEvents

```json
{
  "requestType": "GetAssetSegmentEvents",
  "maxItems": 50,
  "lastNData": 10,
  "filters": {
    "eventUuid": "<uuid>",
    "siteUuid": "<uuid>",
    "segmentUuid": "<uuid>",
    "assetUuid": "<uuid>",
    "serialNumber": "DEMO-ASSET-001",
    "installedNow": true,
    "installedFrom": "2026-01-01T00:00:00Z",
    "installedTo": "2026-01-31T23:59:59Z",
    "removedFrom": "2026-02-01T00:00:00Z",
    "removedTo": "2026-02-28T23:59:59Z"
  }
}
```

CLI: `request post --type get-asset-segment-events`; connector operation: `PostGetAssetSegmentEventsRequest`; Python sample: `samples/python/06_post_request.py`; payload: `payloads/requests/get-asset-segment-events.example.json`.

| Field | Type | Required | Cardinality | Validation | Mapped target |
|---|---|---:|---|---|---|
| `requestType` | enum string | Yes | Single | `GetAssetSegmentEvents`; must match `--type` | Dispatch only |
| `maxItems` | integer | No | Single | `0..32767` | `DataArea.Get.MaxItems` |
| `lastNData` | integer | No | Single | `0..32767` | `ApplicationArea.UserArea.LastNData` |
| `filters.eventUuid` | UUID | No | Single | Valid UUID | `DataArea.AssetSegmentEventsCriteria[0].UUID.UUIDFilter.Value` |
| `filters.siteUuid` | UUID | No | Single | Valid UUID | `DataArea.AssetSegmentEventsCriteria[0].SiteUUID[0].Value` |
| `filters.segmentUuid` | UUID | No | Single | Valid UUID | `DataArea.AssetSegmentEventsCriteria[0].SegmentUUID.UUIDFilter.Value` |
| `filters.assetUuid` | UUID | No | Single | Valid UUID | `DataArea.AssetSegmentEventsCriteria[0].AssetUUID.UUIDFilter.Value` |
| `filters.serialNumber` | string | No | Single | Non-blank values are trimmed | `DataArea.AssetSegmentEventsCriteria[0].AssetSerialNumber[0].Value` |
| `filters.installedNow` | boolean | No | Single | `true`, `false`, or omitted/null | `DataArea.AssetSegmentEventsCriteria[0].InstalledNow[0].Value` |
| `filters.installedFrom` | date-time | No | Single | Parseable; ≤ `installedTo`; normalized to UTC | `DataArea.AssetSegmentEventsCriteria[0].Installed[MinInclusive].Value` |
| `filters.installedTo` | date-time | No | Single | Parseable; ≥ `installedFrom`; normalized to UTC | `DataArea.AssetSegmentEventsCriteria[0].Installed[MaxInclusive].Value` |
| `filters.removedFrom` | date-time | No | Single | Parseable; ≤ `removedTo`; normalized to UTC | `DataArea.AssetSegmentEventsCriteria[0].Removed[MinInclusive].Value` |
| `filters.removedTo` | date-time | No | Single | Parseable; ≥ `removedFrom`; normalized to UTC | `DataArea.AssetSegmentEventsCriteria[0].Removed[MaxInclusive].Value` |

Event type, status, severity, type UUID, measurement-location UUID, and numeric health/measurement filters are not exposed.

## Python sample coverage

`samples/python/06_post_request.py` is a generic post sample for all seven request types. It passes `--type` and the selected payload file to the CLI; it does not construct or constrain type-specific filter fields itself. All seven checked-in example payloads exercise their documented fields, and `RequestPayloadTests.ExamplePayloadsExactlyMatchSupportedRequestTypesAndValidate` verifies that those payloads match the exposed type set, deserialize, validate, and generate preview JSON.

No checked-in Python payload example contains a field rejected by the current CLI. Conversely, the Python script does not expose individual flags for any supported filter—the JSON payload is the sole type-specific input.

## Local-only portal filters

The current portal may use friendly display names and post-response matching for usability. The following are **not** current CLI short-form filters and must carry `portalLocalOnly: true` (as they do in the JSON manifest):

- Site: site type name, status, name search
- Segment: segment type name, status, name search
- Measurement Location: location type name, status, name search
- Measurements: measurement type, unit, status, name search

Type-name filters can be replaced by `typeUuid` selectors once type UUID metadata is available. Name searches and unit filters may remain useful as explicitly local post-response filters. Status filters should be removed before real connector integration or retained only when the response contract provides a dependable status field and the UI clearly indicates local filtering.

## Phase 2 recommendation

Use the selected parent UUID as the connector filter at every step, add conservative `maxItems` limits, and expose exact/type UUID filters only where users have meaningful lookup labels. For measurements, Stage 1 uses a bounded preview with Max Items and optional recorded UTC range controls only; the selected Max Items value is sent as both `maxItems` and `lastNData` because the request is scoped to one Measurement Location. Type, unit, status, text search, analytics, charting, independent Last N Data controls, and Grafana remain out of scope for this portal screen.

## Files inspected

- Connector request DTO, filter DTO, mapper, validator, JSON builder, command runner, and request criteria/BOD builder paths
- CLI request input loader, request-type names, application/workflow dispatch, and staged commands
- External Toolkit docs: `MCEGold.Data.Services.Connector.Toolkit/docs/request-types.md`, `MCEGold.Data.Services.Connector.Toolkit/docs/cli-reference.md`, `MCEGold.Data.Services.Connector.Toolkit/docs/json-contract.md`, and `MCEGold.Data.Services.Connector.Toolkit/docs/mcegold-python-samples-design.md`
- All seven `payloads/requests/*.example.json` files
- Python `06_post_request.py`, `cli_helpers.py`, and Python sample README
- CLI `RequestPayloadTests`, `PythonSampleContractTests`, `CliApplicationTests`, `CliSmokeTests`, and staged command tests

The machine-readable counterpart is [`discovery-filter-manifest.json`](../../docs/discovery-filter-manifest.json).
