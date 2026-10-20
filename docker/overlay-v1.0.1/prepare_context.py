"""Prepare an allowlisted context; never invokes Docker or installs packages."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
import urllib.request


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARCHIVE_NAME = "MCEGold.Discovery.PublicationCollector-v1.0.1.tar.gz"
ARCHIVE_SHA256 = "d3e1af3d43301663facf5870d9d74f74338ea8884976c2c67f0e9bd75ff0316f"
TOOLS_NAME = "setuptools-83.0.0-py3-none-any.whl"
TOOLS_SHA256 = "29b23c360f22f414dc7336bb39178cc7bcbf6021ed2733cde173f09dba19abb3"
TOOLS_URL = (
    "https://files.pythonhosted.org/packages/5d/40/"
    "e1e72872c6354b306daef1703549e8e83b4d43cfea356311bf722a043752/" + TOOLS_NAME
)
BASE_ID = "sha256:9bd95ef98d8744347c7d644033c26942b5aba5a6e9f9d6d28427a7a0bd77c30f"
EPOCH = 1791331200
COLLECTOR_TEMPLATE = ROOT / "docker/single-image/templates/collector.local.json"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def collector_template_bytes() -> bytes:
    """Allow only the public appliance defaults, never a deployed config file."""
    require(COLLECTOR_TEMPLATE.is_file() and not COLLECTOR_TEMPLATE.is_symlink(),
            "Collector release template is missing or linked")
    data = COLLECTOR_TEMPLATE.read_bytes().replace(b"\r\n", b"\n")
    values = json.loads(data)
    require(values == {
        "cliPath": "/opt/mcegold-cli/MCEGold.Data.Services.Connector.Cli",
        "connectorConfigPath": "/config/connector.config.json",
        "discoveryDatabasePath": "/data/discovery_portal.db",
        "pollingIntervalSeconds": 15,
        "logLevel": "INFO",
        "cliTimeoutSeconds": 60,
        "includeRaw": False,
        "useSharedRequestSession": True,
    } and values.get("useSharedRequestSession") is True,
        "Collector release template must contain only the public v1.0.1 defaults")
    return data


def portal_files() -> list[Path]:
    # Copy only tracked application files, using current checkout bytes.
    names = subprocess.check_output(
        ["git", "ls-files", "-z", "--", "app/"], cwd=ROOT
    ).decode().split("\0")
    files = []
    for name in filter(None, names):
        path = ROOT / name
        require(path.is_file() and not path.is_symlink(), f"Missing or linked app file: {name}")
        require(path.resolve().is_relative_to(ROOT / "app"), f"App file escapes tree: {name}")
        lower = path.name.lower()
        require(
            path.suffix.lower() not in {".db", ".sqlite", ".sqlite3", ".pyc", ".pyo"}
            and not lower.endswith((".db-wal", ".db-shm", ".local.json"))
            and not lower.startswith(".env"),
            f"Runtime data is not allowed in the application context: {name}",
        )
        if path.suffix == ".py":
            ast.parse(path.read_bytes(), filename=name)
        files.append(path)
    require(bool(files), "No tracked Portal app files found")
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "-z", "--", "app/"], cwd=ROOT
    )
    require(not untracked, "Untracked app files exist; review and add them before preparing the context")
    return sorted(files)


def check_archive(path: Path) -> None:
    require(sha256(path) == ARCHIVE_SHA256, "Collector archive SHA-256 mismatch")
    prefix = "MCEGold.Discovery.PublicationCollector-v1.0.1/"
    with tarfile.open(path, "r:gz") as archive:
        metadata = archive.extractfile(prefix + "pyproject.toml")
        require(metadata is not None, "Collector pyproject.toml missing")
        project = tomllib.loads(metadata.read().decode())["project"]
        require(project["version"] == "1.0.1", "Collector version mismatch")
        require(project.get("dependencies", []) == [], "Unexpected Collector dependencies")
        require(
            prefix + "src/mcegold_discovery_publication_collector/request_session_settings.py"
            in archive.getnames(), "request_session_settings.py missing",
        )
        for member in archive.getmembers():
            if member.isfile() and member.name.endswith(".py"):
                ast.parse(archive.extractfile(member).read(), filename=member.name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collector-archive", type=Path, required=True,
                        help="Publisher-provided Collector v1.0.1 archive (hash verified)")
    parser.add_argument("--output", type=Path, help="New context directory; defaults to a temporary directory")
    parser.add_argument("--setuptools-wheel", type=Path, help="Use a previously downloaded, hash-verified wheel")
    parser.add_argument("--check-only", action="store_true", help="Check app, template and archive; no writes or downloads")
    args = parser.parse_args()
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT).decode().strip()
    require(branch == "staging", f"Expected staging checkout, found {branch!r}")
    files = portal_files()
    template = collector_template_bytes()
    check_archive(args.collector_archive)
    if args.check_only:
        print(f"Validated {len(files)} Portal files, Collector template and v1.0.1 archive; no context created")
        return

    if args.output:
        context = args.output.resolve()
        context.mkdir(parents=True, exist_ok=False)
    else:
        context = Path(tempfile.mkdtemp(prefix="mcegold-discovery-v1.0.1-"))
    # Keep a failed context for diagnosis; never delete a user-supplied directory.
    print(f"Context: {context}", flush=True)
    for source in files:
        target = context / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    shutil.copyfile(args.collector_archive, context / ARCHIVE_NAME)
    (context / "collector.local.json").write_bytes(template)
    for name in ("Dockerfile", "verify_image.py"):
        # Normalize packaging text across Windows and Linux checkouts.
        (context / name).write_bytes((HERE / name).read_bytes().replace(b"\r\n", b"\n"))
    wheel = context / TOOLS_NAME
    if args.setuptools_wheel:
        shutil.copyfile(args.setuptools_wheel, wheel)
    else:
        with urllib.request.urlopen(TOOLS_URL, timeout=60) as response, wheel.open("wb") as target:
            shutil.copyfileobj(response, target)
    require(sha256(wheel) == TOOLS_SHA256, "Setuptools wheel SHA-256 mismatch")
    provenance = {
        "base_image": "mcegold-discovery:1.0.0", "base_image_id": BASE_ID,
        "portal_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "portal_status": subprocess.check_output(["git", "status", "--porcelain", "--", "app/"], cwd=ROOT).decode(),
        "collector_sha256": ARCHIVE_SHA256, "source_date_epoch": EPOCH,
    }
    (context / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    # Root deny-all with explicit allowlist prevents accidentally added files entering a later build.
    (context / ".dockerignore").write_text(
        "**\n!Dockerfile\n!.dockerignore\n!SHA256SUMS\n!provenance.json\n"
        f"!verify_image.py\n!collector.local.json\n!app/\n!app/**\n!{ARCHIVE_NAME}\n!{TOOLS_NAME}\n", encoding="utf-8"
    )
    entries = sorted(path for path in context.rglob("*") if path.is_file())
    sums = "".join(f"{sha256(path)}  {path.relative_to(context).as_posix()}\n" for path in entries)
    (context / "SHA256SUMS").write_text(sums, encoding="utf-8", newline="\n")
    for path in context.rglob("*"):
        os.chmod(path, 0o755 if path.is_dir() else 0o644)
        os.utime(path, (EPOCH, EPOCH))
    print("Context ready; preserve it and SHA256SUMS to reproduce these inputs. Docker was not invoked.")


if __name__ == "__main__":
    main()
