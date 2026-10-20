# MCEGold Discovery v1.0.1 overlay packaging

This overlay starts with `FROM mcegold-discovery:1.0.0`, replaces
`/app/portal/app`, installs the supplied Collector v1.0.1 archive into the
inherited Python environment, and installs the public Collector configuration
template at `/app/templates/collector.local.json`. Portal templates and static
assets are part of `app/`. The root Dockerfiles and application sources are unchanged.

## Existing tested distribution

The existing `artifacts/mcegold-discovery-v1.0.1-linux-amd64.tar` is a Docker image
archive tagged `mcegold-discovery:1.0.1`, for Linux amd64. Its SHA-256 is:

```text
d1a447455c487db9e2d13ce349f1416be4ffffdbfd708f5e292ce50ba0c24f30
```

Its image configuration digest is
`sha256:9aaf8a6fbea2081cfd3a3772aa5266413d7fe01be2d53cd2a34ac5914ae13254`.
Archive history records the original overlay's Collector installation, Portal
application copy, and interoperability check, followed by a final
`COPY --chown=mcegold:mcegold collector.local.json /app/templates/collector.local.json`.
That final template sets `useSharedRequestSession` to `true`.

The distribution was reported tested on Windows Docker Desktop and deployed on
Rackspace Linux. Archive inspection establishes the contents and layer history;
it does not repeat those deployment tests. Preserve this archive unchanged.

The reusable recipe now includes that final template copy before its smoke
checks. It captures the distribution's configuration behavior in one build and
also validates the shared-mode default. This changes the historical build order;
it does not claim to reproduce the existing archive byte for byte. No rebuild or
deployment is required for this repository consistency update.

## Inputs and installation

- Use the current `staging` checkout. Tracked `app/` files are copied using their
  current bytes; untracked, non-ignored app files cause preparation to fail.
  Review local modifications before preparing the release context.
- Publisher-provided Collector archive, supplied explicitly with
  `--collector-archive`: `MCEGold.Discovery.PublicationCollector-v1.0.1.tar.gz`.
- Collector SHA-256:
  `D3E1AF3D43301663FACF5870D9D74F74338EA8884976C2C67F0E9BD75FF0316F`.
- Verified local v1.0.0 image ID:
  `sha256:9bd95ef98d8744347c7d644033c26942b5aba5a6e9f9d6d28427a7a0bd77c30f`.
- BuildKit with Linux containers and Python 3.12 on the preparation host are
  required. The inspected base is Linux amd64, runs as `mcegold`, and includes pip.
- Public Collector defaults come only from
  `docker/single-image/templates/collector.local.json`. Preparation rejects
  unexpected properties or values, including deployment-specific credentials.

The supplied archive contains `pyproject.toml` and Python sources, rather than a
prebuilt wheel. `pip install` therefore performs its normal internal wheel
installation step and writes v1.0.1 distribution metadata and the console script.
It does not rebuild an sdist, repackage the release archive, or use a Collector
source checkout. These installation steps describe later packaging runs, not
work required to update the existing distribution.

