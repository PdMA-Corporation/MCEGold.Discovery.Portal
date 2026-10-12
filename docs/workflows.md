# Discovery Workflows

[Back to README](../README.md)

The appliance supports guided top-down discovery and publication-driven collection. Both paths store local data in the SQLite discovery database.

## Top-Down Discovery

Top-down discovery starts with broad operational context and narrows toward measurement data:

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

## Site

The Site step discovers available Sites from MCEGold Data Services. A Site is the top-level operational context for the guided workflow.

## Segment

The Segment step requires a selected Site. It discovers Segments under that Site and can use type information from local reference data where available.

## Measurement Location

The Measurement Location step requires a selected Segment. It discovers Measurement Locations under that Segment. A Measurement Location is the point, sensor, or logical location where measurements are observed.

## Measurements

The Measurements step requires a selected Measurement Location. It previews measurement values for that location, with bounded result limits and optional recorded-time filters.

This preview is for discovery and validation. Grafana is the primary bundled surface for dashboard-style inspection of persisted measurement data.

## Publication Collector

The Publication Collector runs in the default appliance. It uses the bundled Connector CLI and configured MCEGold Data Services connection settings, then stores incoming publication data and runtime status locally.

The Portal Settings page exposes collector enablement, polling interval, and runtime status. No separate Connector CLI installation is required for the published single-image appliance.

## Bottom-Up Discovery

Bottom-up discovery is the conceptual counterpart to the guided top-down workflow. Publication-driven processing may encounter incoming measurement data before all local hierarchy or context has been established. In that case, the appliance may need to establish or persist the missing local context around the incoming measurement data.

Public documentation intentionally keeps this explanation conceptual and avoids proprietary Connector internals.

## Persistence

Discovered entities and measurements are stored in the SQLite discovery database. Guided discovery and publication processing both contribute to the same local persistence layer.

Grafana reads from the SQLite discovery database and displays discovered or collected measurement data.
