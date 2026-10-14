# MCEGold Discovery Portal Public Documentation Study

## 1. Executive Summary

The public documentation should use `README.md` as a concise GitHub landing page and keep the deeper operator/integrator material under `docs/`. The current branch already contains a good first version of that shape: `README.md`, `docs/quick-start.md`, `docs/deployment.md`, `docs/configuration.md`, `docs/architecture.md`, `docs/workflows.md`, `docs/troubleshooting.md`, and `docs/security.md`.

Recommended strategy:

- Keep the small public documentation set: README, Quick Start, Deployment, Configuration, Architecture, Workflows, Troubleshooting, Security.
- Do not add `docs/developer.md`, `docs/grafana.md`, or `docs/reference-data.md` yet. Their useful content fits in the existing pages.
- Keep `docs/images/MCEGold_Portal.png`, `docs/images/MCEGold_Dashboard.png`, and `docs/CCOM Reference Data.xml` in `docs/` as public assets.
- Move internal/generated investigation artifacts out of `docs/` in a future change: `discovery-filter-manifest.json`, measurement-location comparison files, and the reference-data integration implementation note.
- Fix documentation inconsistencies before merge, especially the troubleshooting volume names.
- Mark release archive URL/filename policy as unresolved until the release process is formalized. Local artifacts show a likely pattern, but permanent public release instructions need product-owner confirmation.

Evidence used includes `Dockerfile.single-image`, `docker/single-image/*`, `app/core/config.py`, `app/main.py`, `app/api/routes.py`, `app/storage/database.py`, `app/storage/application_settings.py`, `grafana/provisioning/*`, `tests/test_single_image_assets.py`, `THIRD-PARTY-NOTICES.md`, current `README.md`, current `docs/`, local release archives under `artifacts/`, and relevant internal `.agents` notes.

## 2. Target Audience

The documentation should serve:

- MCEGold customers evaluating or deploying the Discovery Portal appliance.
- Integration developers validating MCEGold Data Services discovery workflows.
- Software developers evaluating MCEGold Data Services with the bundled Connector CLI.
- System administrators deploying the single-image Docker appliance.
- Technical users who know basic Docker but do not know this repository or PdMA internal development history.

The public audience should not need to know Connector internals, internal class names, private DTOs, implementation layers, or Codex working history.

## 3. Documentation Principles

- `README.md` is the public landing page. It should explain what the repository is, show one representative image, summarize the architecture, and link to deeper docs.
- `docs/` must contain only public material and public assets.
- Internal studies, investigations, generated diagnostics, release-readiness notes, design discussions, and Codex notes belong under `.agents/`.
- Public docs should describe behavior, configuration, workflows, Docker deployment, public interfaces, and operator troubleshooting.
- Public docs must not document proprietary `MCEGold.Data.Services.Connector` internals.
- Where repository evidence is incomplete, docs should say `UNVERIFIED` or avoid the claim.
- Linux Docker Engine and Windows Docker Desktop command paths should stay separate.
- Beginner deployment instructions should prefer Docker named volumes, which are supported by `Dockerfile.single-image` declaring `VOLUME ["/config", "/data"]`.

## 4. Recommended Public Documentation Tree

```text
README.md
LICENSE
THIRD-PARTY-NOTICES.md
docs/
  quick-start.md
  deployment.md
  configuration.md
  architecture.md
  workflows.md
  troubleshooting.md
  security.md
  CCOM Reference Data.xml
  images/
    MCEGold_Portal.png
    MCEGold_Dashboard.png
```

Do not create these documents at this time:

- `docs/developer.md`: build-from-source is not the default public path; add only after a supported public build process is documented.
- `docs/grafana.md`: Grafana content is currently small enough for Architecture, Configuration, Deployment, and Troubleshooting.
- `docs/reference-data.md`: reference-data behavior can be covered in Architecture and Configuration unless product owners want a public reference-data guide.

## 5. README Recommendation

