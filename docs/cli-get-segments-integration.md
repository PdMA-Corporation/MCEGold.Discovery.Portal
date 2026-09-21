# CLI-backed GetSegments integration

## Purpose

The Discovery Portal uses `MCEGold.Data.Services.Connector.Cli` to retrieve real Segments after a user selects a Site. Measurement Locations and Measurements are also CLI-backed in deeper workflow levels.

## Request shape

The portal posts a short-form `GetSegments` request through the active request session.

Without an optional type filter:

```json
{
  "requestType": "GetSegments",
  "maxItems": 100,
  "filters": {
    "siteUuid": "{selected_site_uuid}"
  }
}
```

With Segment Type selected:

```json
{
  "requestType": "GetSegments",
  "maxItems": 100,
  "filters": {
    "siteUuid": "{selected_site_uuid}",
    "typeUuid": "{selected_segment_type_uuid}"
  }
}
```

Note: the portal query parameter is `segment_type_uuid`, but the Connector CLI short-form contract uses `filters.typeUuid`.

## CLI commands

The portal uses the existing active request session:

```text
request post --config <config> --session-id <sessionId> --type get-segments --input <temp-payload.json> --output json
request read-response --config <config> --session-id <sessionId> --request-id <requestMessageId> --output json
```

## Response shape

The parser supports:

```text
showSegments.dataArea.segments[].segments[]
```

including these envelope locations:

- `envelope.data.showSegments.dataArea.segments[].segments[]`
- `envelope.raw.showSegments.dataArea.segments[].segments[]`
- direct `showSegments.dataArea.segments[].segments[]`

## Mapping

- `segment_uuid` = `segment.UUID`
- `site_uuid` = `group.site.UUID`
- `segment_name` = `segment.shortNames[0].text`
- `segment_type` = `segment.type.shortNames[0].text`
- `segment_type_uuid` = `segment.type.UUID`

Missing names or types are handled safely with fallback values.

## Display columns

The Segment page displays:

- Segment Name
- Segment Type
- Segment UUID
- Action

Status and Description are intentionally hidden because they are not part of the observed `ShowSegments` response.

## Troubleshooting

If GetSegments fails:

1. Confirm Start Discovery opened a request session.
2. Confirm the selected Site UUID exists in the remote system.
3. Try Search with no Segment Type filter first.
4. Confirm the selected Segment Type UUID exists in the reference data and remote data.
5. Check the friendly UI error for exit code, fault code/message, and short stderr.
