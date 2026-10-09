# Quick Start

[Back to README](../README.md)

This guide follows the standard single-image deployment path. The image includes MCEGold Discovery Portal, Publication Collector, Connector CLI, SQLite, and Grafana.

## Prerequisites

- Docker on Linux or Docker Desktop on Windows.
- Access to the published MCEGold Discovery release image.
- MCEGold Data Services connection details.
- Available local ports `8000` and `3000`.

## 1. Obtain the Release Image

Download the image archive or use the image reference published with the release. If the release provides an image archive, load it first:

```powershell
docker load -i .\mcegold-discovery-image.tar
```

Use the image name and tag from the release notes in the commands below. The examples use a placeholder:

```text
mcegold-discovery:<version>
```

## 2. Create Persistent Volumes

```powershell
docker volume create mcegold-discovery-config
docker volume create mcegold-discovery-data
```

The `/config` volume stores local configuration. The `/data` volume stores the SQLite discovery database and Grafana data.

## 3. Run the Container

```powershell
docker run --rm `
  --name mcegold-discovery `
  -p 8000:8000 `
  -p 3000:3000 `
  -v mcegold-discovery-config:/config `
  -v mcegold-discovery-data:/data `
  mcegold-discovery:<version>
```

For Linux shells:

```bash
docker run --rm \
  --name mcegold-discovery \
  -p 8000:8000 \
  -p 3000:3000 \
  -v mcegold-discovery-config:/config \
  -v mcegold-discovery-data:/data \
  mcegold-discovery:<version>
```

## 4. Open the Portal

Open:

```text
http://localhost:8000
```

The health endpoint is:

```text
http://localhost:8000/health
```

## 5. Configure MCEGold Data Services

Open **Settings** in the Portal and enter the values supplied for your MCEGold Data Services environment:

- Data Services URL
- username
- password
- API key, if used by your environment

Saving settings persists local configuration under `/config`.

## 6. Run Top-Down Discovery

Start discovery from the Portal and follow the guided path:

```text
Site -> Segment -> Measurement Location -> Measurements
```

A successful first run shows connector status as connected, lets you select discovered entities, and stores discovered data in the SQLite database under `/data`.

## 7. Enable or Check the Publication Collector

The Publication Collector runs inside the container. In Portal Settings, confirm whether collector processing is enabled and set the polling interval if needed.

When the Collector is running and configured, it processes incoming publications and updates runtime status and measurement data in SQLite.

## 8. Open Grafana

Open:

```text
http://localhost:3000
```

Grafana may take longer than the Portal to become ready on first startup. The default image configures Grafana to read from the SQLite database at `/data/discovery_portal.db`.

If you expose Grafana beyond a trusted local environment, set explicit Grafana credentials and follow the [Deployment Security Notes](security.md).