Recommended outline:

```text
# MCEGold Discovery Portal
## Overview
## Architecture at a Glance
## Included Components
## Quick Start
## Documentation
## License and Third-Party Components
```

Keep inline:

- One-paragraph product description.
- Problem solved: local guided discovery and dashboard inspection for MCEGold Data Services.
- Short architecture diagram.
- Included components.
- Short Quick Start summary linking to `docs/quick-start.md`.
- Documentation links.
- License and third-party notice links.

Move or keep out of README:

- Full Linux/Windows command sequences.
- Full configuration variable reference.
- Connector CLI internal command contracts.
- Full troubleshooting tree.
- Internal design or release-readiness details.

Image recommendation:

- Keep `docs/images/MCEGold_Portal.png` in README. It is an immediate first-viewport signal of the product and shows the guided Portal experience.
- Use alt text like: `MCEGold Discovery Portal guided discovery screen`.
- Do not place the Grafana dashboard screenshot in README unless the README becomes visually crowded; one image is enough.

Architecture diagram recommendation:

- Keep a concise text diagram in README, but revise it to show Portal and Publication Collector as parallel consumers of the Connector CLI and shared SQLite, with Grafana reading SQLite. The current README diagram is directionally correct but slightly too linear.

## 6. Quick Start Recommendation

Purpose: shortest successful first-run path using the published single-image release.

Audience: users who have Docker available and want to run the appliance quickly.

Required sections:

- Prerequisites.
- Load the image archive.
- Identify the loaded image tag.
- Create named volumes.
- Run the container.
- Open Portal.
- Configure MCEGold Data Services connection.
- Start discovery.
- Open Grafana.
- Link to Deployment and Troubleshooting.

Information sources:

- `Dockerfile.single-image`: exposed ports `8000` and `3000`, `/config` and `/data` volumes, healthcheck.
- `docker/single-image/bin/mcegold-single-image-entrypoint`: first-run config seeding.
- `docker/single-image/templates/*.json`: default paths and blank connection settings.
- `artifacts/mcegold-discovery-1.0.0-linux-amd64.tar.gz` manifest: image tag `mcegold-discovery:1.0.0`.
- Current `docs/quick-start.md`.

Missing or uncertain:

- Permanent GitHub Release URL and exact public filename policy are UNVERIFIED.
- Whether all public releases will use `.tar.gz` archives with the observed `mcegold-discovery-<version>-linux-amd64.tar.gz` name is UNVERIFIED.

Should not include:

- Build-from-source instructions.
- Proprietary Connector implementation.
- Internal release packaging notes.

## 7. Deployment Documentation Recommendation

Purpose: detailed operator deployment manual for the published single-image Docker appliance.

Audience: system administrators, integrators, and technical evaluators.

Evidence:

- `Dockerfile.single-image` exposes `8000` and `3000`, declares `/config` and `/data`, uses healthcheck `http://127.0.0.1:8000/health`, and runs as user `mcegold`.
- `docker/single-image/supervisord.conf` starts Portal, Publication Collector, and Grafana.
- `docker/single-image/grafana.ini` binds Grafana to `0.0.0.0:3000`.
- `docker/single-image/bin/mcegold-wait-for-portal-db` gates collector startup on schema version `17`.
- Archive manifests show local tags `mcegold-discovery:1.0.0`, `mcegold-discovery:1.0.0-rc1`, and `mcegold-discovery:1.0.0-rc2`.

### Linux Docker Engine

Recommended outline:

1. Docker prerequisite.
2. Download release archive from GitHub Releases.
3. Change to archive directory.
4. Load image:

   ```bash
   docker load -i ./mcegold-discovery-<version>-linux-amd64.tar.gz
   ```

5. Verify loaded image/tag:

   ```bash
   docker image ls mcegold-discovery
   IMAGE="mcegold-discovery:<version>"
   ```