Pinned setuptools 83.0.0 is used only in `/tmp` during installation, with no global
tooling changes. Its wheel URL and SHA-256 are pinned from the
[PyPI release metadata](https://pypi.org/pypi/setuptools/83.0.0/json).
Context preparation downloads that wheel unless `--setuptools-wheel` supplies a
previously downloaded copy. This is the only preparation network requirement.
Docker installation runs offline with `--no-index --no-deps
--no-build-isolation --force-reinstall`. No runtime dependency, Grafana,
Supervisor, or Connector CLI installation occurs.

The release archive includes a seed database and example configuration. They stay
inside the read-only build input and are not installed by its package definition.
No archive or build tooling is copied into an image layer. The build context uses
an explicit allowlist; it excludes deployed configs, databases, docs, and logs.
The public Collector template is the sole allowed configuration input. The
recipe copies it to `/app/templates`, never `/config`; runtime databases and
credentials must not be copied into either build layers or image configuration.

## Preparation and build commands (for later execution)

Run in PowerShell from the Portal repository root. Preparation does not invoke
Docker, install packages, or repackage Collector:

```powershell
$collectorArchive = 'C:\Path\To\MCEGold.Discovery.PublicationCollector-v1.0.1.tar.gz'
python docker/overlay-v1.0.1/prepare_context.py --collector-archive $collectorArchive --check-only
if ($LASTEXITCODE -ne 0) { throw 'Input validation failed' }

$context = Join-Path $env:TEMP ('mcegold-discovery-v1.0.1-' + [guid]::NewGuid())
python docker/overlay-v1.0.1/prepare_context.py --collector-archive $collectorArchive --output $context
if ($LASTEXITCODE -ne 0) { throw 'Context preparation failed' }
```

For an offline preparation host, append
`--setuptools-wheel C:\path\to\setuptools-83.0.0-py3-none-any.whl`.
The supplied wheel must match the pinned hash.

Before building, verify the local tag still identifies the inspected base. The
Dockerfile intentionally uses the required tag, so this guard is part of the build
procedure; do not retag or pull the base between this check and the build:

```powershell
$expectedBase = 'sha256:9bd95ef98d8744347c7d644033c26942b5aba5a6e9f9d6d28427a7a0bd77c30f'
$actualBase = docker image inspect mcegold-discovery:1.0.0 --format '{{.Id}}'
if ($LASTEXITCODE -ne 0 -or $actualBase -ne $expectedBase) { throw 'Unexpected v1.0.0 base image' }
$Image = 'mcegold-discovery:1.0.1-repack'
docker buildx build --load --pull=false --network=none --platform linux/amd64 --provenance=false --build-arg SOURCE_DATE_EPOCH=1791331200 --tag $Image --file "$context/Dockerfile" $context
if ($LASTEXITCODE -ne 0) { throw 'Overlay build failed' }
```

Use a separate review tag; do not replace the tested `1.0.1` tag or archive.
The original v1.0.0 image is retained for rollback. Keep the complete prepared
context outside Git, including `SHA256SUMS` and `provenance.json`, for repeat builds. Context files use
fixed timestamps, pinned installation tooling, an unchanged Collector archive,
and recorded Portal bytes. Build-time hash verification rejects altered inputs.
Use the same Docker/BuildKit version for binary comparison: identical image or
export-archive digests across different builder versions are not guaranteed.
Preparing a new context after modifying `app/` or the public Collector template
intentionally produces new inputs. Commit only these four overlay source files,
the canonical template, and relevant tests; never add prepared contexts, wheels,
Collector archives, exported images, runtime databases, or credentials to Git.

## Verification commands (after an approved build)

The Dockerfile automatically imports every Portal Python module and checks
Collector version, installation path, CLI metadata, and `request_session_settings.py`.
It verifies the combined-image default (`true`), standalone Collector default
(`false`), and both directions of shared SQLite use: Portal writes a session that
Collector reads, then Collector writes runtime status that Portal reads. This uses a fresh
temporary database, never `/data/discovery_portal.db`, and contacts no Connector.

Repeat those checks using the inherited runtime user, without starting Supervisor
or mounting operational data:

```powershell
$checkScript = Join-Path $context 'verify_image.py'
docker run --rm --network none --read-only --tmpfs /tmp --entrypoint python --env PYTHONPATH=/app/portal --mount "type=bind,source=$checkScript,target=/verify_image.py,readonly" $Image /verify_image.py
if ($LASTEXITCODE -ne 0) { throw 'Image smoke checks failed' }
```

Check inherited configuration and base layers:

```powershell
$baseText = docker image inspect mcegold-discovery:1.0.0
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect base' }
$newText = docker image inspect $Image
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect overlay' }
$base = ($baseText | ConvertFrom-Json)[0]
$new = ($newText | ConvertFrom-Json)[0]
foreach ($field in @('Entrypoint', 'Cmd', 'ExposedPorts', 'Volumes', 'Env', 'User', 'WorkingDir', 'Healthcheck')) {
    $before = $base.Config.$field | ConvertTo-Json -Depth 20 -Compress
    $after = $new.Config.$field | ConvertTo-Json -Depth 20 -Compress
    if ($before -cne $after) { throw "Inherited setting changed: $field" }
}
for ($i = 0; $i -lt $base.RootFS.Layers.Count; $i++) {
    if ($new.RootFS.Layers[$i] -ne $base.RootFS.Layers[$i]) { throw "Base layer changed: $i" }
}
if ($base.Id -ne $expectedBase) { throw 'Rollback tag changed' }
'PASS: inherited settings and original base layers retained'
```

Expected entrypoint: `/usr/local/bin/mcegold-single-image-entrypoint`.
Expected command: `supervisord -c /etc/supervisor/conf.d/mcegold-discovery.conf`.
Expected ports: `8000/tcp` and `3000/tcp`.

## Data, deployed configuration, and limits

The overlay makes no writes to `/data`, `/config`, `/etc`, Grafana, Connector CLI,
or startup scripts. It updates only the public Collector template under
`/app/templates` in addition to application installation. The five preserved locations are:

- `/data/discovery_portal.db`
- `/config/portal.local.json`
- `/config/collector.local.json`
- `/config/connector.config.json`
- `/data/grafana`

At deployment, reuse the existing `/config` and `/data` volumes and their current
permissions. Both applications must resolve their database setting to
`/data/discovery_portal.db`, and the inherited runtime user must have write access
to the database **and its directory** for SQLite journals. The inherited
entrypoint copies the public template only when `/config/collector.local.json`
does not exist, so new combined installations default to shared mode enabled.
Existing configuration files are not overwritten: explicitly set their
`useSharedRequestSession` to `true` or supply
`MCEGOLD_USE_SHARED_REQUEST_SESSION=true` when enabling shared mode on upgrade.
Restart the Collector after a file change (restart the container in the combined
appliance). These are deployment instructions, not image build inputs. Rackspace
settings and credentials must remain outside the distributed image.

The Collector package's standalone default remains `false`; only the combined
image's template enables shared mode. No Collector application source is changed.

The Portal currently requires database schema version 17 and rejects incompatible
existing schemas. No migration or database replacement is included. The smoke
check verifies application interoperability on a fresh v17 database; it cannot
prove compatibility with operational contents, volume permissions, concurrent
production load, or remote Connector credentials. Later deployment validation
should use a consistent copy of the existing database and configuration with the
same volume layout. Application startup may perform its existing schema checks,
default-setting inserts, and data repairs; retaining the image does not roll back
database changes made during later runtime. Keep a consistent data backup for
deployment rollback as well as the original image.

## Versioned export command (only after successful build and verification)

```powershell
New-Item -ItemType Directory -Force artifacts | Out-Null
$exportPath = 'artifacts/mcegold-discovery-v1.0.1-repack-linux-amd64.tar'
if (Test-Path -LiteralPath $exportPath) { throw 'Export target already exists; preserve it' }
docker image save --output $exportPath $Image
if ($LASTEXITCODE -ne 0) { throw 'Image export failed' }
Get-FileHash -LiteralPath $exportPath -Algorithm SHA256
```

This is an image archive for `docker load`; volumes and operational data are not
part of it. This optional command writes a separate review artifact and must
never overwrite the existing tested distribution.
