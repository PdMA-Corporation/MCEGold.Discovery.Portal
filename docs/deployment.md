# Deployment Guide

[Back to README](../README.md)

The recommended deployment path is the published single-image Docker release. It runs the Portal, Publication Collector, Connector CLI, SQLite, and Grafana in one container.

## Ports

Expose these ports from the container:

| Service | Container port | Typical local URL |
| --- | ---: | --- |
| Portal | `8000` | `http://localhost:8000` |
| Grafana | `3000` | `http://localhost:3000` |

## Persistent Locations

Mount persistent storage for:

| Path | Purpose |
| --- | --- |
| `/config` | Portal, Connector, Collector, and Grafana-related local configuration |
| `/data` | SQLite discovery database and Grafana data |

Reusing the same volumes preserves configuration, discovered data, collector status, and Grafana state across restarts.

## Linux Docker

```bash
docker volume create mcegold-discovery-config
docker volume create mcegold-discovery-data

docker run --rm \
  --name mcegold-discovery \
  -p 8000:8000 \
  -p 3000:3000 \
  -v mcegold-discovery-config:/config \
  -v mcegold-discovery-data:/data \
  mcegold-discovery:<version>
```

## Docker Desktop on Windows

PowerShell example:

```powershell
docker volume create mcegold-discovery-config
docker volume create mcegold-discovery-data

docker run --rm `
  --name mcegold-discovery `
  -p 8000:8000 `
  -p 3000:3000 `
  -v mcegold-discovery-config:/config `
  -v mcegold-discovery-data:/data `
  mcegold-discovery:<version>
```

Use the image name and tag published with the release.

## Restart Behavior

Stop the container:

```powershell
docker stop mcegold-discovery
```

Start it again with the same volume mounts to reuse existing settings and data. If the container was started with `--rm`, the container object is removed after it stops, but the named volumes remain.

## Updating the Image

1. Stop the running container.
2. Load or pull the newer image version.
3. Run the new image with the same `/config` and `/data` volumes.
4. Confirm the Portal opens and Grafana dashboards load.

Preserve `/config` and `/data` unless you intentionally want a fresh deployment.

## Clean Reset

To start from empty configuration and data, stop the container and use new volumes or remove the old volumes:

```powershell
docker volume rm mcegold-discovery-config
docker volume rm mcegold-discovery-data
```

Removing these volumes deletes saved settings, the SQLite database, and Grafana state.

## Logs and Health

View container logs:

```powershell
docker logs mcegold-discovery
```

Follow logs:

```powershell
docker logs -f mcegold-discovery
```

Check the Portal health endpoint:

```text
http://localhost:8000/health
```

## Network Exposure

Bind Portal and Grafana only where intended. For shared or production-style environments, place access behind trusted network controls, TLS termination, and an approved reverse proxy or identity layer.

See [Deployment Security Notes](security.md).
