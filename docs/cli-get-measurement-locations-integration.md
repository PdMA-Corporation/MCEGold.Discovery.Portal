# CLI-backed GetMeasurementLocations integration

The Discovery Portal uses `MCEGold.Data.Services.Connector.Cli` to retrieve real Measurement Locations after a user selects a Segment. Sites, Segments, Measurement Locations, and Measurements are CLI-backed.

## Request

The portal posts a short-form `GetMeasurementLocations` request through the active request session.

Without an optional type filter:

```json
{
  "requestType": "GetMeasurementLocations",
  "maxItems": 100,
  "filters": {
    "segmentUuid": "{selected_segment_uuid}"
  }
}
```

With Measurement Location Type selected:

```json
{
  "requestType": "GetMeasurementLocations",
  "maxItems": 100,
  "filters": {
    "segmentUuid": "{selected_segment_uuid}",
    "typeUuid": "{selected_measurement_location_type_uuid}"
  }
}
```

Note: the portal query parameter is `measurement_location_type_uuid`, but the Connector CLI short-form contract uses `filters.typeUuid`.

CLI command:

```text
request post --type get-measurement-locations
```

The request is posted and read using the active request session:

```text
request post --session-id <session> --type get-measurement-locations --input <payload> --output json
request read-response --session-id <session> --request-id <requestMessageId> --output json
```

## Response parsing

The observed response shape is:

```text
showMeasurementLocations.dataArea.measurementLocations[].measurementLocation[]
```

The parser supports:

- `envelope.data.showMeasurementLocations.dataArea.measurementLocations[].measurementLocation[]`
- `envelope.raw.showMeasurementLocations.dataArea.measurementLocations[].measurementLocation[]`
- direct `showMeasurementLocations.dataArea.measurementLocations[].measurementLocation[]`
- measurement location groups as a list or a single object
- `measurementLocation` as a list or a single object
- missing names, types, units, quantities, and parent segment

Mapping:

- `location_uuid` ← `measurementLocation.UUID`
- `segment_uuid` ← parent group `segment.UUID`, falling back to selected SegmentUuid
- `location_name` ← `measurementLocation.shortNames[0].text`
- `location_type` ← `measurementLocation.type.shortNames[0].text`
- `type_uuid` ← `measurementLocation.type.UUID`
- `value_class` ← `measurementLocation.valueClass`
- `unit` ← `measurementLocation.defaultUnitOfMeasure.shortNames[0].text`
- `unit_uuid` ← `measurementLocation.defaultUnitOfMeasure.UUID`
- `uom_quantity` ← `measurementLocation.UOMQuantity.shortNames[0].text`

If no default unit is present, Percentage values display `%` and Number values display `—`.

## UI behavior

The Measurement Locations page does not display rows on initial load. The user may optionally choose a Measurement Location Type and click Search.

Filters:

- Measurement Location Type: sent to the CLI as `filters.typeUuid`.

The implemented short-form interface does not support location-name/text or value-class filters, so the page does not render those filters and the portal does not apply local post-response name filtering in this phase.

Displayed columns match the response:

- Measurement Location
- Type
- Value Class
- Unit
- UUID
- Action

Status, Description, and Type UUID are intentionally hidden because they are not dependable display columns in the observed `ShowMeasurementLocations` response.

## Errors

If `GetMeasurementLocations` fails, the page shows a compact Bootstrap warning with Connector Mode, operation, exit code when available, fault code/message when available, and short redacted stderr. The raw response and credentials are never displayed.
