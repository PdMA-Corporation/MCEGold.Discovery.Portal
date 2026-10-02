from pathlib import Path
import json


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_single_image_dockerfile_uses_supervisor_and_collector_named_context() -> None:
    dockerfile = read("Dockerfile.single-image")

    assert "FROM python:3.12-slim-bookworm AS runtime" in dockerfile
    assert "supervisor" in dockerfile
    assert "apt-get install -y --no-install-recommends ca-certificates libicu72 supervisor" in dockerfile
    assert "COPY --from=collector-source pyproject.toml README.md /tmp/collector/" in dockerfile
    assert "pip install --no-cache-dir /tmp/collector" in dockerfile
    assert "COPY --from=connector-cli-package mcegold-python-linux-x64-v1.0.0.tar.gz" in dockerfile
    assert "tar -xzf /tmp/connector-cli.tar.gz -C /opt/mcegold-cli --strip-components=1" in dockerfile
    assert "rm /tmp/connector-cli.tar.gz" in dockerfile
    assert "chmod 0755 /opt/mcegold-cli/MCEGold.Data.Services.Connector.Cli" in dockerfile
    assert "test -x /opt/mcegold-cli/MCEGold.Data.Services.Connector.Cli" in dockerfile
    assert "EXPOSE 8000" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "/health" in dockerfile
    assert "USER mcegold" in dockerfile
    assert "3000" not in dockerfile
    assert "grafana" not in dockerfile.lower()
    assert "dotnet-install" not in dockerfile
    assert "dotnet-runtime" not in dockerfile
    assert "aspnetcore-runtime" not in dockerfile


def test_single_image_authoritative_cli_path_is_consistent() -> None:
    dockerfile = read("Dockerfile.single-image")
    portal_template = json.loads(read("docker/single-image/templates/portal.local.json"))
    collector_template = json.loads(read("docker/single-image/templates/collector.local.json"))

    cli_path = "/opt/mcegold-cli/MCEGold.Data.Services.Connector.Cli"
    assert f"MCEGOLD_CLI_PATH={cli_path}" in dockerfile
    assert portal_template["mcegoldCliPath"] == cli_path
    assert collector_template["cliPath"] == cli_path


def test_single_image_supervisor_manages_portal_and_collector() -> None:
    config = read("docker/single-image/supervisord.conf")

    assert "[program:portal]" in config
    assert "uvicorn app.main:app --host 0.0.0.0 --port 8000" in config
    assert "[program:collector]" in config
    assert "mcegold-wait-for-portal-db" in config
    assert "mcegold-publication-collector /config/collector.local.json" in config
    assert "stopasgroup=true" in config
    assert "killasgroup=true" in config
    assert "stdout_logfile=/dev/stdout" in config
    assert "stderr_logfile=/dev/stderr" in config


def test_single_image_entrypoint_seeds_config_without_overwriting_mounts() -> None:
    entrypoint = read("docker/single-image/bin/mcegold-single-image-entrypoint")

    assert 'if [ ! -f "$target_path" ]; then' in entrypoint
    assert "/config/portal.local.json" in entrypoint
    assert "/config/collector.local.json" in entrypoint
    assert "/config/connector.config.json" in entrypoint


def test_single_image_wait_gate_checks_portal_owned_schema() -> None:
    gate = read("docker/single-image/bin/mcegold-wait-for-portal-db")

    assert "MCEGOLD_DISCOVERY_DATABASE_PATH" in gate
    assert "ApplicationSetting" in gate
    assert "CollectorRuntimeStatus" in gate
    assert "FactMeasurement" in gate
    assert "SchemaVersion" in gate
    assert "version < 17" in gate


def test_single_image_connector_template_uses_blank_channels() -> None:
    template = json.loads(read("docker/single-image/templates/connector.config.json"))

    assert template["request"]["channel"] == ""
    assert template["request"]["readResponse"] is True
    assert template["request"]["removeResponseOnSuccess"] is False
    assert template["publication"]["channel"] == ""
