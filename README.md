# MCEGold Discovery Portal

MCEGold Discovery Portal is a deployable reference application for exploring MCEGold Data Services discovery workflows and viewing discovered measurement data with Grafana.

![MCEGold Discovery Portal guided discovery screen](docs/images/MCEGold_Portal.png)

## Overview

The Portal helps integrators and deployment administrators configure a local MCEGold discovery environment, run guided discovery, persist discovered data in SQLite, and inspect that data through a bundled Grafana dashboard.

The default deployment is a single Docker image intended for demos, evaluation, and integration planning. It includes the Portal UI, the Publication Collector, the Connector CLI, SQLite, and Grafana so users do not need to install the Connector CLI separately for the standard image-based path.

## Architecture at a Glance

```text
MCEGold Data Services
        |
        v
MCEGold Data Services Connector CLI
        |
        v
Portal / Publication Collector
        |
        v
SQLite discovery database
        |
        v
Grafana
```

The Portal and Publication Collector both use the Connector CLI to communicate with MCEGold Data Services. The Portal provides the user-facing configuration and top-down discovery workflow. The Publication Collector runs continuously and stores incoming publication data. SQLite is the shared local persistence layer, and Grafana reads from that SQLite data.

## Included Components

- **Discovery Portal**: web UI for configuration, connector status, and guided discovery.
- **Publication Collector**: background process that processes MCEGold publications and writes runtime data.
- **Connector CLI**: bundled command-line bridge to MCEGold Data Services in the default single-image deployment.
- **SQLite**: local discovery database stored under `/data`.
- **Grafana**: dashboard service on port `3000` for viewing discovered and collected data.

## Quick Start

The shortest path is to use the published release image.

1. Obtain the release image from the project's release artifacts.
2. Run the image with ports `8000` and `3000` exposed.
3. Persist `/config` and `/data` with Docker volumes.
4. Open the Portal at `http://localhost:8000`.
5. Configure MCEGold Data Services connection settings in the Portal.
6. Start discovery and follow Site -> Segment -> Measurement Location -> Measurements.
7. Open Grafana at `http://localhost:3000`.

See [Quick Start](docs/quick-start.md) for complete first-run instructions.

## Documentation

- [Quick Start](docs/quick-start.md)
- [Deployment Guide](docs/deployment.md)
- [Configuration Guide](docs/configuration.md)
- [Architecture](docs/architecture.md)
- [Discovery Workflows](docs/workflows.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Deployment Security Notes](docs/security.md)

## License and Third-Party Components

This project is licensed under the MIT License. See [LICENSE](LICENSE).

Third-party materials and bundled components remain subject to their own notices and licenses. See [Third-Party Notices](THIRD-PARTY-NOTICES.md).