6. Create persistent volumes:

   ```bash
   docker volume create mcegold-config
   docker volume create mcegold-data
   ```

7. Run container with ports and volumes:

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

8. Check status and health:

   ```bash
   docker ps
   docker inspect --format '{{.State.Health.Status}}' mcegold-discovery
   docker logs mcegold-discovery
   ```

9. Open Portal at `http://localhost:8000`.
10. Open Grafana at `http://localhost:3000`.
11. Stop/start/restart/logs.
12. Upgrade while preserving volumes.
13. Clean reset by removing container and the two named volumes.

Commands/actions needing verification:

- Permanent archive filename.
- Permanent release URL.
- Whether docs should recommend `docker inspect` health output or keep `docker ps` only.
- Whether official release archives will always load to `mcegold-discovery:<version>`.

### Windows Docker Desktop

Recommended outline:

1. Docker Desktop prerequisite.
2. Confirm Docker Desktop is running Linux containers.
3. Use PowerShell, not Bash.
4. Change to archive folder:

   ```powershell
   Set-Location C:\Path\To\Downloaded\Release
   ```

5. Load image:

   ```powershell
   docker load -i .\mcegold-discovery-<version>-linux-amd64.tar.gz
   ```

6. Verify loaded image/tag:

   ```powershell
   docker image ls mcegold-discovery
   $Image = "mcegold-discovery:<version>"
   ```

7. Create persistent volumes:

   ```powershell
   docker volume create mcegold-config
   docker volume create mcegold-data
   ```

8. Run container:

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

9. Check status:

   ```powershell
   docker ps
   docker inspect --format '{{.State.Health.Status}}' mcegold-discovery
   docker logs mcegold-discovery
   ```

10. Open Portal:

    ```powershell
    Start-Process "http://localhost:8000"
    ```

11. Open Grafana:

    ```powershell
    Start-Process "http://localhost:3000"
    ```

12. Stop/start/restart/logs.
13. Upgrade while preserving volumes.
14. Clean reset.

Commands/actions needing verification:

- Whether any end-user Windows deployment step requires WSL. Current repository evidence does not require WSL for running the image in Docker Desktop.
- Permanent archive filename and tag policy.
- Whether a checksum file will be published. Local artifacts include `mcegold-discovery-1.0.0-rc1-linux-amd64.tar.gz.sha256`, but not all observed archives have checksums.

## 8. Configuration Documentation Recommendation

Purpose: explain user-facing configuration, persistence, defaults, and precedence.

Audience: operators and integrators configuring the appliance.

Required sections:

- Portal Settings page.
- MCEGold Data Services connection: URL, username, password, API key.
- Local paths in the single-image deployment:
  - `/config/portal.local.json`
  - `/config/connector.config.json`
  - `/config/collector.local.json`
  - `/data/discovery_portal.db`
- Configuration precedence: environment variable overrides take precedence over local config, then defaults. Evidence: `resolve_portal_config_value` in `app/core/config.py`.
- Environment variables:
  - `MCEGOLD_HOST`
  - `MCEGOLD_USERNAME`
  - `MCEGOLD_PASSWORD`
  - `MCEGOLD_API_KEY`
  - `MCEGOLD_CLI_PATH`
  - `CONNECTOR_CONFIG_PATH`
  - `DISCOVERY_DATABASE_PATH`
  - `GRAFANA_DASHBOARD_URL`
  - `SESSION_SECRET_KEY`
  - relevant limits such as `MCEGOLD_CLI_TIMEOUT_SECONDS`
- Publication Collector settings:
  - `Collector.Enabled`, default `true`.
  - `Collector.PollingIntervalSeconds`, default `15`.
- Data retention:
  - `DataRetention.Enabled`, default `false`.
  - `DataRetention.Days`, default `90`, allowed range `30..730`.
- Grafana dashboard URL behavior.
- Reference-data seeding at startup.

Should not include:

- Internal Connector classes or DTOs.
- Full JSON mapper details.
- Private endpoint examples or credentials.

