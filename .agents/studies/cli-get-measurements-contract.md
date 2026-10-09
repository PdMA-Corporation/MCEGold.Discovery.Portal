# CLI GetMeasurements short-form contract

This document records the actual implemented `GetMeasurements` short-form CLI contract before the Discovery Portal wires the Measurements screen to CLI data.

No portal runtime behavior depends on this document.

## Sources inspected

The Toolkit references below are external repository dependencies from `MCEGold.Data.Services.Connector.Toolkit`.

- `MCEGold.Data.Services.Connector.Toolkit/samples/csharp/MCEGold.Data.Services.Connector.Cli/Input/RequestTypeNames.cs`
- `MCEGold.Data.Services.Connector.Toolkit/samples/csharp/MCEGold.Data.Services.Connector.Cli/Input/RequestInputLoader.cs`
- `MCEGold.Data.Services.Connector.Toolkit/samples/csharp/MCEGold.Data.Services.Connector.Cli/Commands/StagedSessionCommands.cs`
- `MCEGold.Data.Services.Connector.Toolkit/samples/csharp/MCEGold.Data.Services.Connector.Cli/Commands/RequestWorkflow.cs`
- `MCEGold.Data.Services.Connector/src/MCEGold.Data.Services.Connector/Commands/Requests/ConnectorPostRequestOptions.cs`
- `MCEGold.Data.Services.Connector/src/MCEGold.Data.Services.Connector/Commands/Requests/ConnectorRequestFilters.cs`
- `MCEGold.Data.Services.Connector/src/MCEGold.Data.Services.Connector/Commands/Requests/ConnectorRequestMapper.cs`
- `MCEGold.Data.Services.Connector/src/MCEGold.Data.Services.Connector/Commands/Requests/ConnectorRequestValidator.cs`
- `MCEGold.Data.Services.Connector/src/MCEGold.Data.Services.Connector/BODBuilders/GetMeasurementsBODBuilder.cs`
- `MCEGold.Data.Services.Connector/src/MCEGold.Data.Services.Connector/BODBuilders/BuildBODRequest.cs`
- `MCEGold.Data.Services.Connector.Toolkit/docs/cli-reference.md`
- `MCEGold.Data.Services.Connector.Toolkit/docs/calling-mcegold-cli.md`
- `MCEGold.Data.Services.Connector.Toolkit/docs/request-types.md`
- `MCEGold.Data.Services.Connector.Toolkit/payloads/requests/get-measurements.example.json`
- `MCEGold.Data.Services.Connector.Toolkit/samples/python/06_post_request.py`
- `MCEGold.Data.Services.Connector.Toolkit/samples/python/07_read_response.py`
- `MCEGold.Data.Services.Connector.Toolkit/samples/python/README.md`
- `MCEGold.Data.Services.Connector.Toolkit/tests/MCEGold.Data.Services.Connector.Cli.Tests/RequestPayloadTests.cs`
- `MCEGold.Data.Services.Connector.Toolkit/tests/MCEGold.Data.Services.Connector.Cli.Tests/StagedSessionCommandsTests.cs`
- `MCEGoldDataService/MCEGoldDataService/BODDefinitions/ShowMeasurementsDefinition.cs`
- `MCEGoldDataService/MCEGoldDataService/BODDefinitions/CCOMElements.cs`
- `MCEGoldDataService/MCEGoldDataService/Processes/CreateResponseBODs.cs`
- Existing portal discovery manifest notes in `MCEGold.Discovery.Portal/.agents/implementation/discovery-filter-manifest.md`

## CLI command

Implemented request type name:

```text
get-measurements
```

Staged request-session flow:

```text
request post --type get-measurements --input <payload.json> --output json
request read-response --request-id <requestMessageId> --output json
```

The CLI maps `get-measurements` to connector operation:

```text
PostGetMeasurementsRequest
```

The Python sample posts it with:

```powershell
python .\samples\python\06_post_request.py --type get-measurements --input .\payloads\requests\get-measurements.example.json
```

## Exact short-form JSON field names

Canonical implemented field names are:

