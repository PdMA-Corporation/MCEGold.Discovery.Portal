# Discovery Workflows

[Back to README](../README.md)

The appliance supports two independent approaches to discovery. Both persist discovered information in the shared SQLite discovery database, which Grafana reads for visualization.

![Human-guided top-down and publication-driven bottom-up discovery approaches](images/MCEGold%20Discovery%20Approaches%20Flowchart.png)

## Human-Guided Top-Down Discovery

The Discovery Portal uses Consumer Request sessions to start with broad operational context and narrow toward measurement data:

```text
Site -> Segment -> Measurement Location -> Measurements
```

The Portal guides the user through each step:

1. Start discovery.
2. Select a Site.
3. Select a Segment for that Site.
4. Select a Measurement Location for that Segment.
5. Preview Measurements for that Measurement Location.
6. End discovery when finished.

This workflow keeps each request tied to the selected parent context. It helps users understand the MCEGold hierarchy before inspecting measurement values.

The Portal owns and manages the Consumer Request Session. It persists the Session ID and original start timestamp in SQLite and restores them after a Portal or container restart when the database is retained. Restart does not automatically open a replacement session, and restored information does not guarantee that the remote session remains valid. See [Request Session Management](troubleshooting.md#known-limitations--request-session-management) for recovery behavior.

## Site

The Site step discovers available Sites from MCEGold Data Services. A Site is the top-level operational context for the guided workflow.

## Segment

The Segment step requires a selected Site. It discovers Segments under that Site and can use type information from local reference data where available.

## Measurement Location

The Measurement Location step requires a selected Segment. It discovers Measurement Locations under that Segment. A Measurement Location is the point, sensor, or logical location where measurements are observed.

## Measurements

The Measurements step requires a selected Measurement Location. It previews measurement values for that location, with bounded result limits and optional recorded-time filters.

This preview is for discovery and validation. Grafana is the primary bundled surface for dashboard-style inspection of persisted measurement data.

## Publication-Driven Bottom-Up Discovery

The Publication Collector runs independently of the Portal's interactive workflow. It primarily receives measurement publications through Publication sessions and stores incoming measurement data and runtime status locally.

When a publication references a Measurement Location that is not yet known in the local database, the Collector retrieves the missing Measurement Location, Segment, and Site context as needed and persists that context. This is targeted, on-demand reference enrichment initiated by an incoming publication; it is not a complete top-down inventory crawl.

With Shared Request Session mode enabled, the Collector reads the Portal-managed session information from the same live SQLite database and reuses that Consumer Request Session for enrichment. The Collector does not open or close the Portal-owned session. If none is available, enrichment is deferred; Start Discovery in the Portal establishes a session. The user does not need to complete the guided discovery steps for Collector enrichment to use it.

With shared mode disabled, the Collector opens its own temporary Consumer Request Session for enrichment and closes that session afterward. The standalone Collector defaults to disabled shared mode; the combined v1.0.1 Docker image enables it in newly seeded configuration. See [Publication Collector Settings](configuration.md#publication-collector-settings) for configuration and upgrades.

The Collector does not invoke the Portal's discovery endpoints. Both applications use the bundled Connector CLI independently with the configured MCEGold Data Services connection settings. Normal publication processing uses Publication sessions, separately from Consumer Request Sessions used for enrichment.

The Portal Settings page exposes Collector enablement, polling interval, and runtime status. No separate Connector CLI installation is required for the published single-image appliance.

## Persistence

Discovered entities and measurements are stored in the shared SQLite discovery database. Guided discovery and publication-driven enrichment both contribute to the same local persistence layer.

Grafana reads from the SQLite discovery database and displays discovered or collected measurement data.
