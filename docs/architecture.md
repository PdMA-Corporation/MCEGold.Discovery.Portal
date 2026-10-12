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

```text
MCEGold Data Services
        |
        v
Connector CLI
        |
        +----------------------+
        |                      |
        v                      v
Discovery Portal      Publication Collector
        |                      |
        +----------+-----------+
                   |
                   v
          SQLite discovery database
                   |
                   v
                Grafana
```

The Connector CLI is the public integration boundary used by the appliance to communicate with MCEGold Data Services. The Portal and Publication Collector both use the CLI, then persist local data in the shared SQLite discovery database. Grafana reads from that SQLite database through the provisioned SQLite datasource.

## Component Responsibilities

| Component | Responsibility |
| --- | --- |
| MCEGold Data Services | External source of discovery and publication data |
| Connector CLI | Command-line bridge used by the Portal and Publication Collector |
| MCEGold Discovery Portal | User-facing configuration, connector status, and guided top-down discovery workflow |
| Publication Collector | Background processor for incoming publication data |
| SQLite discovery database | Shared local persistence for application settings, discovered entities, runtime status, reference dimensions, and measurements |
| Grafana | Dashboard view over the local SQLite discovery database |

## Data Persistence

The default persistent paths are:

| Path | Purpose |
| --- | --- |
| `/config` | Local appliance configuration files |
| `/data` | SQLite discovery database and persistent runtime data |

The Portal initializes the SQLite discovery database when needed. The Publication Collector waits for the Portal-owned database schema to be ready before it starts processing. Grafana reads from the local SQLite database.

Fresh databases are created at the current supported schema. Older pre-release or incompatible databases are not automatically upgraded.

## Reference Data

The appliance includes `docs/CCOM Reference Data.xml`. On a new or unseeded database, the Portal uses this file to seed local reference dimensions for type labels and reporting metadata.

The reference-data seed supports discovery selectors and reporting context. It does not create demo Sites, Segments, Measurement Locations, or Measurement facts. Customer-specific data comes from discovery responses and publication processing.

The reference data remains third-party material. See [Third-Party Notices](../THIRD-PARTY-NOTICES.md).

## Grafana Dashboard

![MCEGold Grafana dashboard showing discovered measurements](images/MCEGold_Dashboard.png)

The bundled Grafana dashboard provides an operational view of local SQLite discovery data. Grafana is a dashboard surface; the SQLite discovery database is the local persistence layer.
