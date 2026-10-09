# Configuration Guide

[Back to README](../README.md)

Most users configure the single-image deployment through the Portal Settings page. Settings and local configuration are persisted under `/config`; discovered data and Grafana data are persisted under `/data`.

## MCEGold Data Services Connection

Configure these values with placeholders supplied by your environment:

| Setting | Purpose |
| --- | --- |
| MCEGold Data Services URL | Base endpoint for MCEGold Data Services |
| Username | User name for the configured authentication scheme |
| Password | Password for the configured authentication scheme |
| API key | API key when required by the target environment |

Do not commit real credentials or internal endpoint values.

## Portal Settings

The Settings page stores local Portal configuration and synchronizes the Connector configuration used by the Portal and Publication Collector.

In the single-image deployment, the default paths are:

| Item | Path |
| --- | --- |
| Portal local config | `/config/portal.local.json` |
| Connector config | `/config/connector.config.json` |
| Collector config | `/config/collector.local.json` |
| SQLite database | `/data/discovery_portal.db` |

## Publication Collector Settings

The Portal Settings page includes user-facing collector controls:

- Enable or pause publication processing.
- Set the polling interval.
- View collector runtime status, last seen time, last publication time, and last error when available.

The Collector process runs inside the container. The enable setting controls whether publication processing should be active.

## Data Retention

Data retention settings are stored in the SQLite application settings table:

- Enable or disable automatic retention cleanup.
- Set the measurement retention period.

Retention cleanup is separate from publication ingestion. Enabling retention does not enable publication processing by itself.

## Grafana Dashboard URL

The Portal uses the Grafana dashboard URL to open the dashboard from the UI. The default local URL points at port `3000`.

For access from another machine, update the URL to use the Docker host name or IP address, for example:

```text
http://<docker-host>:3000/d/bfvnuobjmh3wgc/mcegold-operations?orgId=1
```

## Environment Overrides

The application supports environment-variable overrides for local configuration. Common variables include:

- `MCEGOLD_HOST`
- `MCEGOLD_USERNAME`
- `MCEGOLD_PASSWORD`
- `MCEGOLD_API_KEY`
- `MCEGOLD_CLI_PATH`
- `CONNECTOR_CONFIG_PATH`
- `DISCOVERY_DATABASE_PATH`
- `GRAFANA_DASHBOARD_URL`
- `SESSION_SECRET_KEY`

For the default image, the Connector CLI path is already configured. Users normally configure MCEGold Data Services values in the Portal rather than installing the CLI manually.

## Reference Data

The Portal seeds local SQLite reference dimensions from `docs/CCOM Reference Data.xml` when a database is new or unseeded. The default single-image deployment includes this file.

The reference data supports type selectors and reporting metadata. It does not create demo Sites, Segments, Measurement Locations, or Measurement facts.