## 9. Architecture Documentation Recommendation

Purpose: public conceptual architecture, not proprietary implementation.

Recommended public model:

```text
MCEGold Data Services
        |
        v
Connector CLI
        |
        +----------------------+
        |                      |
        v                      v
Discovery Portal      Publication Collector
        |                      |
        +----------+-----------+
                   |
                   v
             SQLite database
                   |
                   v
                Grafana
```

This model is supported by:

- `Dockerfile.single-image`: bundles Portal, Collector source, Connector CLI, Grafana, and docs/reference data.
- `docker/single-image/supervisord.conf`: runs Portal, Collector, and Grafana in one container.
- `docker/single-image/templates/portal.local.json` and `collector.local.json`: both point at `/opt/mcegold-cli/MCEGold.Data.Services.Connector.Cli`, `/config/connector.config.json`, and `/data/discovery_portal.db`.
- `grafana/provisioning/datasources/sqlite.yaml`: Grafana reads `/data/discovery_portal.db`.
- `app/storage/database.py`: creates the SQLite schema and reporting views.

Recommended images:

- Use `MCEGold_Portal.png` in README and/or Quick Start.
- Use `MCEGold_Dashboard.png` in Architecture or Troubleshooting/Grafana sections.
- Add a simple public architecture diagram later if desired. It should show the parallel Portal/Collector relationship and shared SQLite.

Should not include:

- Internal Connector architecture.
- Internal CLI DTOs or BOD mapping layers.
- Internal schema migration history except public upgrade caveats.

## 10. Workflow Documentation Recommendation

Purpose: explain public behavior for discovery workflows.

Audience: users running the Portal and integrators understanding what data is discovered.

Required sections:

- Top-down discovery:
  - Start Discovery opens a Connector request session.
  - Site -> Segment -> Measurement Location -> Measurements.
  - Parent selections are preserved in web session.
  - End Discovery closes the request session when possible.
- Site discovery:
  - Gets sites through the CLI.
  - Stores discovered sites in SQLite when persistence succeeds.
- Segment discovery:
  - Requires selected Site.
  - Optional Segment Type selector is UUID-backed.
- Measurement Location discovery:
  - Requires selected Segment.
  - Optional Measurement Location Type selector is UUID-backed.
- Measurement preview:
  - Requires selected Measurement Location and Segment.
  - Supports recorded range and Max Items.
  - Stage 1 preview is not an analytics surface.
- Publication Collector:
  - Runs continuously inside the default container.
  - Uses the Connector CLI and shared configuration.
  - Writes runtime status and publication/measurement data to SQLite.
- Bottom-up discovery:
  - Explain conceptually: incoming publication data can require local context around a measurement.
  - Avoid proprietary implementation detail.
- Local persistence:
  - SQLite stores discovered dimensions and measurement facts.
  - Grafana reads persisted data.

Sources:

- `app/api/routes.py`
- `app/services/mcegold_cli_discovery_client.py`
- `app/storage/discovered_entity_store.py`
- `.agents/implementation/cli-request-session-workflow.md`
- `.agents/implementation/workflow-session-context.md`
- `.agents/implementation/cli-get-*.md`

Should not include:

- Internal request mapper implementation.
- Full short-form CLI JSON contract.
- Proprietary Connector internals.

## 11. Troubleshooting Documentation Recommendation

Supported diagnostic topics:

- Portal does not start.
- Container healthcheck fails.
- `/config` or `/data` not writable.
- Existing database schema is unsupported or older than schema version `17`.
- Connector CLI path/config missing.
- MCEGold Data Services URL or credentials invalid.
- Discovery request timeout or fault.
- Start Discovery/session issues.
- Publication Collector offline, disabled, or error status.
- Grafana slow to start.
- Grafana dashboard or SQLite datasource not loading.
- Old data appears because named volumes persist.
- Clean reset and volume removal.
- Logs and redacted error output.

