# CLI-backed GetSites integration

## Purpose

The Discovery Portal can retrieve real Sites by invoking `MCEGold.Data.Services.Connector.Cli` from Python. This keeps deployment simple: the portal remains a FastAPI app, the Connector CLI owns ISBM communication, and no extra service or database is introduced.

Sites, Segments, Measurement Locations, and Measurements are CLI-backed through the staged request-session workflow.

## Configuration

Set these environment variables before starting the portal:

```powershell
$env:MCEGOLD_CLI_PATH="F:\path\to\MCEGold.Data.Services.Connector.Cli.exe"
$env:CONNECTOR_CONFIG_PATH="configs\connector.config.json"
python run.py
```

For DLL builds:

```powershell
$env:MCEGOLD_CLI_PATH="F:\path\to\MCEGold.Data.Services.Connector.Cli.dll"
```

Optional settings:

- `MCEGOLD_CLI_TIMEOUT_SECONDS`, default `60`
- `MCEGOLD_CLI_GET_SITES_MAX_ITEMS`, default `100`
- `MCEGOLD_CLI_INCLUDE_RAW`, default `false`

Do not commit `configs/connector.config.json`.

## Commands used

The portal uses the Connector CLI staged request-session workflow:

```text
request open-session --config <connector-config.json> --output json
request post --config <connector-config.json> --session-id <sessionId> --type get-sites --input <temp-payload.json> --output json
request read-response --config <connector-config.json> --session-id <sessionId> --request-id <requestMessageId> --output json
request close-session --config <connector-config.json> --session-id <sessionId> --output json
```

If `MCEGOLD_CLI_PATH` ends with `.dll`, the portal executes:

```text
dotnet <dll-path> request open-session ...
```

Otherwise it executes the configured executable path directly.

## Payload

The portal creates a temporary short-form request payload:

```json
{
  "requestType": "GetSites",
  "maxItems": 100,
  "filters": {}
}
```

`maxItems` comes from `MCEGOLD_CLI_GET_SITES_MAX_ITEMS`.

## Response parsing

The CLI returns a JSON envelope. The portal checks:

- process exit code
- `success`
- `fault`
- valid JSON stdout
- empty stdout
- timeout

Site records are defensively discovered under common response paths including:

- `data.sites`
- `data.Sites`
- `data.Site`
- `data.payload.DataArea.Show.Site`
- `data.payload.DataArea.Show.Sites.Site`
- `data.DataArea.Show.Site`
- `raw` when raw data is enabled or no parsed data is found

The portal maps common fields such as `UUID`, `SiteUUID`, `Name`, `ShortName`, `FullName`, `Description`, `Type`, `Status`, and `Region` into the existing `Site` model.

## Error handling

The Sites page does not crash on CLI failure. It shows a compact Bootstrap warning with:

- Connector Mode: CLI
- friendly message
- redacted command attempted
- exit code
- timeout
- short stderr
- fault code/message

Credentials and sensitive values such as passwords, API keys, usernames, Authorization headers, and Basic tokens are redacted.

## Troubleshooting

If CLI mode shows an error:

1. Confirm `MCEGOLD_CLI_PATH` points to the built `.exe` or `.dll`.
2. Confirm `CONNECTOR_CONFIG_PATH` points to a local config file.
3. Run `config validate` with the same CLI and config.
4. Check ISBM host/network reachability and credentials.
5. Increase `MCEGOLD_CLI_TIMEOUT_SECONDS` if the request channel is slow.

Use `MCEGOLD_CLI_INCLUDE_RAW=true` only for troubleshooting. Raw responses may be large or sensitive.
