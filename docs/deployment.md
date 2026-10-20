# Deployment Guide

[Back to README](../README.md)

This guide deploys the published MCEGold Discovery Portal single-image Docker appliance. The image contains the Portal, Publication Collector, Connector CLI, SQLite discovery database, and Grafana.

Download the release archive from the GitHub Releases page. The v1.0.1 examples below use `mcegold-discovery-v1.0.1-linux-amd64.tar` and image tag `mcegold-discovery:1.0.1`. Substitute the supplied archive filename if it differs.

Default service ports:

| Service | Host URL |
| --- | --- |
| MCEGold Discovery Portal | `http://localhost:8000` |
| Grafana | `http://localhost:3000` |

Persistent volumes:

| Named volume | Container path | Contains |
| --- | --- | --- |
| `mcegold-config` | `/config` | Appliance configuration for the Portal, Connector CLI, and Publication Collector |
| `mcegold-data` | `/data` | SQLite discovery database and persistent runtime data, including Grafana data |

Deleting or replacing the container does not delete these named volumes. Normal upgrades should reuse them.

## Linux Docker Engine

Run these commands in Bash from a Linux host with Docker Engine installed.

### 1. Verify Docker

```bash
docker --version
docker info
```

Docker should report both client and server information.

### 2. Change to the Archive Directory

```bash
cd /path/to/downloaded/release
```

### 3. Load the Image

Replace the archive name with the file supplied by the release.

```bash
docker load -i ./mcegold-discovery-v1.0.1-linux-amd64.tar
```

Expected output includes a loaded image tag, for example:

```text
Loaded image: mcegold-discovery:1.0.1
```

### 4. Verify the Image and Set a Variable

```bash
docker image ls mcegold-discovery
IMAGE="mcegold-discovery:1.0.1"
```

Use the exact image tag printed by `docker load`; for v1.0.1, `mcegold-discovery:1.0.1`.

### 5. Create Named Volumes

```bash
docker volume create mcegold-config
docker volume create mcegold-data
```

### 6. Run the Container

```bash
docker run -d \
  --name mcegold-discovery \
  --restart unless-stopped \
  -p 8000:8000 \
  -p 3000:3000 \
  -v mcegold-config:/config \
  -v mcegold-data:/data \
  "$IMAGE"
```

This publishes the Portal on port `8000`, publishes Grafana on port `3000`, and mounts the persistent volumes at `/config` and `/data`.

### 7. Check Container Status

```bash
docker ps
docker ps -a
```

The `mcegold-discovery` container should be running.

### 8. Check Health

```bash
docker inspect --format '{{.State.Health.Status}}' mcegold-discovery
```

The health status should become `healthy` after the Portal starts. First startup may take longer while the SQLite discovery database is initialized.

### 9. View Logs

```bash
docker logs mcegold-discovery
docker logs -f mcegold-discovery
```

### 10. Open the Portal

Open:

```text
http://localhost:8000
```

If connecting from another machine, use the Linux Docker host address instead of `localhost`.

### 11. Open Grafana

Open:

```text
http://localhost:3000
```

Grafana may take longer than the Portal to become ready.

### 12. Stop, Start, or Restart

```bash
docker stop mcegold-discovery
docker start mcegold-discovery
docker restart mcegold-discovery
```

### 13. Upgrade While Preserving Data

Do not remove `mcegold-config` or `mcegold-data` during a normal upgrade.

```bash
docker stop mcegold-discovery
docker rm mcegold-discovery
docker load -i ./mcegold-discovery-v1.0.1-linux-amd64.tar
docker image ls mcegold-discovery
IMAGE="mcegold-discovery:1.0.1"
docker run -d \
  --name mcegold-discovery \
  --restart unless-stopped \
  -p 8000:8000 \
  -p 3000:3000 \
  -v mcegold-config:/config \
  -v mcegold-data:/data \
  "$IMAGE"
```

### 14. Clean Reset

Warning: this deletes local configuration, the local SQLite discovery database, and persistent Grafana/runtime state stored in the named volumes.

```bash
docker stop mcegold-discovery
docker rm mcegold-discovery
docker volume rm mcegold-config
docker volume rm mcegold-data
```

After a clean reset, recreate the volumes and run the container again.

## Windows Docker Desktop

Docker Desktop must be running Linux containers. These steps use PowerShell only. WSL is not required as an end-user deployment step by this repository.

### 1. Verify Docker Desktop / Docker Engine

```powershell
docker --version
docker info
```

If `docker info` cannot connect, start Docker Desktop and confirm it is using Linux containers.

### 2. Change to the Downloaded Archive Folder

```powershell
Set-Location C:\Path\To\Downloaded\Release
```