Current doc fix needed:

- `docs/troubleshooting.md` uses `mcegold-discovery-config` and `mcegold-discovery-data` in reset/inspect examples, but `docs/deployment.md` and `docs/quick-start.md` use `mcegold-config` and `mcegold-data`. Standardize on `mcegold-config` and `mcegold-data` unless product owners choose different names.

Should not include:

- Unresolved bugs as normal behavior.
- Instructions to inspect proprietary Connector internals.
- Raw credential-bearing diagnostics.

## 12. Security Documentation Recommendation

Actual deployment/security concerns:

- Portal binds to `0.0.0.0:8000` in the container.
- Grafana binds to `0.0.0.0:3000` in the container.
- No repository evidence of built-in Portal authentication.
- `adminControlsEnabled` hides/admin-controls behavior but is not an authorization system. Evidence: `.agents/release/single-image-release-readiness.md`.
- Grafana defaults are `admin/admin` unless `GF_SECURITY_ADMIN_USER` and `GF_SECURITY_ADMIN_PASSWORD` are provided. Evidence: `docker/single-image/bin/mcegold-single-image-entrypoint`.
- `SESSION_SECRET_KEY` defaults to `dev-only-change-this-session-secret`; shared deployments should override it.
- `/config` can contain credentials and should be protected.
- `/data` contains SQLite discovery/Grafana data and should be protected/backed up according to customer policy.
- Do not expose Portal or Grafana to untrusted networks without reverse proxy, TLS, VPN, identity provider, or equivalent external access control.
- Logs can contain operational details; CLI errors are redacted in code, but logs should still be reviewed before sharing.

Should not invent:

- Built-in Portal login.
- Built-in TLS.
- Built-in secret manager.
- Multi-user authorization.

## 13. Reference Data Documentation Recommendation

`docs/CCOM Reference Data.xml` is genuinely useful public material because the runtime uses it to seed SQLite reference dimensions on a new/unseeded database. It is also referenced in `THIRD-PARTY-NOTICES.md`.

Recommended public placement:

- Keep `docs/CCOM Reference Data.xml`.
- Cover conceptual behavior in `docs/architecture.md`.
- Cover configuration and reset behavior in `docs/configuration.md`.
- Do not create `docs/reference-data.md` yet.

Public facts to include:

- The XML seeds reference dimensions such as Site Type, Segment Type, Measurement Location Type, Unit, UOM Quantity, and Info Source.
- It does not create demo Sites, Segments, Measurement Locations, or Measurement facts.
- A new or unseeded database requires the XML at startup.
- Deleting the database causes startup to recreate and reseed it.
- Third-party licensing applies; see `THIRD-PARTY-NOTICES.md`.

What should not be public:

- Generated comparison studies.
- Proposed addendum CSVs.
- Internal XML loader implementation details unless needed for operator troubleshooting.

## 14. Images Review

| Filename | Depicts | Technically current | Public suitable | Best location | README use | Alt text | Caption recommendation |
|---|---|---:|---:|---|---:|---|---|
| `docs/images/MCEGold_Portal.png` | Portal guided discovery screen | Yes, based on current README usage and UI routes/templates | Yes | `docs/images/` | Yes | `MCEGold Discovery Portal guided discovery screen` | Optional: "Guided Site to Segment to Measurement Location discovery in the Portal." |
| `docs/images/MCEGold_Dashboard.png` | Grafana MCEGold operations dashboard | Yes, matches bundled Grafana dashboard concept | Yes | `docs/images/` | No, prefer Architecture | `MCEGold Grafana dashboard showing discovered measurements` | Optional: "Bundled Grafana dashboard reading the local SQLite discovery database." |

Both images are 1922x1041 PNG files. Do not modify them during this study.

## 15. Existing docs/ Audit

