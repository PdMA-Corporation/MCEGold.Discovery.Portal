from pathlib import Path
import hashlib
import importlib.util
import json

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_single_image_dockerfile_uses_supervisor_and_collector_named_context() -> None:
    dockerfile = read("Dockerfile.single-image")

    assert "FROM python:3.12-slim-bookworm AS runtime" in dockerfile
    assert "supervisor" in dockerfile
    assert (
        "apt-get install -y --no-install-recommends "
        "ca-certificates libfontconfig1 libicu72 musl supervisor"
        in dockerfile
    )
    assert (
        "COPY --from=collector-source pyproject.toml README.md /tmp/collector/"
        in dockerfile
    )
    assert "pip install --no-cache-dir /tmp/collector" in dockerfile
    assert (
        "COPY --from=connector-cli-package "
        "mcegold-python-linux-x64-v1.0.0.tar.gz"
        in dockerfile
    )
    assert (
        "tar -xzf /tmp/connector-cli.tar.gz "
        "-C /opt/mcegold-cli --strip-components=1"
        in dockerfile
    )
    assert "rm /tmp/connector-cli.tar.gz" in dockerfile
    assert (
        "chmod 0755 /opt/mcegold-cli/MCEGold.Data.Services.Connector.Cli"
        in dockerfile
    )
    assert (
        "test -x /opt/mcegold-cli/MCEGold.Data.Services.Connector.Cli"
        in dockerfile
    )
    assert "ARG GRAFANA_VERSION=12.1.1" in dockerfile
    assert "ARG GRAFANA_SQLITE_PLUGIN_VERSION=4.0.6" in dockerfile
    assert (
        "grafana_${GRAFANA_VERSION}_16903967602_linux_amd64.tar.gz"
        in dockerfile
    )
    assert "sha256sum -c -" in dockerfile
    assert (
        "frser-sqlite-datasource-${GRAFANA_SQLITE_PLUGIN_VERSION}.zip"
        in dockerfile
    )
    assert (
        "chmod 0755 "
        "/var/lib/grafana/plugins/"
        "frser-sqlite-datasource/"
        "gpx_sqlite-datasource_linux_amd64"
        in dockerfile
    )
    assert (
        "test -x "
        "/var/lib/grafana/plugins/"
        "frser-sqlite-datasource/"
        "gpx_sqlite-datasource_linux_amd64"
        in dockerfile
    )
    assert (
        "mkdir -p "
        "/etc/grafana/dashboards "
        "/etc/grafana/provisioning/dashboards "
        "/etc/grafana/provisioning/datasources "
        "/etc/grafana/provisioning/plugins "
        "/etc/grafana/provisioning/alerting"
        in dockerfile
    )
    assert "COPY grafana/provisioning /etc/grafana/provisioning" in dockerfile
    assert (
        "COPY grafana/mcegold-operations.json "
        "/etc/grafana/dashboards/mcegold-operations.json"
        in dockerfile
    )
    assert (
        "COPY docker/single-image/grafana.ini /etc/grafana/grafana.ini"
        in dockerfile
    )
    assert "EXPOSE 8000 3000" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "/health" in dockerfile
    assert "USER mcegold" in dockerfile
    assert "dotnet-install" not in dockerfile
    assert "dotnet-runtime" not in dockerfile
    assert "aspnetcore-runtime" not in dockerfile


def test_single_image_authoritative_cli_path_is_consistent() -> None:
    dockerfile = read("Dockerfile.single-image")
    portal_template = json.loads(
        read("docker/single-image/templates/portal.local.json")
    )
    collector_template = json.loads(
        read("docker/single-image/templates/collector.local.json")
    )

    cli_path = "/opt/mcegold-cli/MCEGold.Data.Services.Connector.Cli"
    assert f"MCEGOLD_CLI_PATH={cli_path}" in dockerfile
    assert portal_template["mcegoldCliPath"] == cli_path
    assert collector_template["cliPath"] == cli_path


def test_single_image_collector_template_enables_shared_request_session() -> None:
    template = json.loads(read("docker/single-image/templates/collector.local.json"))

    assert template["useSharedRequestSession"] is True


