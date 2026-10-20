"""Offline image smoke checks. Operational /config and /data are never opened."""
from importlib import import_module, metadata
from pathlib import Path
import json
import os
import pkgutil
import tempfile


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    # Avoid even reading deployed config when this script is run after a build.
    with tempfile.TemporaryDirectory(prefix="mcegold-overlay-check-") as temporary:
        root = Path(temporary)
        os.environ["PORTAL_LOCAL_CONFIG_PATH"] = str(root / "absent-portal.json")
        os.environ["CONNECTOR_CONFIG_PATH"] = str(root / "absent-connector.json")
        os.environ["MCEGOLD_COLLECTOR_CONFIG"] = str(root / "absent-collector.json")
        os.environ["DISCOVERY_DATABASE_PATH"] = str(root / "shared.db")
        os.environ["MCEGOLD_DISCOVERY_DATABASE_PATH"] = str(root / "shared.db")
        import app

        for module in pkgutil.walk_packages(app.__path__, app.__name__ + "."):
            import_module(module.name)
        require(metadata.version("mcegold-discovery-publication-collector") == "1.0.1", "Wrong Collector version")
        collector = import_module("mcegold_discovery_publication_collector")
        require(Path(collector.__file__).parent == Path(
            "/usr/local/lib/python3.12/site-packages/mcegold_discovery_publication_collector"
        ), "Collector installed outside the inherited Python environment")
        from mcegold_discovery_publication_collector.configuration import CollectorConfig, load_config

        template_path = Path("/app/templates/collector.local.json")
        template = json.loads(template_path.read_text(encoding="utf-8"))
        require(template.get("useSharedRequestSession") is True,
                "Combined image must enable Shared Request Session by default")
        require(load_config(str(template_path), env={"PACKAGING_CHECK": "1"}).use_shared_request_session is True,
                "Collector does not load the combined image's shared-session default")
        require(CollectorConfig("unused-cli", "unused-config").use_shared_request_session is False,
                "Standalone Collector default must remain false")
        session = import_module("mcegold_discovery_publication_collector.request_session_settings")
        require(Path(session.__file__).is_file(), "request_session_settings.py missing")
        entrypoints = metadata.distribution("mcegold-discovery-publication-collector").entry_points
        require(any(e.name == "mcegold-publication-collector" and e.load() for e in entrypoints), "Collector CLI entrypoint missing")
        from app.storage.database import initialize_database
        from app.storage.application_settings import ApplicationSettingsRepository
        from app.storage.collector_runtime_status import CollectorRuntimeStatusRepository
        from mcegold_discovery_publication_collector.runtime_status import CollectorRuntimeStatusStore

        database = root / "shared.db"
        initialize_database(database)
        portal = ApplicationSettingsRepository(database)
        portal.set_request_session("overlay-check-session", "2026-10-19T00:00:00Z")
        require(session.PortalRequestSessionReader(str(database)).read() == "overlay-check-session",
                "Collector cannot read the Portal session from shared SQLite")
        CollectorRuntimeStatusStore(str(database)).mark_running()
        status = CollectorRuntimeStatusRepository(database).get_publication_collector_status()
        require(status is not None and status.runtime_state == "Running",
                "Portal cannot read Collector status from shared SQLite")
    print("PASS: Portal imports, Collector 1.0.1 metadata/module/CLI, combined/standalone defaults, bidirectional shared SQLite access")


if __name__ == "__main__":
    main()