| Path | Current purpose | Classification | Public suitability | Recommended action | Dependencies/references |
|---|---|---|---|---|---|
| `docs/architecture.md` | Public architecture overview | PUBLIC - REVISE | Suitable, but diagram should show Portal and Collector in parallel | Revise in future docs pass | README links it |
| `docs/CCOM Reference Data.xml` | Runtime reference-data seed asset | PUBLIC - KEEP | Suitable as required public reference asset with notices | Keep in `docs/` | `Dockerfile.single-image`, `app/core/config.py`, `ReferenceDataService`, tests, `THIRD-PARTY-NOTICES.md` |
| `docs/configuration.md` | Public configuration guide | PUBLIC - REVISE | Suitable | Add precedence, default values, collector/data-retention details | README links it |
| `docs/deployment.md` | Public deployment guide | PUBLIC - REVISE | Suitable | Keep, verify release filename/tag policy and add healthcheck if desired | README links it |
| `docs/discovery-filter-manifest.json` | Machine-readable CLI filter/contract manifest | INTERNAL - MOVE OUT OF docs | Not suitable; exposes Connector mapping details and internal contract notes | Move to `.agents/implementation/` or `tests/fixtures/` after updating tests | `tests/test_filter_manifest.py`; `.agents/implementation/discovery-filter-manifest.md` links to it |
| `docs/images/MCEGold_Dashboard.png` | Grafana screenshot | PUBLIC - KEEP | Suitable | Keep | `docs/architecture.md` |
| `docs/images/MCEGold_Portal.png` | Portal screenshot | PUBLIC - KEEP | Suitable | Keep | `README.md` |
| `docs/measurement-location-type-comparison.md` | Internal workflow for local comparison script | INTERNAL - MOVE OUT OF docs | Not public; instructs local investigation workflow | Move to `.agents/investigations/` or script docs outside public docs | `scripts/compare_measurement_location_types.py` |
| `docs/measurement-location-type-reference-addendum.csv` | Generated proposed addendum from captured message comparison | GENERATED - MOVE OUT OF docs | Not public; generated review artifact | Move to `.agents/investigations/` or ignored generated output | Generated by `scripts/compare_measurement_location_types.py` |
| `docs/measurement-location-type-reference-comparison.md` | Generated comparison report | GENERATED - MOVE OUT OF docs | Not public; investigation result from local capture | Move to `.agents/investigations/` | Generated by `scripts/compare_measurement_location_types.py` |
| `docs/quick-start.md` | Public first-run guide | PUBLIC - REVISE | Suitable | Keep concise; verify release filename/tag | README links it |
| `docs/reference-data-integration.md` | Implementation-level reference-data integration note | PUBLIC - CONSOLIDATE | Partly useful but too implementation-oriented | Distill into Architecture and Configuration, then move internal detail to `.agents/implementation/` | References `docs/CCOM Reference Data.xml`; overlaps current docs |
| `docs/security.md` | Public security notes | PUBLIC - REVISE | Suitable | Keep, add `adminControlsEnabled` caveat if not present | README links it |
| `docs/troubleshooting.md` | Public troubleshooting guide | PUBLIC - REVISE | Suitable | Fix volume-name inconsistency and split Bash/PowerShell where helpful | README links it |
| `docs/workflows.md` | Public workflow guide | PUBLIC - REVISE | Suitable | Expand enough for top-down, collector, bottom-up, and persistence | README links it |

## 16. Internal Material With Public Value

Useful facts to distill, without linking public docs to `.agents/`:

- `.agents/release/single-image-release-readiness.md`
  - Single-image process supervision is the release posture.
  - Connector CLI bundling is cleared with proprietary dependency notice.
  - MIMOSA CCOM reference data is cleared with license conditions.
  - Security posture is trusted/demo network unless protected externally.
  - `adminControlsEnabled` is not authorization.
- `.agents/architecture/discovered-entity-local-storage-design.md`
  - Public conceptual storage model: Site -> Segment -> Measurement Location -> Measurement facts.
  - Schema version `17` is current; older pre-release schemas are not automatically upgraded.
  - Reference data seeds dimensions but not customer/demo business data.
