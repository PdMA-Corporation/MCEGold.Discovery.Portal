# Troubleshooting

[Back to README](../README.md)

Use these checks for common deployment and runtime issues.

## Portal Does Not Start

- Check container logs with `docker logs mcegold-discovery`.
- Confirm port `8000` is not already in use on the host.
- Confirm the `/config` and `/data` mounts are writable.
- Check the health endpoint: `http://localhost:8000/health`.

## Container Health Check Fails

- Give the Portal time to initialize the SQLite database on first startup.
- Review logs for reference-data or database initialization errors.
- Confirm `/data` has enough space and is writable.

## Collector Does Not Start

- Review container logs for the collector process.
- Confirm the Portal database exists under `/data`.
- Confirm the `/config/collector.local.json` and `/config/connector.config.json` files exist.
- In the Portal Settings page, check collector status and whether collector processing is enabled.

## CLI Status Shows Error

- Confirm MCEGold Data Services URL and credentials are configured.
- Confirm the Connector config was saved from the Portal Settings page.
- In the default single-image deployment, the Connector CLI is already bundled at the configured container path.
- Review redacted error details shown in the Portal.

## Discovery Request Fails

- Confirm discovery was started before navigating deeper into the workflow.
- Confirm the selected Site, Segment, or Measurement Location still exists in the source system.
- Try a smaller result limit where available.
- Check container logs for timeout or connector errors.

## Publication Processing Fails

- Confirm collector processing is enabled.
- Confirm MCEGold Data Services connection settings are valid.
- Review collector runtime status in the Portal Settings page.
- Check container logs for publication channel, credential, or timeout errors.

## Grafana Is Not Ready Immediately

Grafana can take longer than the Portal to become available, especially on first startup. Wait briefly, then open:

```text
http://localhost:3000
```

If it still does not load, check `docker logs mcegold-discovery`.

## Grafana Dashboard Does Not Load

- Confirm port `3000` is exposed.
- Confirm Grafana is running in the container logs.
- Confirm `/data` is mounted and contains the SQLite database.
- Confirm the Portal's Grafana dashboard URL is correct for the host name users are using.

## Old Configuration or Data Appears

Docker volumes preserve state. Reusing the same `/config` and `/data` volumes preserves settings, database contents, and Grafana state.

Use a clean reset only when you intentionally want to discard that state.

## Clean Reset

Stop the container:

```powershell
docker stop mcegold-discovery
```

Remove the named volumes:

```powershell
docker volume rm mcegold-discovery-config
docker volume rm mcegold-discovery-data
```

Then recreate the volumes and run the container again. This deletes saved configuration, the SQLite database, and Grafana state.

## Persistent Volume Checks

List volumes:

```powershell
docker volume ls
```

Inspect a volume:

```powershell
docker volume inspect mcegold-discovery-data
```
