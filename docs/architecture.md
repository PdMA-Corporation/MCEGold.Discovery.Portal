# Architecture

[Back to README](../README.md)

MCEGold Discovery Portal is packaged as a local discovery and dashboard appliance for MCEGold Data Services workflows.

## Single-Image Appliance

The default deployment is a single Docker image containing:

- MCEGold Discovery Portal.
- Publication Collector.
- Bundled Connector CLI.
- SQLite discovery database.
- Grafana.

The appliance is intended for demos, evaluation, and integration planning. It is not a replacement for customer access-control, network, backup, or production operations standards.

## High-Level Flow

![MCEGold Discovery Portal single-container system architecture](images/MCEGold%20Discovery%20Portal%20Architecture%20Diagram.png)

The Connector CLI is the public integration boundary used by the appliance to communicate with MCEGold Data Services. The Portal and Publication Collector invoke the bundled CLI independently. The Portal owns and manages its Consumer Request Session. With Shared Request Session mode enabled, the Collector reads the session information from the same live SQLite database and reuses it for reference enrichment without opening or closing the Portal-owned session. The Collector does not call the Portal's discovery API; shared enrichment requires an available Portal-managed session, while publication processing uses separate Publication sessions. See [Discovery Workflows](workflows.md).

The Portal provides the Web UI and API on port `8000`, performs guided discovery, and reads and writes local discovery data. The Publication Collector receives measurement publications and writes collected measurements, discovered reference context, and runtime status directly to the shared SQLite database. Grafana serves dashboards on port `3000` and reads that database through the provisioned SQLite datasource.

## Component Responsibilities

| Component | Responsibility |
| --- | --- |
| MCEGold Data Services | External source of discovery and publication data |
| Connector CLI | Command-line bridge used by the Portal and Publication Collector |
| MCEGold Discovery Portal | Web UI and API for configuration, connector status, guided top-down discovery, and local discovery data access |
| Publication Collector | Background processor for incoming measurement publications and targeted reference-data enrichment |
| SQLite discovery database | Shared local persistence for application settings, discovered entities, runtime status, reference dimensions, and measurements |
| Grafana | Dashboard view over the local SQLite discovery database |

## Data Persistence

The default persistent paths are:

| Path | Purpose |
| --- | --- |
| `/config` | Local appliance configuration files |
| `/data` | SQLite discovery database and persistent runtime data |

The diagram shows both persistent directories conceptually. `/config` supplies configuration to the appliance components; it does not store the SQLite database. `/data` contains `discovery_portal.db` and Grafana runtime data.

The Portal initializes the SQLite discovery database when needed. The Publication Collector waits for the Portal-owned database schema to be ready before it starts processing, then writes directly to that database. Grafana reads from the local SQLite database.

The Portal persists its Consumer Request Session ID and original start timestamp in SQLite. Retaining `/data` allows the Portal to restore that information after application or container restart without automatically opening a replacement session. The restored remote session may no longer be valid. This v1.0.1 capability uses the existing supported SQLite schema and requires no schema migration from v1.0.0.

Fresh databases are created at the current supported schema. Older pre-release or incompatible databases are not automatically upgraded.

## Reference Data

The appliance includes `docs/CCOM Reference Data.xml`. On a new or unseeded database, the Portal uses this file to seed local reference dimensions for type labels and reporting metadata.

The reference-data seed supports discovery selectors and reporting context. It does not create demo Sites, Segments, Measurement Locations, or Measurement facts. Customer-specific data comes from discovery responses and publication processing.

The reference data remains third-party material. See [Third-Party Notices](../THIRD-PARTY-NOTICES.md).

## Grafana Dashboard

The bundled Grafana dashboard provides an operational view of local SQLite discovery data. Grafana is a dashboard surface; the SQLite discovery database is the local persistence layer.