def load_overlay_packaging():
    spec = importlib.util.spec_from_file_location(
        "overlay_prepare_context", REPO_ROOT / "docker/overlay-v1.0.1/prepare_context.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("change", [{"useSharedRequestSession": False}, {"password": "not-a-release-setting"}])
def test_overlay_rejects_nonrelease_collector_configuration(monkeypatch, tmp_path, change) -> None:
    packaging = load_overlay_packaging()
    template = json.loads(read("docker/single-image/templates/collector.local.json"))
    template.update(change)
    path = tmp_path / "collector.local.json"
    path.write_text(json.dumps(template), encoding="utf-8")
    monkeypatch.setattr(packaging, "COLLECTOR_TEMPLATE", path)

    with pytest.raises(ValueError, match="only the public v1.0.1 defaults"):
        packaging.collector_template_bytes()


def test_overlay_context_contains_release_template_and_excludes_runtime_files(monkeypatch, tmp_path) -> None:
    packaging = load_overlay_packaging()
    source = tmp_path / "source"
    app = source / "app/main.py"
    app.parent.mkdir(parents=True)
    app.write_text("# packaging fixture\n", encoding="utf-8")
    (source / "data").mkdir()
    (source / "data/runtime.db").write_bytes(b"not-for-packaging")
    (source / "configs").mkdir()
    (source / "configs/collector.local.json").write_text('{"password":"fixture"}', encoding="utf-8")
    archive = tmp_path / packaging.ARCHIVE_NAME
    archive.write_bytes(b"publisher archive fixture")
    wheel = tmp_path / packaging.TOOLS_NAME
    wheel.write_bytes(b"offline tooling fixture")
    output = tmp_path / "context"

    monkeypatch.setattr(packaging, "ROOT", source)
    monkeypatch.setattr(packaging, "portal_files", lambda: [app])
    # Archive validation is separate; exercise preparation without external inputs.
    monkeypatch.setattr(packaging, "check_archive", lambda path: None)
    monkeypatch.setattr(packaging, "TOOLS_SHA256", hashlib.sha256(wheel.read_bytes()).hexdigest())
    git_outputs = {"branch": b"staging\n", "rev-parse": b"fixture-commit\n", "status": b""}
    monkeypatch.setattr(packaging.subprocess, "check_output", lambda args, **kwargs: git_outputs[args[1]])
    monkeypatch.setattr("sys.argv", [
        "prepare_context.py", "--collector-archive", str(archive),
        "--setuptools-wheel", str(wheel), "--output", str(output),
    ])

    packaging.main()

    assert {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()} == {
        "app/main.py", "collector.local.json", packaging.ARCHIVE_NAME, packaging.TOOLS_NAME,
        "Dockerfile", "verify_image.py", "provenance.json", ".dockerignore", "SHA256SUMS",
    }
    assert json.loads((output / "collector.local.json").read_text())["useSharedRequestSession"] is True
    assert (
        "COPY --chown=mcegold:mcegold collector.local.json /app/templates/collector.local.json"
        in (output / "Dockerfile").read_text()
    )
    assert "!collector.local.json\n" in (output / ".dockerignore").read_text()
    for line in (output / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest


def test_single_image_supervisor_manages_portal_and_collector() -> None:
    config = read("docker/single-image/supervisord.conf")

    assert "[program:portal]" in config
    assert "uvicorn app.main:app --host 0.0.0.0 --port 8000" in config
    assert "[program:collector]" in config
    assert "mcegold-wait-for-portal-db" in config
    assert (
        "mcegold-publication-collector /config/collector.local.json"
        in config
    )
    assert "[program:grafana]" in config
    assert "/usr/share/grafana/bin/grafana server" in config
    assert "--config=/etc/grafana/grafana.ini" in config
    assert "stopasgroup=true" in config
    assert "killasgroup=true" in config
    assert "stdout_logfile=/dev/stdout" in config
    assert "stderr_logfile=/dev/stderr" in config


def test_single_image_entrypoint_seeds_config_without_overwriting_mounts() -> None:
    entrypoint = read(
        "docker/single-image/bin/mcegold-single-image-entrypoint"
    )

    assert 'if [ ! -f "$target_path" ]; then' in entrypoint
    assert "/config/portal.local.json" in entrypoint
    assert "/config/collector.local.json" in entrypoint
    assert "/config/connector.config.json" in entrypoint

    assert (
        'export GF_SECURITY_ADMIN_USER="${GF_SECURITY_ADMIN_USER:-admin}"'
        in entrypoint
    )
    assert (
        'export GF_SECURITY_ADMIN_PASSWORD='
        '"${GF_SECURITY_ADMIN_PASSWORD:-admin}"'
        in entrypoint
    )

    assert "/config/grafana.admin.password" not in entrypoint
    assert "secrets.token_urlsafe" not in entrypoint


def test_single_image_grafana_config_uses_appliance_paths() -> None:
    config = read("docker/single-image/grafana.ini")

    assert "data = /data/grafana" in config
    assert "logs = /var/log/grafana" in config
    assert "plugins = /var/lib/grafana/plugins" in config
    assert "provisioning = /etc/grafana/provisioning" in config

    assert "http_addr = 0.0.0.0" in config
    assert "http_port = 3000" in config

    assert "preinstall_disabled = true" in config
    assert "preinstall_auto_update = false" in config
    assert "plugin_admin_enabled = false" in config
    assert "plugin_admin_external_manage_enabled = false" in config

    assert "admin_password" not in config
    assert "anonymous" not in config


def test_single_image_wait_gate_checks_portal_owned_schema() -> None:
    gate = read("docker/single-image/bin/mcegold-wait-for-portal-db")

    assert "MCEGOLD_DISCOVERY_DATABASE_PATH" in gate
    assert "ApplicationSetting" in gate
    assert "CollectorRuntimeStatus" in gate
    assert "FactMeasurement" in gate
    assert "SchemaVersion" in gate
    assert "version < 17" in gate


def test_single_image_connector_template_uses_blank_channels() -> None:
    template = json.loads(
        read("docker/single-image/templates/connector.config.json")
    )

    assert template["request"]["channel"] == ""
    assert template["request"]["readResponse"] is True
    assert template["request"]["removeResponseOnSuccess"] is False
    assert template["publication"]["channel"] == ""


def test_single_image_portal_template_uses_release_defaults() -> None:
    template = json.loads(
        read("docker/single-image/templates/portal.local.json")
    )

    assert template["adminControlsEnabled"] is True
    assert (
        template["grafanaDashboardUrl"]
        == "http://localhost:3000/d/bfvnuobjmh3wgc/mcegold-operations?orgId=1&kiosk"
    )


def test_public_portal_example_uses_release_defaults() -> None:
    template = json.loads(
        read("configs/portal.local.example.json")
    )

    assert template["adminControlsEnabled"] is True
    assert (
        template["grafanaDashboardUrl"]
        == "http://localhost:3000/d/bfvnuobjmh3wgc/mcegold-operations?orgId=1&kiosk"
    )
