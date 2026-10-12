# Configuration Guide

[Back to README](../README.md)

Most users configure the single-image appliance through the Portal Settings page. Settings are persisted under `/config`; discovered data and persistent runtime data are stored under `/data`.

## Configuration Precedence

For supported Portal settings, the application resolves configuration in this order:

1. Environment variable override.
2. Local configuration file value.
3. Application default.

This means an environment variable can override a value saved in the local Portal configuration file.

## MCEGold Data Services Connection

Configure these values with placeholders supplied by your environment:

| Setting | Environment variable | Purpose |
| --- | --- | --- |
| MCEGold Data Services URL | `MCEGOLD_HOST` | Base endpoint for MCEGold Data Services |
| Username | `MCEGOLD_USERNAME` | User name for the configured authentication scheme |
| Password | `MCEGOLD_PASSWORD` | Password for the configured authentication scheme |
| API key | `MCEGOLD_API_KEY` | API key when required by the target environment |

Do not commit real credentials, internal endpoints, or API keys.

## Single-Image Paths

The default single-image appliance uses these paths:

| Item | Path |
| --- | --- |
| Portal local config | `/config/portal.local.json` |
| Connector config | `/config/connector.config.json` |
| Collector config | `/config/collector.local.json` |
| SQLite discovery database | `/data/discovery_portal.db` |

The first container startup seeds the configuration files if they are not already present in `/config`. Existing files are not overwritten.

## Portal Settings

The Settings page stores local Portal configuration and synchronizes the Connector configuration used by the Portal and Publication Collector.

User-facing settings include:

- MCEGold Data Services URL.
- Username.
- Password.
- API key.
- Grafana dashboard URL.
- Publication Collector controls.
- Data retention controls.

The default image already configures the bundled Connector CLI path. Users normally configure MCEGold Data Services values in the Portal rather than installing the CLI manually.

## Connector CLI Settings

The appliance uses the bundled Connector CLI to communicate with MCEGold Data Services.

| Setting | Environment variable | Default in single-image appliance |
| --- | --- | --- |
| Connector CLI path | `MCEGOLD_CLI_PATH` | `/opt/mcegold-cli/MCEGold.Data.Services.Connector.Cli` |
| Connector config path | `CONNECTOR_CONFIG_PATH` | `/config/connector.config.json` |
| CLI timeout seconds | `MCEGOLD_CLI_TIMEOUT_SECONDS` | `60` |

The CLI timeout can be useful when the request channel or target environment is slow.

## Discovery Database

The SQLite discovery database path is configured by `DISCOVERY_DATABASE_PATH` and defaults to:

```text
/data/discovery_portal.db
```

This database stores discovered entities, measurement data, application settings, reference dimensions, and runtime status used by the appliance.

## Publication Collector Settings

The Publication Collector runs inside the default appliance. User-facing collector settings are stored in the SQLite application settings table.

Verified defaults:

| Setting | Default | Purpose |
| --- | --- | --- |
| `Collector.Enabled` | `true` | Enables publication processing |
| `Collector.PollingIntervalSeconds` | `15` | Polling interval for collector activity |

The Portal Settings page also shows collector runtime status, last seen time, last publication time, and last error when available.

## Data Retention

Data retention settings are stored in the SQLite application settings table.

Verified defaults and range:

| Setting | Default | Range | Purpose |
| --- | --- | --- | --- |
| `DataRetention.Enabled` | `false` | `true` or `false` | Enables automatic retention cleanup |
| `DataRetention.Days` | `90` | `30` to `730` | Measurement retention period |

Retention cleanup is separate from publication ingestion. Enabling retention does not enable publication processing by itself.

## Grafana Dashboard URL

The Portal uses the Grafana dashboard URL when opening the dashboard from the UI. The default local URL points at port `3000`.

For access from another machine, use the Docker host name or IP address:

```text
http://<docker-host>:3000/d/bfvnuobjmh3wgc/mcegold-operations?orgId=1
```

## Session Secret

`SESSION_SECRET_KEY` controls the web session signing secret. The default development placeholder should be changed for shared or persistent deployments.

Example placeholder:

```text
SESSION_SECRET_KEY=<use-a-deployment-specific-secret>
```

## Reference Data

The Portal seeds local SQLite reference dimensions from `docs/CCOM Reference Data.xml` when a database is new or unseeded. The default single-image appliance includes this file.

Reference data supports type selectors and reporting metadata. It does not create demo Sites, Segments, Measurement Locations, or Measurement facts.
