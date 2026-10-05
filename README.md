# MCEGold Discovery Portal

MCEGold Discovery Portal is a public reference/demo application for exploring MCEGold Data Services discovery workflows and initializing the shared SQLite database used by the MCEGold discovery demo ecosystem.

The public ecosystem is intended to be used together:

- **MCEGold.Data.Services.Connector.Toolkit** teaches developers how to use the Connector package and related tooling.
- **MCEGold.Discovery.Portal** owns the reference SQLite schema, initializes the database, provides guided UI workflows, and includes optional Grafana assets.
- **MCEGold.Discovery.PublicationCollector** consumes the Portal-created SQLite database, writes measurements and runtime status, and does not own schema creation.

## Current Scope

The Portal demonstrates a guided top-down discovery workflow:

```text
Site -> Segment -> Measurement Location -> Measurements
```

It also participates in the broader bottom-up/runtime data pattern by persisting newly discovered runtime entities into local dimensions and measurement facts when discovery requests return them. The Portal is not a fully autonomous bottom-up discovery engine; long-running runtime collection belongs to the Publication Collector.

## Prerequisites

- Python 3.12 is the recommended development baseline.
- Access to `MCEGold.Data.Services.Connector.Cli` as an external prerequisite.
- MCEGold Data Services connection details for live discovery.
- Optional: Grafana with the `frser-sqlite-datasource` plugin, version `4.0.6` for deterministic v1.0.0 release validation.
- Optional: Docker, if you want to build a Portal container image.

The Connector CLI binary bundle is not included in this public-release candidate. Configure `MCEGOLD_CLI_PATH` or `configs/portal.local.json` to point to a local Connector CLI installation. The Toolkit publishes a self-contained Linux CLI package for users, and the official self-contained CLI runtime may be bundled into a future official MCEGold Discovery Docker image with the proprietary dependency notice described in [Third-Party Notices](THIRD-PARTY-NOTICES.md).

## Install and Run Locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SESSION_SECRET_KEY="change-this-for-local-testing"
python run.py
```

Then open:

```text
http://127.0.0.1:8000
```

For Linux/macOS-style shells:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SESSION_SECRET_KEY="change-this-for-local-testing"
python run.py
```

## Configuration

Create local configuration files from the tracked examples when needed:

```powershell
Copy-Item configs\portal.local.example.json configs\portal.local.json
Copy-Item configs\connector.config.example.json configs\connector.config.json
```

Do not commit the local files. They may contain machine-specific paths and credentials.

Portal configuration is resolved from environment variables first, then `configs/portal.local.json`, then built-in defaults. Important values include:

- `MCEGOLD_HOST`
- `MCEGOLD_USERNAME`
- `MCEGOLD_PASSWORD`
- `MCEGOLD_API_KEY`
- `MCEGOLD_CLI_PATH`
- `CONNECTOR_CONFIG_PATH`
- `DISCOVERY_DATABASE_PATH`
- `GRAFANA_DASHBOARD_URL`
- `SESSION_SECRET_KEY`

The Settings page can write local values to `configs/portal.local.json`. Password and API key values are not rendered back to the browser, but local-file credential storage is still clear text. Use environment variables or a stronger secret provider for deployments that need stronger protection.

## SQLite Database Ownership

The Portal is the authoritative owner of the reference SQLite schema.

Verified source behavior:

- `app/main.py` initializes the database during application startup.
- `app/storage/database.py` owns schema creation.
- `CURRENT_SCHEMA_VERSION = 17`.
- Fresh database creation creates the current schema directly.
- Existing pre-release databases below schema version 17 are rejected instead of upgraded through a migration chain.
- Test schemas and test fixtures are not the production initialization mechanism.

The default database path is:

```text
data/discovery_portal.db
```

Override it with:

```powershell
$env:DISCOVERY_DATABASE_PATH="path\to\discovery_portal.db"
```

or with `discoveryDatabasePath` in `configs/portal.local.json`.

To inspect the configured database path without intentionally modifying schema, use:

```powershell
python scripts/inspect_database_schema.py
python scripts/inspect_database_schema.py --json
```

To inspect a specific database path:

```powershell
python scripts/inspect_database_schema.py --database data\discovery_portal.db
```

## Database Setup Flow

For a new local demo environment:

1. Configure Portal settings and Connector CLI paths.
2. Start Portal with `python run.py`.
3. Let Portal initialize `data/discovery_portal.db` automatically.
4. Confirm schema version 17 with `python scripts/inspect_database_schema.py`.
5. Point PublicationCollector at the same physical SQLite database.
6. Point Grafana at the same SQLite database if using the dashboard assets.

Portal-created tables used by PublicationCollector include:

- `ApplicationSetting`
- `CollectorRuntimeStatus`
- `DimMeasurementLocation`
- `FactMeasurement`

## PublicationCollector Integration

Portal owns:

- SQLite database creation
- SQLite schema version 17
- desired collector settings in `ApplicationSetting`
- reference UI workflows and local settings

