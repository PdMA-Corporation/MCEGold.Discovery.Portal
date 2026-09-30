# Single-Image Release Readiness

This document records the release-readiness decisions that must be settled before work begins on a combined MCEGold Discovery demo image containing the Portal, Publication Collector, Grafana, Connector CLI, SQLite data, and process supervision.

The architecture study classified the approach as:

```text
B - Single image is practical with process supervision
```

This document does not implement the combined image. It only records the release posture for the known blockers.

## Connector CLI Redistribution

CLI/open-source tooling classification: `CLEARED`

Future Docker bundling classification: `CLEARED WITH PROPRIETARY DEPENDENCY NOTICE`

Repository evidence:

- `MCEGold.Data.Services.Connector.Toolkit` documents `mcegold-python-linux-x64-v1.0.0.tar.gz` as a published Linux runtime package.
- Toolkit packaging publishes a self-contained Linux x64 `MCEGold.Data.Services.Connector.Cli` executable.
- The CLI project references the proprietary `MCEGold.Data.Services.Connector` NuGet package.
- The Connector CLI/tooling layer is intended to be open source for users to inspect, modify, and adapt to integration needs.
- The official self-contained Linux CLI package intentionally contains the runtime dependencies needed to execute the CLI.

Release posture:

- The future official MCEGold Discovery Docker image may bundle the official self-contained Connector CLI runtime.
- The `MCEGold.Data.Services.Connector` runtime/library remains proprietary.
- Bundling its binary/runtime dependency does not make the proprietary Connector source code open source.
- Proprietary dependency notices must remain visible in `THIRD-PARTY-NOTICES.md` or equivalent image documentation.

Do not expose or document proprietary Connector implementation details.

## Portal License

Classification: `CLEARED`

The Portal uses the MIT License.

Repository evidence:

- `MCEGold.Discovery.PublicationCollector` is licensed under MIT with copyright `2026 PdMA Corporation`.
- `MCEGold.Data.Services.Connector.Toolkit` is licensed under MIT with the same copyright convention.
- The Portal README describes this repository as part of the same public MCEGold Discovery ecosystem and as a public reference/demo application.

The Portal repository includes `LICENSE` with the matching MIT text and organization naming convention.

## MIMOSA CCOM Reference Data

Source repository classification: `CLEARED WITH MIMOSA LICENSE CONDITIONS`

Future Docker-image redistribution classification: `CLEARED WITH MIMOSA LICENSE CONDITIONS`

Runtime findings:

- Portal startup reads `docs/CCOM Reference Data.xml` by default through `REFERENCE_DATA_PATH`.
- A fresh unseeded database requires a valid reference-data XML file during startup.
- Once a database has been successfully seeded, startup can skip opening and parsing the XML when the seed marker and required reference rows are present.
- The XML seeds reference dimensions only. It does not seed demo Sites, Segments, Measurement Locations, or Measurement facts.

Release posture:

- The Portal is an example implementation of the publicly available MIMOSA CCOM standard.
- The CCOM reference data may be distributed with the Portal source and with a future MCEGold Discovery Docker image subject to applicable MIMOSA license conditions.
- MIMOSA CCOM materials remain third-party material owned or licensed by MIMOSA and/or its licensors.
- The CCOM XML is excluded from the Portal MIT License scope.
- Existing MIMOSA copyright, proprietary, and license notices in `docs/CCOM Reference Data.xml` must be preserved.

## Grafana SQLite Datasource Plugin

Classification: `CLEARED WITH VERSION PIN`

Plugin identity:

```text
frser-sqlite-datasource
```

Pinned version for v1.0.0 release planning:

```text
4.0.6
```

Evidence checked on 2026-09-30:

- Grafana Labs plugin catalog lists `frser-sqlite-datasource` version `4.0.6`, last updated May 13, 2026, with dependency `Grafana >=7.3.3`.
- The upstream GitHub release page documents deterministic install by plugin URL:

```text
grafana-cli --pluginUrl https://github.com/fr-ser/grafana-sqlite-datasource/releases/download/v4.0.6/frser-sqlite-datasource-4.0.6.zip plugins install frser-sqlite-datasource
```

The Portal dashboard and datasource provisioning reference this plugin by ID and query SQLite directly. The plugin must be installed before Grafana starts provisioning `grafana/provisioning/datasources/sqlite.yaml`.

Compatibility assumption:

- A future image should pin a Grafana version compatible with plugin `4.0.6`; the plugin catalog states `Grafana >=7.3.3`, but the final image should still smoke-test the selected Grafana image tag with the provisioned dashboard.

## Access-Control Defaults

Classification: `CLEARED FOR DEMO RELEASE`

The v1.0.0 posture is demo/local-network only:

- Portal may bind to a LAN/container address for demo access, but it must not be exposed to untrusted networks without external access control.
- The Settings UI is administrative and is not protected by built-in user authentication.
- `adminControlsEnabled` only hides Settings and selected controls; it is not authorization.
- `SESSION_SECRET_KEY` must be overridden for any shared or persistent environment.
- Grafana default admin credentials must not be used in exposed environments.
- Wider exposure requires a trusted reverse proxy, identity provider, VPN, or equivalent network control in front of both Portal and Grafana.

No full authentication or authorization system is added in this phase.

## Public-Release Hygiene

The tracked examples are intended to contain placeholders only. Do not commit:

- real MCEGold endpoint credentials;
- API keys, passwords, bearer tokens, or private connection strings;
- local Connector CLI payloads;
- local SQLite databases or captured live payloads;
- `.env`, `connector.config.json`, or `portal.local.json`.

The Portal source still references CDN-hosted Bootstrap assets in `app/templates/base.html`. That is acceptable for local/demo source release, but a future offline appliance image should vendor or otherwise pin frontend assets if offline operation is required.

## Overall Phase 1 Status

Release-readiness blocker disposition is complete.

Phase 1 validation completed on 2026-09-30 with JSON/YAML configuration checks, FastAPI import validation, and the automated pytest suite passing. The pytest validation used a temporary preseeded database and disabled pytest's cache provider because the local validation environment hung while writing pytest cache metadata during session finish.
