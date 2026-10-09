# Discovery Workflows

[Back to README](../README.md)

The Portal supports guided top-down discovery and works with the Publication Collector for incoming publication data.

## Top-Down Discovery

Top-down discovery starts with broad context and narrows toward measurement data:

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

This path helps users keep operational context while exploring available MCEGold data.

## Publication Collector

The Publication Collector runs in the default container and processes MCEGold publications. It uses the configured Connector CLI and connection settings, then writes runtime status and incoming measurement data to the local SQLite database.

The Portal Settings page exposes collector enablement, polling interval, and runtime status. The setting controls whether publication processing should be active; it is not a separate installer or manual CLI setup step for the default image.

## Bottom-Up Discovery

Bottom-up discovery is the conceptual counterpart to the guided top-down workflow. When incoming publication data references measurement context that is not already present locally, the deployment may need to discover or persist the missing hierarchy around that measurement.

At a user level, this means publication processing and guided discovery both contribute to the same local SQLite discovery database. The public documentation intentionally avoids proprietary Connector internals and lower-level implementation details.

## Grafana View

Grafana reads from the SQLite database and displays discovered or collected measurement data. It is useful after top-down discovery has stored entities or after the Publication Collector has processed incoming publications.