PublicationCollector consumes the database and writes runtime measurements/status. It updates or reads tables such as `FactMeasurement`, `CollectorRuntimeStatus`, and `ApplicationSetting` according to its own runtime behavior.

Portal does not start or stop the PublicationCollector process. The Collector process remains owned by the operating system, Docker, or a service wrapper. Portal settings such as `Collector.Enabled` represent desired processing state for a running Collector.

Local config path distinction:

- Portal local config: `configs/portal.local.json`
- Collector local config: `config/collector.local.json`

For Docker-style deployments, the intended shared paths are:

- Portal config: `/config/portal.local.json`
- Connector config: `/config/connector.config.json`
- Shared SQLite database: `/data/discovery_portal.db`

## Reference Data

Portal startup seeds supported reference dimensions from:

```text
docs/CCOM Reference Data.xml
```

The XML file is required to initialize an unseeded database unless `REFERENCE_DATA_PATH` is pointed at another valid copy. After a database has already been seeded successfully, startup can use the database marker and reference rows without reparsing the XML. The CCOM reference data is third-party MIMOSA material. It may be distributed with the Portal source and with a future MCEGold Discovery Docker image subject to applicable MIMOSA license conditions, and it is not licensed under the Portal MIT License.

Seeded reference dimensions include:

- `DimSiteType`
- `DimSegmentType`
- `DimMeasurementLocationType`
- `DimUnit`
- `DimUomQuantity`
- `DimInfoSource`

Startup does not insert demo Sites, Segments, Measurement Locations, or Measurement facts.

## Guided Discovery Workflow

Implementation areas:

- `app/api/routes.py` owns web routes and selected workflow context.
- `app/services/mcegold_cli_discovery_client.py` invokes `MCEGold.Data.Services.Connector.Cli` and maps response payloads.
- `app/storage/discovered_entity_store.py` persists discovered runtime entities into SQLite.

Workflow summary:

1. Start Discovery opens a Connector request session.
2. Sites page requests `GetSites`.
3. Selecting a Site opens Segments.
4. Segments page requests `GetSegments` for the selected Site.
5. Selecting a Segment opens Measurement Locations.
6. Measurement Locations page requests `GetMeasurementLocations` for the selected Segment.
7. Selecting a Measurement Location opens Measurements.
8. Measurements page requests a bounded `GetMeasurements` preview.
9. End Discovery closes the request session and clears selected context.

Discovery responses can upsert Sites, Segments, Measurement Locations, reference metadata observed at runtime, and Measurement facts into the local schema.

## Grafana

Grafana assets are optional reference/demo assets:

- `grafana/mcegold-operations.json`
- `grafana/provisioning/datasources/sqlite.yaml`
- `grafana/provisioning/dashboards/dashboards.yaml`

The datasource provisioning expects the `frser-sqlite-datasource` plugin and a SQLite database at:

```text
/data/discovery_portal.db
```

For v1.0.0 release validation, pin the SQLite datasource plugin to:

```text
frser-sqlite-datasource 4.0.6
```

The plugin must be installed before Grafana starts so datasource provisioning can resolve the plugin type. The pinned version was selected from the Grafana plugin catalog and upstream release metadata checked on 2026-09-30. Final image work should also pin and smoke-test the selected Grafana server version.

For local non-container use, adjust the datasource path to the same database initialized by Portal.

## Docker Status

The Dockerfile builds a Python Portal image and keeps the same container path conventions used by the broader demo environment. It no longer copies a committed Connector CLI binary bundle.

A full runtime container still requires an externally provided Connector CLI at the configured `MCEGOLD_CLI_PATH`. Future combined-image work may bundle the official self-contained Connector CLI runtime only with clear notice that the CLI/tooling layer and the proprietary `MCEGold.Data.Services.Connector` runtime/library have different licensing and source-availability boundaries.

### Single-Image Runtime

`Dockerfile.single-image` builds the local appliance foundation for running Portal, PublicationCollector, and Grafana together under `supervisord`.

The image contains:

- Portal served by Uvicorn on port `8000`
- PublicationCollector installed from the sibling `MCEGold.Discovery.PublicationCollector` Python package
- Grafana OSS served on port `3000`
- the pinned `frser-sqlite-datasource` plugin for SQLite dashboard access
- the official self-contained Linux x64 Connector CLI runtime unpacked under `/opt/mcegold-cli`
- `supervisord` as PID 1
- safe default config templates
- Portal license and third-party notice files

Build from this repository with the Collector repository and validated Connector CLI package directory supplied as named build contexts:

```powershell
docker build `
  -f Dockerfile.single-image `
  --build-context collector-source=../MCEGold.Discovery.PublicationCollector `
  --build-context connector-cli-package=../MCEGold.Data.Services.Connector.Toolkit/artifacts `
  -t mcegold-discovery:phase2a `
  .
