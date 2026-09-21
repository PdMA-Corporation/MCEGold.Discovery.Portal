# Workflow session context

The Discovery Portal preserves the selected workflow context in the web session to avoid unnecessary ISBM/CLI requests.

This is intentional reference-code behavior. Each CLI request should be driven by a user action, not by page rendering trying to reconstruct upstream context.

## Stored context

The portal stores only safe display context:

- `selected_site`: UUID, name, type
- `selected_segment`: UUID, name, type
- `selected_measurement_location`: UUID, name, type, value class, unit

The session does not store credentials, connector configuration, raw ISBM payloads, or CLI command details.

## Request lifecycle

- Start Discovery opens a request session and clears stale selected context.
- Sites page calls `GetSites`.
- Selecting a Site stores site context, then opens the Segments page.
- Segments page rendering does not call `GetSites`.
- Searching Segments calls `GetSegments`.
- Selecting a Segment stores segment context, then opens the Measurement Locations page.
- Measurement Locations page rendering does not call `GetSites` or `GetSegments`.
- Searching Measurement Locations calls `GetMeasurementLocations`.
- Selecting a Measurement Location stores location context, then opens the Measurements page.
- Measurements page rendering does not call `GetSites`, `GetSegments`, or `GetMeasurementLocations`.
- Searching Measurements calls `GetMeasurements`.
- End Discovery closes the request session and clears selected context.

Direct deep links into child workflow pages require the user to navigate from the top of the guided workflow. This keeps the demo predictable and avoids hidden upstream calls.
