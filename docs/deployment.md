# Deployment Guide

[Back to README](../README.md)

This guide deploys the published MCEGold Discovery Portal single-image Docker release. The image contains:

- MCEGold Discovery Portal
- Publication Collector
- Connector CLI
- SQLite
- Grafana

The default ports are:

| Service | Host URL |
| --- | --- |
| Portal | `http://localhost:8000` |
| Grafana | `http://localhost:3000` |

The default persistent container paths are:

| Container path | Named volume | Contains |
| --- | --- | --- |
| `/config` | `mcegold-config` | local configuration for the Portal, Connector, Collector, and Grafana-related settings |
| `/data` | `mcegold-data` | SQLite discovery database and Grafana data |

Deleting or replacing the container does not delete these named volumes. The data remains until the volumes are removed.

## Linux Docker Engine

Run these commands in Bash from the directory containing the downloaded image archive.

### 1. Verify Docker

```bash
docker --version
docker info
```

Expected result: Docker reports a version and server information.

### 2. Load the Downloaded Image Archive

Replace the archive name with the file supplied by the release.

```bash
docker load -i ./mcegold-discovery-image.tar
```

Expected result: Docker prints the loaded image name and tag, for example:

```text
Loaded image: mcegold-discovery:1.0.0
```

### 3. Verify the Image

Use the exact image name and tag printed by `docker load`.

```bash
docker image ls
```

Find the repository and tag printed by `docker load`, then use that exact value in the `IMAGE` variable:

```bash
IMAGE="mcegold-discovery:1.0.0"
```

### 4. Create Named Volumes

```bash
docker volume create mcegold-config
docker volume create mcegold-data
```

Expected result: Docker prints each volume name.

### 5. Run the Container

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

Expected result: Docker prints a container ID.

### 6. Verify Container Status

```bash
docker ps
```

Expected result: `mcegold-discovery` is running and ports `8000` and `3000` are listed.

For all containers, including stopped containers:

```bash
docker ps -a
```

### 7. Open the Portal

Open:

```text
http://localhost:8000
```

### 8. Open Grafana

Open:

```text
http://localhost:3000
```

Grafana may take longer than the Portal to become ready on first startup.

## Windows Docker Desktop

Docker Desktop must be running and set to Linux containers.

Run these commands in PowerShell.

### 1. Verify Docker Desktop / Docker Engine

```powershell
docker --version
docker info
```

Expected result: Docker reports a version and server information. If `docker info` cannot connect, start Docker Desktop and confirm it is using Linux containers.

### 2. Change to the Folder Containing the Downloaded Archive

```powershell
Set-Location C:\Path\To\Downloaded\Release
```

### 3. Load the Image

Replace the archive name with the file supplied by the release.

```powershell
docker load -i .\mcegold-discovery-image.tar
```

Expected result: Docker prints the loaded image name and tag, for example:

```text
Loaded image: mcegold-discovery:1.0.0
```

### 4. Verify the Image

```powershell
docker image ls
```

Find the repository and tag printed by `docker load`, then use that exact value in `$Image`:

```powershell
$Image = "mcegold-discovery:1.0.0"
```

### 5. Create Named Volumes

```powershell
docker volume create mcegold-config
docker volume create mcegold-data
```

Expected result: Docker prints each volume name.

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

Expected result: Docker prints a container ID.

### 7. Verify Container Status

```powershell
docker ps
```

Expected result: `mcegold-discovery` is running and ports `8000` and `3000` are listed.

For all containers, including stopped containers:

```powershell
docker ps -a
```

### 8. Open the Portal

```powershell
Start-Process "http://localhost:8000"
```

### 9. Open Grafana

```powershell
Start-Process "http://localhost:3000"
```

Grafana may take longer than the Portal to become ready on first startup.

## First-Time Setup

After the container is running:

1. Open the Portal at `http://localhost:8000`.
2. Open **Settings**.
3. Configure the MCEGold Data Services connection.
4. Save settings.
5. Start the first discovery.
6. Verify discovery results in the guided workflow.
7. Open Grafana at `http://localhost:3000`.

The published single-image deployment already includes the Connector CLI. Users do not need to install it manually.

## Container Management

Linux Bash:

```bash
docker ps
docker stop mcegold-discovery
docker start mcegold-discovery
docker restart mcegold-discovery
docker logs mcegold-discovery
docker logs -f mcegold-discovery
```

Windows PowerShell:

```powershell
docker ps
docker stop mcegold-discovery
docker start mcegold-discovery
docker restart mcegold-discovery
docker logs mcegold-discovery
docker logs -f mcegold-discovery
```

## Upgrade

Do not delete volumes during a normal upgrade.

Linux Bash:

```bash
docker stop mcegold-discovery
docker rm mcegold-discovery
docker load -i ./mcegold-discovery-newer-image.tar
IMAGE="<new-loaded-image-name>:<new-loaded-tag>"
docker run -d \
  --name mcegold-discovery \
  --restart unless-stopped \
  -p 8000:8000 \
  -p 3000:3000 \
  -v mcegold-config:/config \
  -v mcegold-data:/data \
  "$IMAGE"
```

Windows PowerShell:

```powershell
docker stop mcegold-discovery
docker rm mcegold-discovery
docker load -i .\mcegold-discovery-newer-image.tar
$Image = "<new-loaded-image-name>:<new-loaded-tag>"
docker run -d `
  --name mcegold-discovery `
  --restart unless-stopped `
  -p 8000:8000 `
  -p 3000:3000 `
  -v mcegold-config:/config `
  -v mcegold-data:/data `
  $Image
```

Use the exact newer image tag printed by `docker load`.

## Clean Reset

This procedure is destructive. It deletes local configuration, the SQLite discovery database, and Grafana data.

Linux Bash:

```bash
docker stop mcegold-discovery
docker rm mcegold-discovery
docker volume rm mcegold-config
docker volume rm mcegold-data
```

Windows PowerShell:

```powershell
docker stop mcegold-discovery
docker rm mcegold-discovery
docker volume rm mcegold-config
docker volume rm mcegold-data
```

After a clean reset, recreate the volumes and run the container again.

## Troubleshooting

Useful first checks:

```text
docker ps -a
docker logs mcegold-discovery
```

For more help, see [Troubleshooting](troubleshooting.md).