- `.agents/implementation/cli-request-session-workflow.md`
  - Start Discovery opens/reuses a request session.
  - End Discovery closes it when possible.
  - Session storage excludes credentials/raw payloads.
- `.agents/implementation/workflow-session-context.md`
  - Selected workflow context is stored for UX and avoids hidden upstream calls.
- `.agents/implementation/cli-get-*.md`
  - Public workflow behavior and error handling facts.
- `.agents/implementation/discovery-filter-manifest.md`
  - High-level supported filters can inform public workflow docs, but mapped BOD paths and Connector internals should stay internal.

## 17. Script/Test-Dependent Documentation Artifacts

Path dependencies currently preventing simple removal from `docs/`:

| Artifact | Current dependency | Recommended future home | Required future change |
|---|---|---|---|
| `docs/discovery-filter-manifest.json` | `tests/test_filter_manifest.py` reads it from `docs/` | `tests/fixtures/discovery-filter-manifest.json` if test fixture; `.agents/implementation/discovery-filter-manifest.json` if internal study artifact | Update test path and any internal links |
| `docs/measurement-location-type-reference-comparison.md` | Default output path in `scripts/compare_measurement_location_types.py` | `.agents/investigations/measurement-location-type-reference-comparison.md` | Change script default output path |
| `docs/measurement-location-type-reference-addendum.csv` | Default addendum path in `scripts/compare_measurement_location_types.py` | `.agents/investigations/measurement-location-type-reference-addendum.csv` | Change script default addendum path |
| `docs/measurement-location-type-comparison.md` | Human workflow doc for the comparison script | `.agents/investigations/measurement-location-type-comparison.md` or script-adjacent internal note | Update references if retained |
| `docs/reference-data-integration.md` | Public docs currently may link/reference it indirectly; no test dependency found | `.agents/implementation/reference-data-integration.md` after public facts are consolidated | Update README/docs links if any are added later |

Do not move these files as part of this study.

## 18. Terminology Standard

Recommended canonical public terminology:

- `MCEGold Discovery Portal`: full product/repository name on first use; `Portal` after.
- `Publication Collector`: public name for the background publication process.
- `MCEGold Data Services`: external service/source system.
- `Connector CLI`: public shorthand for the bundled MCEGold Data Services Connector CLI; use full name on first mention.
- `discovery database`: friendly term for local SQLite persistence.
- `SQLite`: storage engine; say `SQLite discovery database` when clarity matters.
- `Grafana`: bundled dashboard service.
- `top-down discovery`: guided Site -> Segment -> Measurement Location -> Measurements workflow.
- `bottom-up discovery`: conceptual publication-driven context discovery/persistence around incoming measurement data.
- `Site`: top-level discovered operational context.
- `Segment`: child of Site.
- `Measurement Location`: point/sensor/logical location under Segment where measurements are observed.
- `Measurement`: observed numeric value over time associated with a Measurement Location.

Naming inconsistencies to correct:

- Use `Measurement Location` in prose, not mixed `measurement-location` except in URLs/filenames.
- Use `Publication Collector`, not alternating `Collector` alone on first mention.
- Standardize named volumes as `mcegold-config` and `mcegold-data` unless product owners choose otherwise.
- Use `MCEGold Data Services` rather than bare `MCEGold` when referring to the external service.

## 19. Release Documentation Gaps

Verified:

- Local archive manifests show Docker tags:
  - `mcegold-discovery:1.0.0`
  - `mcegold-discovery:1.0.0-rc1`
  - `mcegold-discovery:1.0.0-rc2`
- Local artifact filenames include:
  - `mcegold-discovery-1.0.0-linux-amd64.tar.gz`
  - `mcegold-discovery-1.0.0-rc1-linux-amd64.tar.gz`
  - `mcegold-discovery-1.0.0-rc2-linux-amd64.tar.gz`
