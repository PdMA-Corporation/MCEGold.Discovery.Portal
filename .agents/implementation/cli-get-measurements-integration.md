# CLI-backed GetMeasurements Stage 1 preview

The Measurements page is a discovery and validation preview. It is intentionally not an analytics surface: no charts, Grafana embeds, statistics, or Asset workflow are included in this stage.

## UI behavior

The page does not display rows on initial load. It shows:

```text
Set filters and click Search to preview measurements for this location.
```

The filter panel contains only:

- Recorded From
- Recorded To
- Max Items

Max Items is a dropdown with:

- `10`
- `25`
- `50`

Default Max Items is `10`; the maximum accepted value is `50`.

The page does not render Measurement Type, Unit, Status, Search by measurement name, or Last N Data filters. Unit is shown in the selected Measurement Location context panel instead of repeated in every row.

## Request

The portal posts a short-form `GetMeasurements` request through the active request session. It uses the request session opened by Start Discovery; it does not open a new request session for each preview query.

The UI displays only Max Items. Because the Stage 1 Measurements workflow is scoped to one selected Measurement Location and one selected Segment, the portal maps the selected Max Items value to both `maxItems` and `lastNData`. This avoids backend defaults from limiting the preview to fewer rows than the user selected while still preventing arbitrary Last N Data values from the query string or UI.

Minimal Stage 1 preview request:

```json
{
  "requestType": "GetMeasurements",
  "maxItems": 10,
  "lastNData": 10,
  "filters": {
    "measurementLocationUuid": "{selected_location_uuid}",
    "segmentUuid": "{selected_segment_uuid}"
  }
}
```

With optional recorded range:

```json
{
  "requestType": "GetMeasurements",
  "maxItems": 10,
  "lastNData": 10,
  "filters": {
    "measurementLocationUuid": "{selected_location_uuid}",
    "segmentUuid": "{selected_segment_uuid}",
    "recordedFrom": "2026-01-01T00:00:00Z",
    "recordedTo": "2026-01-02T00:00:00Z"
  }
}
```

Rules:

- Always include `requestType`.
- Always include `maxItems` from the dropdown.
- Always include `lastNData` with the same value as `maxItems`.
- Always include `filters.measurementLocationUuid`.
- Always include `filters.segmentUuid`.
- Include `filters.recordedFrom` only when supplied.
- Include `filters.recordedTo` only when supplied.
- Do not accept independent `lastNData` / `last_n_data` values from the portal UI or query string.
- Do not include unsupported filters.

## Validation

Blank dates are allowed. If both dates are supplied, `recordedFrom` must be earlier than or equal to `recordedTo`. Invalid date ranges show a friendly validation message and do not call the CLI.

Max Items must be a positive integer and cannot exceed `50`. The UI offers `10`, `25`, and `50`.

## Results

The Stage 1 table displays only:

- Recorded UTC
- Value

If no rows are returned, the page shows:

```text
No measurements found for this location and filter.
```

For larger analysis, use Grafana, the Python Toolkit, or data ingestion workflows rather than expanding this preview page into an analytics tool.