```

The `connector-cli-package` context must contain:

```text
mcegold-python-linux-x64-v1.0.0.tar.gz
```

Run locally with persistent named volumes:

```powershell
docker volume create mcegold-discovery-data
docker volume create mcegold-discovery-config

docker run --rm `
  --name mcegold-discovery `
  -p 8000:8000 `
  -p 3000:3000 `
  -v mcegold-discovery-data:/data `
  -v mcegold-discovery-config:/config `
  mcegold-discovery:phase2a
```

Open:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/health
http://127.0.0.1:3000
```

Runtime paths inside the container:

- Portal application: `/app/portal`
- Collector package runtime: installed in the Python environment
- Runtime config directory: `/config`
- Persistent data directory: `/data`
- Shared SQLite database: `/data/discovery_portal.db`
- Grafana data directory: `/data/grafana`
- Grafana config: `/etc/grafana/grafana.ini`
- Grafana provisioning: `/etc/grafana/provisioning`
- Grafana dashboards: `/etc/grafana/dashboards`
- Bundled Connector CLI path: `/opt/mcegold-cli/MCEGold.Data.Services.Connector.Cli`

On first startup, the entrypoint copies safe templates to `/config/portal.local.json`, `/config/collector.local.json`, and `/config/connector.config.json` only when those files are absent. Existing mounted config files are preserved. Environment-variable overrides continue to take precedence according to the existing Portal and Collector configuration rules.

Grafana uses `GF_SECURITY_ADMIN_USER=admin`. If `GF_SECURITY_ADMIN_PASSWORD` is not provided, the entrypoint generates a password once and stores it in `/config/grafana.admin.password` with owner-only permissions. Preserve the `/config` volume to keep the generated Grafana admin password stable across restarts.

For browser access from another machine, update **Settings -> Grafana dashboard URL** to the Docker host name or IP address, for example:

```text
http://<docker-host>:3000/d/bfvnuobjmh3wgc/mcegold-operations?orgId=1
```

Portal owns database creation, schema initialization, and reference-data seeding. The Collector process starts under supervisor after a readiness gate confirms the shared SQLite database exists with the Portal-owned schema. Use the Portal Settings page to enter the MCEGold endpoint and credentials; saving settings updates both `/config/portal.local.json` and `/config/connector.config.json` so Portal and Collector use the same bundled CLI and connection configuration. Without live MCEGold connection settings, the Collector remains in a degraded/idle retry posture and logs that connection settings are unavailable; basic container liveness does not require live MCEGold connectivity.

Stop the container with:

```powershell
docker stop mcegold-discovery
```

Restarting with the same `/data` volume reuses the existing SQLite database and Grafana state. Restarting with the same `/config` volume preserves settings saved through the UI and the generated Grafana admin password.

GHCR publishing, release tags, and GitHub Releases are deferred to later phases.

## Tests

Run the local test suite with:

```text
pytest
```

Tests are designed to use local/temp resources and mocked CLI behavior where appropriate. Do not convert unit tests into live integration tests that require internal services or real credentials.

## Security Notes

This is a local/reference/demo application. It does not provide a complete authentication or production authorization layer.

`SESSION_SECRET_KEY` signs session data; it is not user authentication. Override the development default for any shared or persistent environment.

`adminControlsEnabled` can hide Settings and selected administrative controls, but it is not a replacement for authentication or network access control.

Do not expose the Settings/admin UI on an untrusted network. For wider exposure, put Portal and Grafana behind an approved reverse proxy, identity provider, VPN, or equivalent network access control.

Grafana default admin credentials must not be used in exposed environments. Set explicit Grafana admin credentials or an approved authentication mechanism before making Grafana reachable beyond a trusted local/LAN demo context.

Keep credentials in ignored local config files or environment variables. Do not commit real credentials, connector configs, local SQLite databases, or captured live payloads.

See [Single-Image Release Readiness](docs/single-image-release-readiness.md) for the current blocker dispositions for Connector CLI redistribution, CCOM reference data redistribution, Grafana plugin pinning, and demo access-control posture.

## Troubleshooting

- If Portal cannot start discovery, confirm `MCEGOLD_CLI_PATH` points to a real local Connector CLI executable or DLL.
- If Connector calls fail, validate `CONNECTOR_CONFIG_PATH` and Data Services environment variables.
- If the database is missing, start Portal once and confirm `DISCOVERY_DATABASE_PATH`.
- If schema inspection reports an older database below version 17, create a new demo database; pre-release schema upgrades are not supported by the current Portal source.
- If Grafana panels are empty, confirm the datasource plugin, datasource path, and that Portal/Collector are writing to the same SQLite database.

## Licensing

This project is licensed under the MIT License. See [LICENSE](LICENSE).

Unless otherwise noted, MCEGold Discovery Portal source code is licensed under the MIT License. Third-party materials included with the project remain subject to their respective licenses and notices. See [Third-Party Notices](THIRD-PARTY-NOTICES.md), including the MIMOSA CCOM reference data and MCEGold Data Services Connector dependency notices.
