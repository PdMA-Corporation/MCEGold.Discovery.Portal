# Quick Start

[Back to README](../README.md)

Use this guide for the standard published single-image deployment. The image includes MCEGold Discovery Portal, Publication Collector, Connector CLI, SQLite, and Grafana.

For complete platform-specific commands, see the [Deployment Guide](deployment.md).

## Prerequisites

- Docker Engine on Linux, or Docker Desktop on Windows running Linux containers.
- The downloaded MCEGold Discovery image archive from the release.
- MCEGold Data Services connection details.
- Available host ports `8000` and `3000`.

## 1. Load the Image

Load the image archive supplied with the release:

```text
docker load -i <downloaded-image-archive>.tar
```

Use the image name and tag printed by `docker load`. For example, if Docker prints:

```text
Loaded image: mcegold-discovery:1.0.0
```

then use:

```text
mcegold-discovery:1.0.0
```

in the run command.

## 2. Create Persistent Volumes

The beginner deployment uses Docker named volumes:

```text
mcegold-config
mcegold-data
```

`mcegold-config` stores local configuration. `mcegold-data` stores the SQLite discovery database and Grafana data.

## 3. Run the Container

Run the image with:

- Portal exposed on `8000`
- Grafana exposed on `3000`
- `/config` persisted to `mcegold-config`
- `/data` persisted to `mcegold-data`

Detailed copy-and-paste commands are available for [Linux Docker Engine](deployment.md#linux-docker-engine) and [Windows Docker Desktop](deployment.md#windows-docker-desktop).

## 4. First-Time Setup

1. Open the Portal: `http://localhost:8000`
2. Open **Settings**.
3. Configure the MCEGold Data Services connection.
4. Save settings.
5. Start discovery.
6. Select Site -> Segment -> Measurement Location -> Measurements.
7. Confirm discovery results are shown.
8. Open Grafana: `http://localhost:3000`

You do not need to manually install the Connector CLI when using the published single-image deployment.

## Expected Result

After setup:

- the Portal opens on port `8000`;
- connector status can be verified from the Portal;
- discovery results can be selected in the guided workflow;
- the Publication Collector runs inside the container;
- Grafana opens on port `3000` and reads from the local SQLite database.

For errors, see [Troubleshooting](troubleshooting.md).
