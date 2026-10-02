import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PORTAL_LOCAL_CONFIG_PATH = os.getenv("PORTAL_LOCAL_CONFIG_PATH", "configs/portal.local.json")
ADMIN_CONTROLS_ENABLED_LOCAL_KEY = "adminControlsEnabled"
PORTAL_LOCAL_CONFIG_FIELDS = {
    "mcegold_data_services_url": {
        "env": "MCEGOLD_HOST",
        "local": "mcegoldDataServicesUrl",
        "default": "",
    },
    "mcegold_username": {
        "env": "MCEGOLD_USERNAME",
        "local": "mcegoldUsername",
        "default": "",
    },
    "mcegold_password": {
        "env": "MCEGOLD_PASSWORD",
        "local": "mcegoldPassword",
        "default": "",
    },
    "mcegold_api_key": {
        "env": "MCEGOLD_API_KEY",
        "local": "mcegoldApiKey",
        "default": "",
    },
    "mcegold_cli_path": {
        "env": "MCEGOLD_CLI_PATH",
        "local": "mcegoldCliPath",
        "default": "",
    },
    "connector_config_path": {
        "env": "CONNECTOR_CONFIG_PATH",
        "local": "connectorConfigPath",
        "default": "configs/connector.config.json",
    },
    "discovery_database_path": {
        "env": "DISCOVERY_DATABASE_PATH",
        "local": "discoveryDatabasePath",
        "default": "data/discovery_portal.db",
    },
    "grafana_dashboard_url": {
        "env": "GRAFANA_DASHBOARD_URL",
        "local": "grafanaDashboardUrl",
        "default": "http://127.0.0.1:3000/d/bfvnuobjmh3wgc/mcegold-operations?kiosk",
    },
}

MCEGOLD_DATA_SERVICES_FIELDS = {
    "mcegold_data_services_url",
    "mcegold_username",
    "mcegold_password",
    "mcegold_api_key",
}

MCEGOLD_SECRET_FIELDS = {"mcegold_password", "mcegold_api_key"}

CONNECTOR_CONFIG_DEFAULTS: dict[str, Any] = {
    "host": "",
    "authenticationScheme": "BasicApi",
    "apiKey": "",
    "userName": "",
    "password": "",
    "request": {
        "channel": "",
        "readResponse": True,
        "removeResponseOnSuccess": False,
    },
    "publication": {
        "channel": "",
    },
}

CONNECTOR_CONFIG_PORTAL_FIELD_MAP = {
    "mcegoldDataServicesUrl": "host",
    "mcegoldUsername": "userName",
    "mcegoldPassword": "password",
    "mcegoldApiKey": "apiKey",
}


class ConnectorConfigSyncError(RuntimeError):
    pass


def read_portal_local_config(path: str | Path = PORTAL_LOCAL_CONFIG_PATH) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


_LOCAL_CONFIG = read_portal_local_config(PORTAL_LOCAL_CONFIG_PATH)


def write_portal_local_config(values: dict[str, Any], path: str | Path = PORTAL_LOCAL_CONFIG_PATH) -> None:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json_replace(config_path, values)


def synchronize_connector_config_from_portal(
    portal_config: dict[str, Any],
    connector_config_path: str | Path,
) -> None:
    config_path = Path(connector_config_path)
    try:
        connector_config = _read_connector_config_for_update(config_path)
        for portal_key, connector_key in CONNECTOR_CONFIG_PORTAL_FIELD_MAP.items():
            connector_config[connector_key] = str(portal_config.get(portal_key) or "")
        connector_config["authenticationScheme"] = str(
            connector_config.get("authenticationScheme") or CONNECTOR_CONFIG_DEFAULTS["authenticationScheme"]
        )
        _merge_connector_section(connector_config, "request")
        _merge_connector_section(connector_config, "publication")
        _write_json_replace(config_path, connector_config)
    except ConnectorConfigSyncError:
        raise
    except OSError as exc:
        raise ConnectorConfigSyncError("Connector configuration could not be saved.") from exc
    except (TypeError, ValueError) as exc:
        raise ConnectorConfigSyncError("Connector configuration could not be saved.") from exc


def _read_connector_config_for_update(path: Path) -> dict[str, Any]:
    if not path.exists():
        return json.loads(json.dumps(CONNECTOR_CONFIG_DEFAULTS))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConnectorConfigSyncError("Connector configuration is not valid JSON.") from exc
    except OSError as exc:
        raise ConnectorConfigSyncError("Connector configuration could not be read.") from exc
    if not isinstance(data, dict):
        raise ConnectorConfigSyncError("Connector configuration root must be a JSON object.")
    return data


def _merge_connector_section(connector_config: dict[str, Any], section_name: str) -> None:
    defaults = CONNECTOR_CONFIG_DEFAULTS[section_name]
    existing = connector_config.get(section_name)
    section = existing if isinstance(existing, dict) else {}
    for key, value in defaults.items():
        section.setdefault(key, value)
    connector_config[section_name] = section


