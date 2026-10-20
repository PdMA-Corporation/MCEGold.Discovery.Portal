# Troubleshooting

[Back to README](../README.md)

Use these checks for common deployment and runtime issues.

## Container Does Not Start

- Check container status:

  ```text
  docker ps -a
  ```

- Review logs:

  ```text
  docker logs mcegold-discovery
  ```

- Confirm host ports `8000` and `3000` are available.
- Confirm the `mcegold-config` and `mcegold-data` volumes exist.
- Confirm the mounted `/config` and `/data` paths are writable inside the container.

## Container Is Unhealthy

- Give the Portal time to initialize the SQLite discovery database on first startup.
- Check the health endpoint from the Docker host:

  ```text
  http://localhost:8000/health
  ```

- Review logs for database initialization, reference-data, or permission errors.
- Confirm `/data` has enough space and is writable.

## Portal Is Unavailable

- Confirm the container is running:

  ```text
  docker ps
  ```

- Confirm port `8000` is published as `8000:8000`.
- Open `http://localhost:8000` from the Docker host.
- If connecting from another machine, use the Docker host name or IP address instead of `localhost`.

## Configuration or Data Path Is Not Writable

The appliance expects:

| Named volume | Container path |
| --- | --- |
| `mcegold-config` | `/config` |
| `mcegold-data` | `/data` |

Inspect the volumes:

```text
docker volume inspect mcegold-config
docker volume inspect mcegold-data
```

If you intentionally want to discard all local state, use the clean reset procedure below.

## CLI Missing or Configuration Problem

- In the default single-image appliance, the Connector CLI is bundled and configured at the container path.
- Confirm MCEGold Data Services settings were saved from the Portal Settings page.
- Confirm `/config/connector.config.json` exists.
- Review redacted connector error details shown in the Portal.
- Check logs for timeout or Connector CLI execution errors.

## Invalid MCEGold Data Services URL or Credentials

- Confirm the MCEGold Data Services URL is correct for your environment.
- Confirm username, password, and API key values are current.
- Save settings again from the Portal.
- Avoid pasting credentials into public issues, logs, or documentation.

## Discovery Request Fails

- Confirm discovery was started before navigating deeper into the workflow.
- Confirm the selected Site, Segment, or Measurement Location still exists in MCEGold Data Services.
- Try a smaller result limit where available.
- Check container logs for timeout or connector errors.

## Known Limitations — Request Session Management

MCEGold Discovery Portal v1.0.1 owns and manages one application-wide Consumer Request Session. Multiple browser users share this Request Session, while each browser keeps its own selected Site, Segment, and Measurement Location context. Start Discovery opens a session when none is saved; otherwise it reuses the saved session without first validating it against MCEGold Data Services.

The Portal persists the Session ID and original start timestamp in SQLite. After a Portal or container restart with the same database, it restores that information without automatically opening a replacement session. Restoration does not guarantee remote validity, and restart does not clear an invalid saved session.

Discovery responses confirming that a session is closed or missing cause the Portal to clear the saved session state. Connectivity failures, including timeouts, do not automatically invalidate it. Automatic recovery is limited: the Segments search can open a replacement session and retry once. Other discovery paths can clear an invalid session and require **Start Discovery** again; universal automatic retry is not provided.

When `adminControlsEnabled` is `true`, **End Discovery** attempts to close the remote session and clears the persisted and local session state even if the Connector reports a remote-close failure. If saving the cleared state fails, the Portal reports an error and retains the saved state; resolve the database access problem and retry. For manual recovery:

1. Select **End Discovery**.
2. Return to the home page.
3. Select **Start Discovery** to open a new Request session.

When `adminControlsEnabled` is `false`, End Discovery is unavailable. After a discovery request confirms invalidation and clears the saved state, use **Start Discovery** again. Restarting the Portal is not a session reset.

Changes saved through Portal Settings to effective Data Services connection values (URL or credentials), Connector configuration path, or CLI path invalidate the saved session state. Unrelated changes, such as the Grafana URL or Collector polling interval, do not. Start Discovery again after changing the connection.

The Collector uses separate Publication sessions for normal publication processing. With Shared Request Session mode enabled, it reads the Portal-managed session information from the same live SQLite database for reference enrichment and does not open or close that session. If none is available, enrichment is deferred. Check [Publication Collector Settings](configuration.md#publication-collector-settings), especially when upgrading with an existing Collector configuration file.

Simultaneous multi-user discovery has not been fully validated and is not a primary objective of this release. Because the Request Session is shared application-wide, ending or invalidating it can affect other browser users and Collector enrichment in shared mode.

## Publication Collector Offline, Disabled, or Error

- Open the Portal Settings page and review collector status.
- Confirm collector processing is enabled if you expect publication processing.
- Confirm the configured MCEGold Data Services connection is valid.
- Review logs for publication channel, credential, timeout, or database errors.

## Grafana Is Not Ready Immediately

Grafana can take longer than the Portal to become available, especially on first startup. Wait briefly, then open:

```text
http://localhost:3000
```

If it still does not load, check:

```text
docker logs mcegold-discovery
```

## Grafana Dashboard or Datasource Issue

- Confirm port `3000` is published as `3000:3000`.
- Confirm Grafana is running in the container logs.
- Confirm `/data` is mounted from `mcegold-data`.
- Confirm the SQLite discovery database exists at `/data/discovery_portal.db`.
- Confirm the Portal's Grafana dashboard URL is correct for the host name users are using.

## Stale Data or Old Configuration Appears

Docker named volumes preserve state. Reusing `mcegold-config` and `mcegold-data` preserves settings, database contents, and persistent runtime data even when the container is removed and recreated.

Use a clean reset only when you intentionally want to discard that state.

## Clean Reset

Warning: this deletes local configuration, local SQLite discovery data, and persistent Grafana/runtime state stored in the named volumes.

Stop and remove the container:

```text
docker stop mcegold-discovery
docker rm mcegold-discovery
```

Remove the named volumes:

```text
docker volume rm mcegold-config
docker volume rm mcegold-data
```

Then recreate the volumes and run the container again.

## Logs

Useful log commands:

```text
docker logs mcegold-discovery
docker logs -f mcegold-discovery
```

Review logs before sharing them publicly. They can include operational details such as endpoint names or environment-specific information.