| Meaning | Implemented JSON field |
|---|---|
| Request type discriminator | `requestType` |
| Max items limit | `maxItems` |
| Last N data limit | `lastNData` |
| Filters object | `filters` |
| Measurement location UUID filter | `filters.measurementLocationUuid` |
| Segment UUID filter | `filters.segmentUuid` |
| Recorded lower-bound filter | `filters.recordedFrom` |
| Recorded upper-bound filter | `filters.recordedTo` |

Important loader behavior:

- `requestType` must be present exactly as `requestType`; the loader checks that property before deserializing.
- Known property names are then deserialized with `PropertyNameCaseInsensitive = true`, but the source, examples, validator messages, and docs all use the camelCase names above.
- Unknown fields are rejected because `JsonUnmappedMemberHandling.Disallow` is enabled.

## Required fields

Only this field is required in the input document:

```json
{
  "requestType": "GetMeasurements"
}
```

The value must match the CLI `--type get-measurements` argument. A mismatch fails validation before posting.

`maxItems`, `lastNData`, and `filters` are optional.

## Optional fields

```json
{
  "requestType": "GetMeasurements",
  "maxItems": 100,
  "lastNData": 10,
  "filters": {
    "measurementLocationUuid": "55555555-5555-4555-8555-555555555555",
    "segmentUuid": "22222222-2222-4222-8222-222222222222",
    "recordedFrom": "2026-01-01T00:00:00Z",
    "recordedTo": "2026-01-02T00:00:00Z"
  }
}
```

### Validation rules

- `requestType`
  - Required.
  - Must deserialize to `GetMeasurements`.
  - Must match CLI `--type get-measurements`.
- `maxItems`
  - Optional.
  - Backing type is nullable `short`; accepted range is effectively `0..32767`.
  - Validator rejects negative values.
- `lastNData`
  - Optional.
  - Backing type is nullable `short`; accepted range is effectively `0..32767`.
  - Validator rejects negative values.
- `filters.measurementLocationUuid`
  - Optional.
  - Must be a valid UUID when supplied.
  - Supported for `GetMeasurements`.
- `filters.segmentUuid`
  - Optional.
  - Must be a valid UUID when supplied.
  - Supported for `GetMeasurements`.
- `filters.recordedFrom`
  - Optional.
  - Must parse as a date/time when supplied.
  - Supported only for `GetMeasurements`.
- `filters.recordedTo`
  - Optional.
  - Must parse as a date/time when supplied.
  - Supported only for `GetMeasurements`.
- `filters.recordedFrom` and `filters.recordedTo`
  - If both are valid and supplied, `recordedFrom` must be earlier than or equal to `recordedTo`.

### Explicitly unsupported filters for GetMeasurements

The validator rejects these for `GetMeasurements`:

- `filters.siteUuid`
- `filters.typeUuid`
- `filters.assetUuid`
- `filters.serialNumber`
- assessment-only fields such as `healthLevelTypeUuid`, `assessedFrom`, `assessedTo`, `healthLevelMin`, and `healthLevelMax`
- asset-segment-event fields such as `eventUuid`, `installedNow`, `installedFrom`, `installedTo`, `removedFrom`, and `removedTo`

The C# console README also states that GetMeasurements intentionally does not expose:

- `assetUuid`
- `siteUuid`
- `typeUuid`
- `measurementUuid`
- text filters
- numeric filters
- status filters

## Example minimal request

```json
{
  "requestType": "GetMeasurements"
}
```

This is valid short-form input. It leaves limits and criteria at connector defaults.

## Example request for selected measurement location

```json
{
  "requestType": "GetMeasurements",
  "maxItems": 100,
  "filters": {
    "measurementLocationUuid": "55555555-5555-4555-8555-555555555555"
  }
}
```

## Example request with date range

```json
{
  "requestType": "GetMeasurements",
  "maxItems": 100,
  "filters": {
    "measurementLocationUuid": "55555555-5555-4555-8555-555555555555",
    "recordedFrom": "2026-01-01T00:00:00Z",
    "recordedTo": "2026-01-02T00:00:00Z"
  }
}
```

Date values should be parseable by .NET `DateTimeOffset.TryParse`. Existing docs recommend ISO-style strings with offsets, such as:

```text
2026-06-17T00:00:00Z
2026-06-17T00:00:00-04:00
```