def _write_json_replace(path: Path, values: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    try:
        temp_path.write_text(json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp_path, path)
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        finally:
            raise


def resolve_portal_config_value(
    field_name: str,
    local_config: dict[str, Any] | None = None,
) -> tuple[str, str]:
    definition = PORTAL_LOCAL_CONFIG_FIELDS[field_name]
    env_name = str(definition["env"])
    local_key = str(definition["local"])
    default = str(definition["default"])
    env_value = os.getenv(env_name)
    if env_value not in (None, ""):
        return env_value, "environment variable"
    data = _LOCAL_CONFIG if local_config is None else local_config
    local_value = data.get(local_key)
    if local_value not in (None, ""):
        return str(local_value), "local config"
    return default, "default"


def resolve_admin_controls_enabled(
    local_config: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    data = _LOCAL_CONFIG if local_config is None else local_config
    local_value = _parse_bool_value(data.get(ADMIN_CONTROLS_ENABLED_LOCAL_KEY))
    if local_value is not None:
        return local_value, "local config"
    return True, "default"


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def resolve_data_services_environment(
    local_config: dict[str, Any] | None = None,
) -> dict[str, str]:
    environment: dict[str, str] = {}
    for field_name in MCEGOLD_DATA_SERVICES_FIELDS:
        value, _ = resolve_portal_config_value(field_name, local_config)
        if value:
            environment[str(PORTAL_LOCAL_CONFIG_FIELDS[field_name]["env"])] = value
    return environment


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _parse_bool_value(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return None


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "MCEGold Discovery Portal")
    portal_local_config_path: str = PORTAL_LOCAL_CONFIG_PATH
    mcegold_data_services_url: str = resolve_portal_config_value("mcegold_data_services_url")[0]
    mcegold_username: str = resolve_portal_config_value("mcegold_username")[0]
    mcegold_password: str = resolve_portal_config_value("mcegold_password")[0]
    mcegold_api_key: str = resolve_portal_config_value("mcegold_api_key")[0]
    mcegold_cli_path: str = resolve_portal_config_value("mcegold_cli_path")[0]
    mcegold_cli_timeout_seconds: int = _int_env("MCEGOLD_CLI_TIMEOUT_SECONDS", 60)
    mcegold_cli_get_sites_max_items: int = _int_env("MCEGOLD_CLI_GET_SITES_MAX_ITEMS", 100)
    discovery_default_segments_max_items: int = _int_env("DISCOVERY_DEFAULT_SEGMENTS_MAX_ITEMS", 25)
    discovery_default_measurement_locations_max_items: int = _int_env(
        "DISCOVERY_DEFAULT_MEASUREMENT_LOCATIONS_MAX_ITEMS", 25
    )
    discovery_default_measurements_max_items: int = _int_env(
        "DISCOVERY_DEFAULT_MEASUREMENTS_MAX_ITEMS", 50
    )
    discovery_limit_segments_max_items: int = _int_env("DISCOVERY_LIMIT_SEGMENTS_MAX_ITEMS", 100)
    discovery_limit_measurement_locations_max_items: int = _int_env(
        "DISCOVERY_LIMIT_MEASUREMENT_LOCATIONS_MAX_ITEMS", 100
    )
    discovery_limit_measurements_max_items: int = _int_env(
        "DISCOVERY_LIMIT_MEASUREMENTS_MAX_ITEMS", 250
    )
    mcegold_cli_get_segments_max_items: int = _int_env("MCEGOLD_CLI_GET_SEGMENTS_MAX_ITEMS", discovery_default_segments_max_items)
    mcegold_cli_get_measurement_locations_max_items: int = _int_env(
        "MCEGOLD_CLI_GET_MEASUREMENT_LOCATIONS_MAX_ITEMS", discovery_default_measurement_locations_max_items
    )
    mcegold_cli_get_measurements_max_items: int = _int_env(
        "MCEGOLD_CLI_GET_MEASUREMENTS_MAX_ITEMS", discovery_default_measurements_max_items
    )
    mcegold_cli_include_raw: bool = _bool_env("MCEGOLD_CLI_INCLUDE_RAW", False)
    session_secret_key: str = os.getenv(
        "SESSION_SECRET_KEY", "dev-only-change-this-session-secret"
    )
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///data/discovery.db")
    discovery_database_path: str = resolve_portal_config_value("discovery_database_path")[0]
    connector_config_path: str = resolve_portal_config_value("connector_config_path")[0]
    grafana_dashboard_url: str = resolve_portal_config_value("grafana_dashboard_url")[0]
    admin_controls_enabled: bool = resolve_admin_controls_enabled()[0]
    reference_data_path: str = os.getenv(
        "REFERENCE_DATA_PATH", "docs/CCOM Reference Data.xml"
    )
    reference_data_sheet: str = os.getenv(
        "REFERENCE_DATA_SHEET", "CCOM Reference Data"
    )
    reference_data_load_mode: str = os.getenv("REFERENCE_DATA_LOAD_MODE", "startup")
    reference_class_segment_types: str = os.getenv("REFERENCE_CLASS_SEGMENT_TYPES", "SegmentType")
    reference_class_measurement_location_types: str = os.getenv(
        "REFERENCE_CLASS_MEASUREMENT_LOCATION_TYPES", "MeasurementLocationType"
    )
    reference_class_measurement_types: str = os.getenv(
        "REFERENCE_CLASS_MEASUREMENT_TYPES", "MeasurementSourceType"
    )
    reference_class_units_of_measure: str = os.getenv(
        "REFERENCE_CLASS_UNITS_OF_MEASURE", "UnitOfMeasure"
    )


settings = Settings()
