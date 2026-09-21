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
- Optional: Grafana with the `frser-sqlite-datasource` plugin.
- Optional: Docker, if you want to build a Portal container image.

The Connector CLI binary bundle is not included in this public-release candidate. Configure `MCEGOLD_CLI_PATH` or `configs/portal.local.json` to point to a local Connector CLI installation. A verified public distribution path for that CLI must be documented separately when available.

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

The XML file is required to initialize an unseeded database unless `REFERENCE_DATA_PATH` is pointed at another valid copy. Repository content does not establish final public redistribution rights for this XML file. Treat redistribution approval as a public-release checklist item.

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

- `grafana/MCEGold Operations.json`
- `grafana/provisioning/datasources/sqlite.yaml`
- `grafana/provisioning/dashboards/dashboards.yaml`

The datasource provisioning expects the `frser-sqlite-datasource` plugin and a SQLite database at:

```text
/data/discovery_portal.db
```

For local non-container use, adjust the datasource path to the same database initialized by Portal.

## Docker Status

The Dockerfile builds a Python Portal image and keeps the same container path conventions used by the broader demo environment. It no longer copies a committed Connector CLI binary bundle.

A full runtime container still requires an externally provided Connector CLI at the configured `MCEGOLD_CLI_PATH`. Until a public Connector CLI distribution path is verified, full Docker runtime behavior is blocked by that external prerequisite.

The combined Portal + PublicationCollector + Grafana compose stack is expected to live with the broader deployment/demo materials, not in this Portal repository unless added intentionally later.

## Tests

Run the local test suite with:

```text
pytest
```

Tests are designed to use local/temp resources and mocked CLI behavior where appropriate. Do not convert unit tests into live integration tests that require internal services or real credentials.

## Security Notes

This is a local/reference/demo application. It does not provide a complete authentication or production authorization layer.

`SESSION_SECRET_KEY` signs session data; it is not user authentication. Do not expose the Settings/admin UI on an untrusted network without adding appropriate security controls.

`adminControlsEnabled` can hide Settings and selected administrative controls, but it is not a replacement for authentication or network access control.

Keep credentials in ignored local config files or environment variables. Do not commit real credentials, connector configs, local SQLite databases, or captured live payloads.

## Troubleshooting

- If Portal cannot start discovery, confirm `MCEGOLD_CLI_PATH` points to a real local Connector CLI executable or DLL.
- If Connector calls fail, validate `CONNECTOR_CONFIG_PATH` and Data Services environment variables.
- If the database is missing, start Portal once and confirm `DISCOVERY_DATABASE_PATH`.
- If schema inspection reports an older database below version 17, create a new demo database; pre-release schema upgrades are not supported by the current Portal source.
- If Grafana panels are empty, confirm the datasource plugin, datasource path, and that Portal/Collector are writing to the same SQLite database.

## Licensing

No authoritative public license file is present in this release candidate. A license and any required third-party/reference-data notices must be resolved before public release.