## Example request with last N data

```json
{
  "requestType": "GetMeasurements",
  "maxItems": 100,
  "lastNData": 10,
  "filters": {
    "measurementLocationUuid": "55555555-5555-4555-8555-555555555555"
  }
}
```

## Mapper targets

The short-form mapper writes:

| Short-form field | Connector criteria target |
|---|---|
| `maxItems` | `DataArea.Get.MaxItems` |
| `lastNData` | `ApplicationArea.UserArea.LastNData` |
| `filters.measurementLocationUuid` | `DataArea.MeasurementsCriteria[0].MeasurementLocationUUID.UUIDFilter.Value` |
| `filters.segmentUuid` | `DataArea.MeasurementsCriteria[0].SegmentUUID.UUIDFilter.Value` |
| `filters.recordedFrom` | `DataArea.MeasurementsCriteria[0].Recorded` with `MinInclusive` |
| `filters.recordedTo` | `DataArea.MeasurementsCriteria[0].Recorded` with `MaxInclusive` |

Generated BOD JSON uses lower-level CCOM names such as `getMeasurements`, `measurementsCriteria`, `measurementLocationUUID`, `segmentUUID`, `recorded`, and `userArea.lastNData`. These are not the CLI short-form input names.

## Expected ShowMeasurements response shape

The Toolkit tests and docs do not include a complete `ShowMeasurements` fixture. The response shape below is inferred from the local service response definition and response builder:

- `MCEGoldDataService/MCEGoldDataService/BODDefinitions/ShowMeasurementsDefinition.cs`
- `MCEGoldDataService/MCEGoldDataService/BODDefinitions/CCOMElements.cs`
- `MCEGoldDataService/MCEGoldDataService/Processes/CreateResponseBODs.cs`

Expected root:

```text
showMeasurements
```

Expected measurement row path:

```text
showMeasurements.dataArea.measurements[].measurement[]
```

The `measurements` array contains grouped containers. Each group has:

- `count`
- `measurement`: array of `SingleDataMeasurement` rows

Each measurement row is expected to contain:

| Meaning | Response path |
|---|---|
| Measurement UUID | `measurement.UUID` |
| Timestamp | `measurement.recorded.dateTime` |
| Value for Measure value class | `measurement.data.measure.value.numeric` |
| Unit for Measure value class | `measurement.data.measure.UnitOfMeasure.shortNames[0].text` |
| Unit UUID for Measure value class | `measurement.data.measure.UnitOfMeasure.UUID` |
| Value for Percentage value class | `measurement.data.percentage.numeric` |
| Value for Number value class | `measurement.data.number.numeric` |
| Measurement location UUID | `measurement.measurementLocation.UUID` |
| Measurement location name | `measurement.measurementLocation.shortNames[0].text` |
| Segment UUID | `measurement.segment.UUID` |
| Segment name | `measurement.segment.shortNames[0].text` |

Notes:

- For `Measure` rows, unit appears inside `data.measure.UnitOfMeasure`.
- For `Percentage` and `Number` rows, the response builder does not attach a unit.
- The response builder generates `measurement.UUID` with `Guid.NewGuid()` for each row, so this appears to be a response-row UUID rather than a stable source measurement definition UUID.
- The response builder includes `measurementLocation` and `segment` objects on each row; there is no separate parent group object for location or segment in `ShowMeasurementsDefinition`.
- Empty results are represented as `showMeasurements.dataArea.measurements[]` containing an empty measurement container.

## Open questions / uncertainty

- No Toolkit test fixture was found for a real `ShowMeasurements` payload, so parser implementation should be tested against an actual captured CLI response before relying solely on the inferred shape.
- Unit casing is unusual in the response builder: `data.measure.UnitOfMeasure` uses an uppercase `U`, matching the `JsonProperty("UnitOfMeasure")` attribute.
- The short-form contract does not expose measurement type, unit, status, text search, numeric comparisons, measurement UUID, site UUID, or asset UUID. Any portal filters for those fields would need to be local post-response filters unless the CLI contract changes.
- The response does not appear to include a direct measurement type label. The portal may need to derive display labels from the selected Measurement Location context or show a neutral measurement/value label.
