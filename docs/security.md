# Deployment Security Notes

[Back to README](../README.md)

These notes describe practical deployment precautions for the current MCEGold Discovery Portal appliance.

## Network Exposure

The Portal listens on port `8000`. Grafana listens on port `3000`.

Do not expose either service to untrusted networks unless they are protected by approved network controls. For shared or production-style deployments, use a trusted reverse proxy, TLS termination, VPN, identity provider, or equivalent access-control layer.

## Portal Authentication

There is no repository evidence of built-in Portal authentication in the current appliance. Treat the Portal as an administrative surface.

`adminControlsEnabled` is not an authorization mechanism. Do not rely on it to secure a deployment.

## Grafana Credentials

The single-image appliance runs Grafana on port `3000`. Default Grafana credentials must be changed before broader exposure.

The image supports Grafana's standard environment variables:

```text
GF_SECURITY_ADMIN_USER
GF_SECURITY_ADMIN_PASSWORD
```

Use deployment-specific values for shared environments.

## MCEGold Data Services Credentials and API Keys

Protect MCEGold Data Services usernames, passwords, and API keys.

- Do not commit real credentials.
- Do not paste credentials into public issues, logs, or documentation.
- Prefer deployment-secret mechanisms or protected environment variables where available.
- Restrict access to `/config`, because local configuration can contain sensitive values.

## Session Secret

Set a deployment-specific `SESSION_SECRET_KEY` for shared or persistent deployments. Do not leave the development default in environments that other users can access.

## Persistent Volumes

Protect both persistent locations:

| Path | Contains |
| --- | --- |
| `/config` | Local configuration and connection settings |
| `/data` | SQLite discovery database and persistent runtime data |

Back up and handle these volumes according to your organization's data-handling rules.

## Logs

Logs can contain operational details. Avoid sharing logs publicly without reviewing them for endpoint names, environment details, or sensitive data.

## Features Not Provided by the Appliance

Do not assume the appliance provides:

- Built-in Portal login.
- Built-in TLS.
- Built-in secret management.
- Multi-user authorization.

Provide those controls externally when the deployment requires them.
