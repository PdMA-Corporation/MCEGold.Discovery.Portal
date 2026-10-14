# Quick Start

[Back to README](../README.md)

Use this guide for the shortest successful first run of the published MCEGold Discovery Portal appliance. For complete platform-specific commands, see the [Deployment Guide](deployment.md).

## Prerequisites

- Docker Engine on Linux, or Docker Desktop on Windows running Linux containers.
- The MCEGold Discovery Portal release archive from the GitHub Releases page.
- MCEGold Data Services connection details.
- Available host ports `8000` and `3000`.

## 1. Obtain the Release Image Archive

Download the release archive from the GitHub Releases page. The permanent archive URL and filename policy are not finalized, so use the archive supplied with the release you are installing.

Versioned examples in this documentation use placeholders such as:

```text
mcegold-discovery-<version>-linux-amd64.tar.gz
mcegold-discovery:<version>
```

Use the actual version from your release.

## 2. Load the Image

From the folder containing the downloaded archive, load the image:

```text
docker load -i <downloaded-release-archive>
```

Docker prints the loaded image name and tag. For example:

```text
Loaded image: mcegold-discovery:1.0.0
```

Use the exact image tag printed by `docker load`.

## 3. Verify the Image Tag

List local images and confirm the `mcegold-discovery` tag:

```text
docker image ls mcegold-discovery
```

Use an explicit version tag such as:

```text
mcegold-discovery:1.0.0
```

## 4. Create Persistent Volumes

Create the named volumes used by the beginner deployment:

```text
docker volume create mcegold-config
docker volume create mcegold-data
```

`mcegold-config` stores appliance configuration under `/config`. `mcegold-data` stores the SQLite discovery database and persistent runtime data under `/data`.

## 5. Run the Container

Run the image with:

- Portal exposed on `8000`
- Grafana exposed on `3000`
- `mcegold-config` mounted at `/config`
- `mcegold-data` mounted at `/data`

Copy-and-paste commands are available for [Linux Docker Engine](deployment.md#linux-docker-engine) and [Windows Docker Desktop](deployment.md#windows-docker-desktop).

## 6. Open the Portal

Open:

```text
http://localhost:8000
```

If you are connecting from another machine, use the Docker host name or IP address instead of `localhost`.

## 7. Configure MCEGold Data Services

In the Portal:

1. Open **Settings**.
2. Enter the MCEGold Data Services URL and credentials supplied for your environment.
3. Save settings.

The published single-image appliance already includes the Connector CLI.

## 8. Run the First Discovery

Start discovery and follow the guided path:

```text
Site -> Segment -> Measurement Location -> Measurements
```

Confirm that discovery results appear before moving deeper into the workflow.

## 9. Open Grafana

Open:

```text
http://localhost:3000
```

Grafana reads the local SQLite discovery database. It may take a little longer than the Portal to become ready on first startup.

## Next Steps

- For full Linux and Windows commands, see [Deployment Guide](deployment.md).
- For configuration details, see [Configuration Guide](configuration.md).
- For common problems, see [Troubleshooting](troubleshooting.md).