- `Dockerfile.single-image` builds the single-image appliance and copies the Connector CLI from named build context `connector-cli-package`.

Unverified:

- Permanent GitHub Releases URL.
- Whether every public release will include a `.sha256` checksum.
- Whether every public archive filename will follow `mcegold-discovery-<version>-linux-amd64.tar.gz`.
- Whether Docker tags will always be `mcegold-discovery:<version>`.
- Whether `latest` will ever be published or documented. Do not recommend `latest` without a release policy.
- Exact build command for public source users, because `Dockerfile.single-image` requires named external build contexts.

## 20. Proposed Documentation Implementation Order

1. Fix public-doc correctness issues already found:
   - Troubleshooting volume names.
   - Architecture diagram shape.
   - Any release filename/tag placeholders product owners can confirm.
2. Move or rehome internal/generated artifacts from `docs/`:
   - Update script defaults and tests first.
   - Move generated comparison outputs and manifest out of public docs.
3. Tighten `README.md`:
   - Keep concise.
   - Use one Portal screenshot.
   - Link to deeper docs.
4. Tighten `docs/quick-start.md`:
   - Keep it short and image-release based.
5. Expand `docs/deployment.md`:
   - Keep Linux and Windows paths separate.
   - Include upgrade and reset.
   - Mark release URL/filename policy only after confirmation.
6. Improve `docs/configuration.md`:
   - Add precedence and settings defaults.
7. Improve `docs/architecture.md` and `docs/workflows.md`:
   - Public concepts only.
8. Improve `docs/security.md` and `docs/troubleshooting.md`.
9. Final audit for public-only `docs/`.

## 21. Public Documentation Acceptance Checklist

- [ ] README is concise and functions as public landing page.
- [ ] README links only to public docs/assets.
- [ ] `docs/` contains only public docs and public assets.
- [ ] Internal studies and generated diagnostics are under `.agents/` or test/script fixture locations, not public docs.
- [ ] Linux Docker Engine and Windows Docker Desktop instructions are separate.
- [ ] Commands use the confirmed release archive filename and loaded Docker tag policy.
- [ ] Deployment docs use named volumes consistently.
- [ ] Upgrade docs preserve `/config` and `/data` volumes.
- [ ] Clean reset docs clearly warn about deleting config, SQLite data, and Grafana state.
- [ ] Configuration docs explain environment-over-local-config precedence.
- [ ] Security docs do not invent built-in auth/TLS.
- [ ] Security docs warn about Portal/Grafana exposure and default Grafana credentials.
- [ ] Public docs avoid proprietary Connector internals.
- [ ] Reference data licensing is linked through `THIRD-PARTY-NOTICES.md`.
- [ ] Images have appropriate alt text.
- [ ] No public docs link to `.agents/`.
- [ ] No real endpoints, credentials, API keys, local payloads, or private operational procedures are present.
- [ ] `git diff --check` passes.

## 22. Open Questions / Human Decisions

- Confirm permanent GitHub Release URL structure and whether docs should link to a release page or exact artifact.
- Confirm release archive filename policy.
- Confirm Docker image tag policy and whether `latest` should be avoided or documented.
- Decide whether checksum files are required and should be documented.
- Decide final named volume names. Current docs mostly use `mcegold-config` and `mcegold-data`; troubleshooting has inconsistent names.
- Decide whether `docs/CCOM Reference Data.xml` should remain directly under `docs/` or move to a public asset subfolder such as `docs/reference/`. Current runtime defaults and notices support keeping it where it is.
- Decide whether public docs should include a generated architecture diagram in addition to the text diagram.
- Decide whether any public build-from-source guide is needed for developers, given `Dockerfile.single-image` depends on named external build contexts.
- Decide how much Grafana default credential guidance belongs in Deployment versus Security.
- Decide whether bottom-up discovery should remain conceptual or wait for more operator-visible implementation evidence before expanding.
