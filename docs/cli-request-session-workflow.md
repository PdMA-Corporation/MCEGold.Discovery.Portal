# CLI request-session workflow

## Purpose

The Discovery Portal uses a request-session lifecycle through the local MCEGold Connector CLI. The portal does not implement connector authentication itself; credentials and ISBM connection settings remain in `configs/connector.config.json`, and the CLI performs all ISBM operations.

Sites, Segments, Measurement Locations, and Measurements are CLI-backed in this phase.

## Start Discovery flow

The Home page `Start Discovery` button posts to:

```text
POST /discovery/start
```

The portal stores the request session id returned by the CLI in FastAPI application state and mirrors it into the current browser session. One Portal process owns one shared Discovery request session; repeated Start Discovery requests reuse the active shared session instead of opening another Connector session.

In CLI mode, the portal executes:

```text
MCEGold.Data.Services.Connector.Cli.exe request open-session --config configs/connector.config.json --output json
```

For DLL deployments:

```text
dotnet MCEGold.Data.Services.Connector.Cli.dll request open-session --config configs/connector.config.json --output json
```

The portal extracts the request session id from fields such as `data.sessionId`, `data.requestSessionId`, `data.id`, or equivalent PascalCase fields.

## Sites / GetSites flow

The Sites page requires an active portal discovery session. In CLI mode it:

1. Creates a temporary `GetSites` short-form payload.
2. Posts the request with the active request session id.
3. Reads the response using the returned request message id.
4. Maps returned Site records into the portal `Site` model.

Commands:

```text
request post --config <config> --session-id <sessionId> --type get-sites --input <temp-payload.json> --output json
request read-response --config <config> --session-id <sessionId> --request-id <requestMessageId> --output json
```

## End Discovery flow

Discovery pages include an `End Discovery` button that posts to:

```text
POST /discovery/end
```

In CLI mode, if a request session id exists, the portal executes:

```text
request close-session --config <config> --session-id <sessionId> --output json
```

The portal clears its web session even if remote close reports an error, then redirects home with a non-blocking warning.

## Web session data

The portal stores only non-sensitive values in FastAPI application state and mirrors them into the Starlette session cookie for the current browser workflow:

- `discovery_session_id`
- `discovery_started_at`

It does not store passwords, API keys, connector config contents, or raw responses.

This first-release shared session is process-local. It is not coordinated across multiple uvicorn workers, multiple Portal processes, multiple container replicas, or Portal restarts.

Set `SESSION_SECRET_KEY` in local CLI mode:

```powershell
$env:SESSION_SECRET_KEY="change-this-for-local-testing"
```

## Error handling

The CLI client handles:

- `success=false`
- fault objects
- missing `success`
- invalid JSON
- empty stdout
- non-zero exit code
- timeouts

The UI shows friendly Bootstrap alerts and redacts sensitive values.

## Security and redaction

The portal redacts:

- `password`
- `apiKey`
- `userName`
- `Authorization`
- Basic tokens
- Bearer tokens

Do not commit `configs/connector.config.json`.

## Troubleshooting

If Start Discovery fails in CLI mode:

1. Confirm `MCEGOLD_CLI_PATH` points to the built CLI `.exe` or `.dll`.
2. Confirm `CONNECTOR_CONFIG_PATH` points to a real local config.
3. Run the CLI `config validate` command manually.
4. Confirm ISBM host, credentials, request channel, and response channel.
5. Increase `MCEGOLD_CLI_TIMEOUT_SECONDS` if responses are slow.