### 3. Load the Image

Replace the archive name with the file supplied by the release.

```powershell
docker load -i .\mcegold-discovery-v1.0.1-linux-amd64.tar
```

Expected output includes a loaded image tag, for example:

```text
Loaded image: mcegold-discovery:1.0.1
```

### 4. Verify the Image and Set a Variable

```powershell
docker image ls mcegold-discovery
$Image = "mcegold-discovery:1.0.1"
```

Use the exact image tag printed by `docker load`; for v1.0.1, `mcegold-discovery:1.0.1`.

### 5. Create Named Volumes

```powershell
docker volume create mcegold-config
docker volume create mcegold-data
```

### 6. Run the Container

```powershell
docker run -d `
  --name mcegold-discovery `
  --restart unless-stopped `
  -p 8000:8000 `
  -p 3000:3000 `
  -v mcegold-config:/config `
  -v mcegold-data:/data `
  $Image
```

This publishes the Portal on port `8000`, publishes Grafana on port `3000`, and mounts the persistent volumes at `/config` and `/data`.

### 7. Check Status

```powershell
docker ps
docker ps -a
```

The `mcegold-discovery` container should be running.

### 8. Check Health

```powershell
docker inspect --format '{{.State.Health.Status}}' mcegold-discovery
```

The health status should become `healthy` after the Portal starts. First startup may take longer while the SQLite discovery database is initialized.

### 9. View Logs

```powershell
docker logs mcegold-discovery
docker logs -f mcegold-discovery
```

### 10. Open the Portal

```powershell
Start-Process "http://localhost:8000"
```

If connecting from another machine, use the Windows Docker host name or IP address instead of `localhost`.

### 11. Open Grafana

```powershell
Start-Process "http://localhost:3000"
```

Grafana may take longer than the Portal to become ready.

### 12. Stop, Start, or Restart

```powershell
docker stop mcegold-discovery
docker start mcegold-discovery
docker restart mcegold-discovery
```

### 13. Upgrade While Preserving Data

Do not remove `mcegold-config` or `mcegold-data` during a normal upgrade.

```powershell
docker stop mcegold-discovery
docker rm mcegold-discovery
docker load -i .\mcegold-discovery-v1.0.1-linux-amd64.tar
docker image ls mcegold-discovery
$Image = "mcegold-discovery:1.0.1"
docker run -d `
  --name mcegold-discovery `
  --restart unless-stopped `
  -p 8000:8000 `
  -p 3000:3000 `
  -v mcegold-config:/config `
  -v mcegold-data:/data `
  $Image
```

### 14. Clean Reset

Warning: this deletes local configuration, the local SQLite discovery database, and persistent Grafana/runtime state stored in the named volumes.

```powershell
docker stop mcegold-discovery
docker rm mcegold-discovery
docker volume rm mcegold-config
docker volume rm mcegold-data
```

After a clean reset, recreate the volumes and run the container again.

## First-Time Setup

After the container is running:

1. Open the Portal at `http://localhost:8000`.
2. Open **Settings**.
3. Configure the MCEGold Data Services URL and credentials.
4. Save settings.
5. Start the first top-down discovery.
6. Follow Site -> Segment -> Measurement Location -> Measurements.
7. Open Grafana at `http://localhost:3000`.

The published single-image appliance already includes the Connector CLI.

## Persistence and Upgrades

`mcegold-config` stores appliance configuration under `/config`.

`mcegold-data` stores the SQLite discovery database and persistent runtime data under `/data`.

Removing or replacing the container does not remove these volumes. Normal upgrades preserve data by reusing both volumes with the newer image. A clean reset intentionally removes both volumes and discards the saved state.

The combined v1.0.1 image enables Shared Request Session mode in newly seeded Collector configuration. An existing `/config/collector.local.json` is preserved and may need `"useSharedRequestSession": true` added or updated explicitly. Alternatively, supply `-e MCEGOLD_USE_SHARED_REQUEST_SESSION=true` when creating the container; this environment variable overrides the file value. Restart the container after editing the file. See [Publication Collector Settings](configuration.md#publication-collector-settings).

The Portal and Collector must use the same live SQLite database, normally `/data/discovery_portal.db`. The Portal persists its Consumer Request Session ID and original start timestamp there and restores them on restart without automatically opening a replacement session. The remote session may no longer be valid; see [Request Session Management](troubleshooting.md#known-limitations--request-session-management). No SQLite schema migration is required from a supported v1.0.0 database.

## Troubleshooting

Useful first checks:

```text
docker ps -a
docker logs mcegold-discovery
```

For more help, see [Troubleshooting](troubleshooting.md).
