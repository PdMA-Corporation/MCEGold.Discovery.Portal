# Deployment Security Notes

[Back to README](../README.md)

These notes describe practical deployment precautions for the current MCEGold Discovery Portal release.

## Network Exposure

Do not expose the Portal or Grafana to untrusted networks unless they are protected by approved network controls. For shared or production-style deployments, use a trusted reverse proxy, TLS termination, VPN, identity provider, or equivalent access-control layer.

## Grafana Credentials

The single-image deployment runs Grafana on port `3000`. Before exposing Grafana beyond a trusted local or LAN environment, set explicit Grafana admin credentials or use an approved authentication mechanism.

The image supports Grafana's standard `GF_SECURITY_ADMIN_USER` and `GF_SECURITY_ADMIN_PASSWORD` environment variables.

## MCEGold Credentials and API Keys

Protect MCEGold Data Services usernames, passwords, and API keys.

- Do not commit real credentials.
- Do not paste credentials into public issues, logs, or documentation.
- Prefer deployment-secret mechanisms or protected environment variables where available.
- Restrict access to `/config`, because local configuration can contain sensitive values.

## Persistent Volumes

Protect both persistent locations:

| Path | Contains |
| --- | --- |
| `/config` | local configuration and connection settings |
| `/data` | SQLite discovery database and Grafana data |

Back up and handle these volumes according to your organization's data-handling rules.

## Session Secret

Set a deployment-specific `SESSION_SECRET_KEY` for shared or persistent deployments. Do not reuse development placeholder values for environments that other users can access.

## Logs

Logs can contain operational details. Avoid sharing logs publicly without reviewing them for endpoint names, environment details, or sensitive data.
