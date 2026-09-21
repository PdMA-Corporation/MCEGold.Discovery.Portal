import logging
import sqlite3
import threading
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.config import (
    MCEGOLD_DATA_SERVICES_FIELDS,
    MCEGOLD_SECRET_FIELDS,
    PORTAL_LOCAL_CONFIG_FIELDS,
    read_portal_local_config,
    resolve_portal_config_value,
    resolve_data_services_environment,
    settings,
    write_portal_local_config,
)
from app.models import Measurement, MeasurementLocation, Segment, Site
from app.services.discovery_client import DiscoveryClient
from app.services.collector_runtime_status_service import (
    CollectorStatusView,
    get_publication_collector_status,
)
from app.services.mcegold_cli_discovery_client import CliDiscoveryError, MceGoldCliDiscoveryClient
from app.services.measurement_discovery_service import MeasurementDiscoveryService
from app.services.measurement_location_discovery_service import MeasurementLocationDiscoveryService
from app.services.segment_discovery_service import SegmentDiscoveryService
from app.services.site_discovery_service import SiteDiscoveryService
from app.storage.discovered_entity_store import DiscoveredEntityStore
from app.storage.application_settings import (
    ApplicationSettingError,
    ApplicationSettingsRepository,
    DATA_RETENTION_DAYS_VALIDATION_MESSAGE,
    DATA_RETENTION_MAX_DAYS,
    DATA_RETENTION_MIN_DAYS,
    ENERGY_COST_RATE_VALIDATION_MESSAGE,
    validate_energy_cost_rate,
)
from app.storage.reference_data_repository import (
    get_currency_unit_entries,
    get_measurement_location_type_entries,
    get_reference_data_status,
    get_segment_type_entries,
    get_unit_of_measure_entries,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger("mcegold.discovery")
discovery_session_lock = threading.Lock()

COLLECTOR_STATUS_BADGE_CLASSES = {
    "Running": "text-bg-success",
    "Idle": "text-bg-info",
    "Error": "text-bg-danger",
    "Offline": "text-bg-secondary",
}

COLLECTOR_STATUS_MESSAGES = {
    "Running": "Collector process is alive and publication polling is active.",
    "Idle": "Collector process is alive and publication polling is paused.",
    "Error": "Collector process is alive and reported an operational error.",
}


def page_context(request: Request, **values: object) -> dict[str, object]:
    return {
        "request": request,
        "settings": settings,
        "reference_data_status": get_reference_data_status(get_database_path(request)),
        "connector_status": get_connector_status(request),
        "discovery_session": get_discovery_session_status(request),
        **values,
    }


def create_discovery_client() -> DiscoveryClient:
    local_config = read_portal_local_config(settings.portal_local_config_path)
    return MceGoldCliDiscoveryClient(
        cli_path=settings.mcegold_cli_path,
        connector_config_path=settings.connector_config_path,
        timeout_seconds=settings.mcegold_cli_timeout_seconds,
        max_items=settings.mcegold_cli_get_sites_max_items,
        segment_max_items=settings.discovery_default_segments_max_items,
        measurement_location_max_items=settings.discovery_default_measurement_locations_max_items,
        measurement_max_items=settings.discovery_default_measurements_max_items,
        include_raw=settings.mcegold_cli_include_raw,
        environment_overrides=resolve_data_services_environment(local_config),
    )


def refresh_saved_portal_settings(local_config: dict[str, str]) -> None:
    for field_name in PORTAL_LOCAL_CONFIG_FIELDS:
        value, _ = resolve_portal_config_value(field_name, local_config)
        object.__setattr__(settings, field_name, value)


def invalidate_cached_discovery_client(request: Request) -> None:
    if hasattr(request.app.state, "discovery_client"):
        delattr(request.app.state, "discovery_client")


def get_discovery_client(request: Request) -> DiscoveryClient:
    client = getattr(request.app.state, "discovery_client", None)
    if client is None:
        client = create_discovery_client()
        request.app.state.discovery_client = client
    return client


def get_site_service(request: Request) -> SiteDiscoveryService:
    return SiteDiscoveryService(get_discovery_client(request))


def get_segment_service(request: Request) -> SegmentDiscoveryService:
    return SegmentDiscoveryService(get_discovery_client(request))


def get_location_service(request: Request) -> MeasurementLocationDiscoveryService:
    return MeasurementLocationDiscoveryService(get_discovery_client(request))


def get_measurement_service(request: Request) -> MeasurementDiscoveryService:
    return MeasurementDiscoveryService(get_discovery_client(request))


def get_connector_status(request: Request) -> dict[str, object]:
    client = get_discovery_client(request)
    if isinstance(client, MceGoldCliDiscoveryClient):
        return client.get_status()
    return {"mode": "cli", "configured": True, "status": "ok", "error": None}


def get_get_sites_diagnostics(request: Request) -> dict[str, object] | None:
    client = get_discovery_client(request)
    if isinstance(client, MceGoldCliDiscoveryClient):
        return client.last_get_sites_diagnostics
    return None


def get_discovery_session_id(request: Request) -> str | None:
    value = getattr(request.app.state, "discovery_session_id", None)
    return str(value) if value else None


def get_discovery_session_status(request: Request) -> dict[str, object]:
    session_id = get_discovery_session_id(request)
    return {
        "active": bool(session_id),
        "sessionId": session_id,
        "shortSessionId": shorten_session_id(session_id),
        "startedAt": getattr(request.app.state, "discovery_started_at", None),
    }


def shorten_session_id(session_id: str | None) -> str:
    if not session_id:
        return ""
    if len(session_id) <= 16:
        return session_id
    return f"{session_id[:6]}...{session_id[-3:]}"


def log_cli_call(request: Request, operation: str) -> None:
    count = getattr(request.state, "cli_call_count", 0) + 1
    request.state.cli_call_count = count
    logger.info(
        "operation=%s session=%s page=%s cliCallCount=%s",
        operation,
        shorten_session_id(get_discovery_session_id(request)),
        request.url.path,
        count,
    )


def mirror_shared_discovery_session(request: Request) -> None:
    session_id = get_discovery_session_id(request)
    if session_id:
        request.session["discovery_session_id"] = session_id
        request.session["discovery_started_at"] = getattr(
            request.app.state,
            "discovery_started_at",
            None,
        )
    else:
        request.session.pop("discovery_session_id", None)
        request.session.pop("discovery_started_at", None)


def require_discovery_session(request: Request):
    if not get_discovery_session_id(request):
        mirror_shared_discovery_session(request)
        return RedirectResponse("/?message=start_discovery", status_code=303)
    mirror_shared_discovery_session(request)
    return None


def set_discovery_session(request: Request, session_id: str) -> None:
    clear_selected_workflow_context(request)
    started_at = datetime.now(timezone.utc).isoformat()
    request.app.state.discovery_session_id = session_id
    request.app.state.discovery_started_at = started_at
    request.session["discovery_session_id"] = session_id
    request.session["discovery_started_at"] = started_at


def refresh_discovery_session(request: Request, session_id: str) -> None:
    started_at = datetime.now(timezone.utc).isoformat()
    request.app.state.discovery_session_id = session_id
    request.app.state.discovery_started_at = started_at
    request.session["discovery_session_id"] = session_id
    request.session["discovery_started_at"] = started_at


def clear_shared_discovery_session(request: Request) -> None:
    if hasattr(request.app.state, "discovery_session_id"):
        delattr(request.app.state, "discovery_session_id")
    if hasattr(request.app.state, "discovery_started_at"):
        delattr(request.app.state, "discovery_started_at")


def clear_discovery_session(request: Request) -> None:
    clear_shared_discovery_session(request)
    request.session.pop("discovery_session_id", None)
    request.session.pop("discovery_started_at", None)
    clear_selected_workflow_context(request)


def clear_selected_workflow_context(request: Request) -> None:
    request.session.pop("selected_site", None)
    request.session.pop("selected_segment", None)
    request.session.pop("selected_measurement_location", None)


def clear_cached_discovery_client(request: Request) -> None:
    if hasattr(request.app.state, "discovery_client"):
        delattr(request.app.state, "discovery_client")


def portal_settings_context(
    request: Request,
    form_values: dict[str, str] | None = None,
    errors: list[str] | None = None,
    saved: bool = False,
) -> dict[str, object]:
    local_config = read_portal_local_config(settings.portal_local_config_path)
    application_settings = application_settings_context(request, form_values)
    collector_status = collector_runtime_status_context(
        request,
        fallback_enabled=bool(application_settings["form"].get("collector_enabled")),
    )
    fields: dict[str, dict[str, object]] = {}
    for field_name, definition in PORTAL_LOCAL_CONFIG_FIELDS.items():
        value, source = resolve_portal_config_value(field_name, local_config)
        if form_values and field_name in form_values:
            value = form_values[field_name]
        warning = ""
        if field_name in {"mcegold_cli_path", "connector_config_path"} and value and not Path(value).exists():
            warning = "Path does not exist on this machine."
        fields[field_name] = {
            "value": "" if field_name in MCEGOLD_SECRET_FIELDS else value,
            "source": source,
            "localKey": definition["local"],
            "env": definition["env"],
            "warning": warning,
            "configured": bool(value),
            "secret": field_name in MCEGOLD_SECRET_FIELDS,
        }
    return {
        "fields": fields,
        "application": application_settings,
        "collector_status": collector_status,
        "errors": errors or [],
        "saved": saved,
        "local_config_path": settings.portal_local_config_path,
    }


def application_settings_repository(request: Request) -> ApplicationSettingsRepository:
    return ApplicationSettingsRepository(get_database_path(request))


def application_settings_context(
    request: Request,
    form_values: dict[str, str] | None = None,
) -> dict[str, object]:
    repository = application_settings_repository(request)
    currencies = get_currency_unit_entries(get_database_path(request))
    currency_names = {entry.uuid: entry.short_name for entry in currencies}

    currency_uuid = repository.get_uuid("EnergyCost.CurrencyUomUuid")
    rate = repository.get_decimal("EnergyCost.RatePerKwh")
    collector_enabled = repository.get_boolean("Collector.Enabled") is True
    polling_interval = repository.get_integer("Collector.PollingIntervalSeconds")
    data_retention_enabled = repository.get_boolean("DataRetention.Enabled") is True
    data_retention_days = repository.get_integer("DataRetention.Days")

    values = {
        "energy_cost_currency_uom_uuid": currency_uuid or "",
        "energy_cost_rate_per_kwh": "" if rate is None else format(rate, "f"),
        "collector_enabled": "on" if collector_enabled else "",
        "collector_polling_interval_seconds": "" if polling_interval is None else str(polling_interval),
        "data_retention_enabled": "on" if data_retention_enabled else "",
        "data_retention_days": "" if data_retention_days is None else str(data_retention_days),
    }
    if form_values:
        for key in values:
            if key in form_values:
                values[key] = form_values[key]

    selected_currency_name = currency_names.get(values["energy_cost_currency_uom_uuid"], "")
    rate_summary = ""
    if values["energy_cost_rate_per_kwh"] and selected_currency_name:
        rate_summary = f"{values['energy_cost_rate_per_kwh']} {selected_currency_name} / kWh"

    return {
        "form": values,
        "currencies": currencies,
        "selected_currency_name": selected_currency_name,
        "rate_summary": rate_summary,
    }


def collector_runtime_status_context(
    request: Request,
    fallback_enabled: bool,
) -> dict[str, object]:
    try:
        status = get_publication_collector_status(get_database_path(request))
    except Exception:
        logger.exception("Failed to read Publication Collector runtime status.")
        return format_collector_runtime_status(
            CollectorStatusView(
                enabled=fallback_enabled,
                runtime_status="Offline",
                last_seen_utc=None,
                last_publication_utc=None,
                last_error_utc=None,
                last_error=None,
            ),
            unavailable=True,
        )
    return format_collector_runtime_status(status)


def format_collector_runtime_status(
    status: CollectorStatusView,
    unavailable: bool = False,
) -> dict[str, object]:
    runtime_status = status.runtime_status
    return {
        "enabled": status.enabled,
        "runtime_status": runtime_status,
        "badge_class": COLLECTOR_STATUS_BADGE_CLASSES.get(runtime_status, "text-bg-secondary"),
        "last_seen": format_collector_timestamp(status.last_seen_utc, empty_label="Never"),
        "last_publication": format_collector_timestamp(status.last_publication_utc, empty_label="None"),
        "last_error": status.last_error,
        "last_error_utc": format_collector_timestamp(status.last_error_utc, empty_label=""),
        "message": collector_status_message(status, unavailable=unavailable),
        "unavailable": unavailable,
    }


def collector_status_message(status: CollectorStatusView, unavailable: bool = False) -> str:
    if unavailable:
        return "Runtime status is temporarily unavailable."
    if status.runtime_status == "Offline":
        if status.enabled:
            return "Collector is enabled, but no active heartbeat is detected."
        return "Collector is disabled and no active heartbeat is detected."
    return COLLECTOR_STATUS_MESSAGES.get(status.runtime_status, "")


def format_collector_timestamp(value: datetime | None, empty_label: str) -> str:
    if value is None:
        return empty_label
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def parse_application_settings_form(
    request: Request,
    form: dict[str, str],
) -> tuple[dict[str, object], dict[str, str], list[str]]:
    repository = application_settings_repository(request)
    current_currency = repository.get_uuid("EnergyCost.CurrencyUomUuid")
    current_rate = repository.get_decimal("EnergyCost.RatePerKwh")
    current_collector_enabled = repository.get_boolean("Collector.Enabled") is True
    current_polling_interval = repository.get_integer("Collector.PollingIntervalSeconds")
    current_data_retention_enabled = repository.get_boolean("DataRetention.Enabled") is True
    current_data_retention_days = repository.get_integer("DataRetention.Days")

    if "application_settings_present" not in form:
        current_values = {
            "EnergyCost.CurrencyUomUuid": current_currency,
            "EnergyCost.RatePerKwh": current_rate,
            "Collector.Enabled": current_collector_enabled,
            "Collector.PollingIntervalSeconds": current_polling_interval,
            "DataRetention.Enabled": current_data_retention_enabled,
            "DataRetention.Days": current_data_retention_days,
        }
        return current_values, {}, []

    currencies = get_currency_unit_entries(get_database_path(request))
    currency_uuids = {entry.uuid for entry in currencies}
    form_values = {
        "energy_cost_currency_uom_uuid": form.get("energy_cost_currency_uom_uuid", "").strip(),
        "energy_cost_rate_per_kwh": form.get("energy_cost_rate_per_kwh", "").strip(),
        "collector_enabled": "on" if form.get("collector_enabled") else "",
        "collector_polling_interval_seconds": form.get("collector_polling_interval_seconds", "").strip(),
        "data_retention_enabled": "on" if form.get("data_retention_enabled") else "",
        "data_retention_days": form.get("data_retention_days", "").strip(),
    }

    collector_enabled = bool(form.get("collector_enabled"))
    data_retention_enabled = bool(form.get("data_retention_enabled"))
    currency_uuid = form_values["energy_cost_currency_uom_uuid"] if "energy_cost_currency_uom_uuid" in form else current_currency
    rate_text = form_values["energy_cost_rate_per_kwh"] if "energy_cost_rate_per_kwh" in form else (
        "" if current_rate is None else format(current_rate, "f")
    )
    polling_text = form_values["collector_polling_interval_seconds"] if "collector_polling_interval_seconds" in form else (
        "" if current_polling_interval is None else str(current_polling_interval)
    )
    retention_days_text = form_values["data_retention_days"] if "data_retention_days" in form else (
        "" if current_data_retention_days is None else str(current_data_retention_days)
    )

    errors: list[str] = []
    rate_value: Decimal | None = None
    polling_interval: int | None = None
    retention_days: int | None = None

    if bool(currency_uuid) != bool(rate_text):
        errors.append("Currency and rate per kWh must either both be configured or both be left blank.")
    if currency_uuid and currency_uuid not in currency_uuids:
        errors.append("Energy Cost currency must be a configured Currency unit of measure.")

    if rate_text:
        try:
            rate_value = Decimal(rate_text)
        except InvalidOperation:
            errors.append("Energy Cost rate per kWh must be a non-negative decimal with no more than 6 decimal places.")
        else:
            try:
                validate_energy_cost_rate(rate_value)
            except ApplicationSettingError:
                errors.append(ENERGY_COST_RATE_VALIDATION_MESSAGE.replace("EnergyCost.RatePerKwh", "Energy Cost rate per kWh"))

    if not polling_text:
        errors.append("Polling interval is required.")
    else:
        try:
            polling_interval = int(polling_text)
        except ValueError:
            errors.append("Polling interval must be a whole number.")
        else:
            if polling_interval <= 0:
                errors.append("Polling interval must be greater than zero.")

    if not retention_days_text:
        errors.append("Data Retention period is required.")
    else:
        try:
            retention_days = int(retention_days_text)
        except ValueError:
            errors.append("Data Retention period must be a whole number.")
        else:
            if not DATA_RETENTION_MIN_DAYS <= retention_days <= DATA_RETENTION_MAX_DAYS:
                errors.append(
                    DATA_RETENTION_DAYS_VALIDATION_MESSAGE.replace("DataRetention.Days", "Data Retention period")
                )

    values = {
        "EnergyCost.CurrencyUomUuid": currency_uuid or None,
        "EnergyCost.RatePerKwh": rate_value,
        "Collector.Enabled": collector_enabled,
        "Collector.PollingIntervalSeconds": polling_interval,
        "DataRetention.Enabled": data_retention_enabled,
        "DataRetention.Days": retention_days,
    }
    return values, form_values, errors


def save_application_settings(request: Request, values: dict[str, object]) -> None:
    repository = application_settings_repository(request)
    for setting_key, value in values.items():
        repository.set_setting(setting_key, value)


def require_admin_controls_enabled() -> None:
    if not settings.admin_controls_enabled:
        raise HTTPException(status_code=404, detail="Not Found")


def is_closed_cli_session_error(exc: CliDiscoveryError) -> bool:
    fault = exc.fault if isinstance(exc.fault, dict) else {}
    text = " ".join(
        str(value)
        for value in (
            fault.get("code"),
            fault.get("message"),
            exc.stderr,
            exc.stdout,
            exc.friendly_message,
        )
        if value
    ).casefold()
    return "session" in text and ("closed" in text or "does not exist" in text)


def reopen_cli_session_for_retry(request: Request) -> str | None:
    client = get_discovery_client(request)
    if not isinstance(client, MceGoldCliDiscoveryClient):
        return None
    session_id = client.open_request_session()
    refresh_discovery_session(request, session_id)
    return session_id


def get_or_open_shared_discovery_session(request: Request, client: DiscoveryClient) -> str:
    with discovery_session_lock:
        session_id = get_discovery_session_id(request)
        if session_id:
            mirror_shared_discovery_session(request)
            clear_selected_workflow_context(request)
            return session_id
        session_id = client.open_request_session()
        set_discovery_session(request, session_id)
        return session_id


def store_selected_site(request: Request, *, uuid: str, name: str, site_type: str) -> None:
    request.session["selected_site"] = {
        "uuid": uuid,
        "name": name,
        "type": site_type,
    }
    request.session.pop("selected_segment", None)
    request.session.pop("selected_measurement_location", None)


def store_selected_segment(request: Request, *, uuid: str, name: str, segment_type: str) -> None:
    request.session["selected_segment"] = {
        "uuid": uuid,
        "name": name,
        "type": segment_type,
    }
    request.session.pop("selected_measurement_location", None)


def store_selected_measurement_location(
    request: Request,
    *,
    uuid: str,
    name: str,
    location_type: str,
    value_class: str,
    unit: str,
) -> None:
    request.session["selected_measurement_location"] = {
        "uuid": uuid,
        "name": name,
        "type": location_type,
        "value_class": value_class,
        "unit": unit,
    }


def get_selected_site(request: Request, expected_uuid: str | None = None) -> Site | None:
    selected = request.session.get("selected_site")
    if not isinstance(selected, dict):
        return None
    uuid = str(selected.get("uuid") or "")
    if not uuid or (expected_uuid and uuid != expected_uuid):
        return None
    return Site(
        site_uuid=uuid,
        site_name=str(selected.get("name") or uuid),
        site_type=str(selected.get("type") or "Unknown"),
        status="",
        region="",
        description="Selected workflow context from this web session.",
    )


def get_selected_segment(
    request: Request,
    *,
    expected_site_uuid: str | None = None,
    expected_segment_uuid: str | None = None,
) -> Segment | None:
    site = get_selected_site(request, expected_site_uuid)
    if site is None:
        return None
    selected = request.session.get("selected_segment")
    if not isinstance(selected, dict):
        return None
    uuid = str(selected.get("uuid") or "")
    if not uuid or (expected_segment_uuid and uuid != expected_segment_uuid):
        return None
    return Segment(
        segment_uuid=uuid,
        site_uuid=site.site_uuid,
        segment_name=str(selected.get("name") or uuid),
        segment_type=str(selected.get("type") or "Unknown"),
        status="",
        description="Selected workflow context from this web session.",
    )


def get_selected_measurement_location(
    request: Request,
    *,
    expected_site_uuid: str | None = None,
    expected_segment_uuid: str | None = None,
    expected_location_uuid: str | None = None,
) -> MeasurementLocation | None:
    segment = get_selected_segment(
        request,
        expected_site_uuid=expected_site_uuid,
        expected_segment_uuid=expected_segment_uuid,
    )
    if segment is None:
        return None
    selected = request.session.get("selected_measurement_location")
    if not isinstance(selected, dict):
        return None
    uuid = str(selected.get("uuid") or "")
    if not uuid or (expected_location_uuid and uuid != expected_location_uuid):
        return None
    return MeasurementLocation(
        location_uuid=uuid,
        segment_uuid=segment.segment_uuid,
        location_name=str(selected.get("name") or uuid),
        location_type=str(selected.get("type") or "Unknown"),
        value_class=str(selected.get("value_class") or ""),
        unit=str(selected.get("unit") or ""),
        description="Selected workflow context from this web session.",
    )


def workflow_context_required_response(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        page_context(
            request,
            home_message=(
                "Please navigate from Sites through the guided workflow so the portal can preserve "
                "selected context without re-querying upstream data."
            ),
        ),
        status_code=409,
    )


async def read_urlencoded_form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[0] if values else "" for key, values in parsed.items()}


def safe_redirect_target(request: Request, fallback: str = "/") -> str:
    referer = request.headers.get("referer", "")
    if not referer:
        return fallback
    parsed = urlparse(referer)
    if not parsed.netloc:
        return referer if referer.startswith("/") else fallback
    if parsed.netloc == request.url.netloc:
        path = parsed.path or fallback
        return f"{path}?{parsed.query}" if parsed.query else path
    return fallback


def normalize_recorded_filter(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    else:
        parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


SEGMENT_MAX_ITEM_OPTIONS = [25, 50, 100]
MEASUREMENT_LOCATION_MAX_ITEM_OPTIONS = [25, 50, 100]
DISCOVERY_MEASUREMENT_PREVIEW_DEFAULT_ITEMS = 10
DISCOVERY_MEASUREMENT_PREVIEW_MAX_ITEMS = 50
MEASUREMENT_MAX_ITEM_OPTIONS = [10, 25, DISCOVERY_MEASUREMENT_PREVIEW_MAX_ITEMS]
MEASUREMENT_PREVIEW_DEFAULT_RANGE = timedelta(hours=24)


def format_max_item_options(options: list[int]) -> str:
    if len(options) == 1:
        return str(options[0])
    return f"{', '.join(str(item) for item in options[:-1])}, or {options[-1]}"


def parse_demo_max_items(
    value: str | None,
    *,
    default: int,
    limit: int,
    options: list[int],
    require_option: bool = True,
) -> tuple[int, str | None]:
    if value is None or not value.strip():
        return default, None
    try:
        parsed = int(value)
    except ValueError:
        return default, "Max Items must be a valid integer."
    if parsed < 1:
        return parsed, "Max Items must be greater than 0."
    if parsed > limit:
        return parsed, f"Max Items cannot exceed {limit}."
    if require_option and parsed not in options:
        return parsed, f"Max Items must be one of {format_max_item_options(options)}."
    return parsed, None


def parse_segment_max_items(value: str | None) -> tuple[int, str | None]:
    return parse_demo_max_items(
        value,
        default=settings.discovery_default_segments_max_items,
        limit=settings.discovery_limit_segments_max_items,
        options=SEGMENT_MAX_ITEM_OPTIONS,
    )


def parse_measurement_location_max_items(value: str | None) -> tuple[int, str | None]:
    return parse_demo_max_items(
        value,
        default=settings.discovery_default_measurement_locations_max_items,
        limit=settings.discovery_limit_measurement_locations_max_items,
        options=MEASUREMENT_LOCATION_MAX_ITEM_OPTIONS,
    )


def parse_measurement_max_items(value: str | None) -> tuple[int, str | None]:
    return parse_demo_max_items(
        value,
        default=DISCOVERY_MEASUREMENT_PREVIEW_DEFAULT_ITEMS,
        limit=DISCOVERY_MEASUREMENT_PREVIEW_MAX_ITEMS,
        options=MEASUREMENT_MAX_ITEM_OPTIONS,
        require_option=False,
    )


def default_measurement_preview_filters() -> tuple[str, str]:
    recorded_to = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    recorded_from = recorded_to - MEASUREMENT_PREVIEW_DEFAULT_RANGE
    return format_measurement_preview_datetime(recorded_from), format_measurement_preview_datetime(recorded_to)


def format_measurement_preview_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")


def validate_measurement_filters(
    recorded_from: str | None,
    recorded_to: str | None,
    max_items: str | None,
) -> tuple[str | None, str | None, int, str | None]:
    try:
        normalized_from = normalize_recorded_filter(recorded_from)
        normalized_to = normalize_recorded_filter(recorded_to)
    except ValueError:
        return None, None, DISCOVERY_MEASUREMENT_PREVIEW_DEFAULT_ITEMS, "Recorded filters must be valid date/time values."
    parsed_max_items, max_items_error = parse_measurement_max_items(max_items)
    if max_items_error:
        return normalized_from, normalized_to, parsed_max_items, max_items_error
    if normalized_from and normalized_to and normalized_from > normalized_to:
        return normalized_from, normalized_to, parsed_max_items, "Recorded From must be earlier than or equal to Recorded To."
    return normalized_from, normalized_to, parsed_max_items, None


def validate_optional_service_url(value: str) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        return "MCEGold Data Services URL must be an absolute HTTPS URL."
    return None


def get_database_path(request: Request) -> str:
    database = getattr(request.app.state, "database", None)
    return str(getattr(database, "db_path", settings.discovery_database_path))


def reference_entry_json(entry) -> dict[str, str | None]:
    return {
        "uuid": entry.uuid,
        "shortName": entry.short_name,
        "fullName": entry.full_name,
        "displayName": entry.display_name,
        "className": entry.class_name,
        "description": entry.description,
    }


def require_site(request: Request, site_uuid: str) -> Site:
    try:
        site = get_site_service(request).get_site(site_uuid, get_discovery_session_id(request))
    except CliDiscoveryError:
        raise
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


def require_segment(request: Request, site_uuid: str, segment_uuid: str) -> Segment:
    require_site(request, site_uuid)
    try:
        segment = next(
            (
                item
                for item in get_segment_service(request).get_segments(
                    site_uuid, discovery_session_id=get_discovery_session_id(request)
                )
                if item.segment_uuid == segment_uuid
            ),
            None,
        )
    except CliDiscoveryError:
        raise
    if segment is None:
        raise HTTPException(status_code=404, detail="Segment not found for this site")
    return segment


def require_location(request: Request, site_uuid: str, segment_uuid: str, location_uuid: str) -> MeasurementLocation:
    require_segment(request, site_uuid, segment_uuid)
    try:
        location = get_location_service(request).get_location(
            location_uuid,
            segment_uuid,
            discovery_session_id=get_discovery_session_id(request),
        )
    except CliDiscoveryError:
        raise
    if location is None or location.segment_uuid != segment_uuid:
        raise HTTPException(status_code=404, detail="Measurement location not found for this segment")
    return location


@router.get("/", response_class=HTMLResponse)
def home(request: Request, message: str | None = None) -> HTMLResponse:
    messages = {
        "start_discovery": "Start discovery to open a request session.",
        "open_failed": "Could not start discovery. The request session was not opened.",
        "close_failed": "Discovery ended, but closing the remote request session reported a warning.",
    }
    return templates.TemplateResponse(
        request,
        "index.html",
        page_context(request, home_message=messages.get(message or "")),
    )


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request) -> HTMLResponse:
    require_admin_controls_enabled()
    return templates.TemplateResponse(
        request,
        "settings.html",
        page_context(request, portal_settings=portal_settings_context(request)),
    )


@router.post("/settings", response_class=HTMLResponse)
async def save_settings(request: Request) -> HTMLResponse:
    require_admin_controls_enabled()
    form = await read_urlencoded_form(request)
    values = {
        "mcegold_data_services_url": form.get("mcegold_data_services_url", "").strip(),
        "mcegold_username": form.get("mcegold_username", "").strip(),
        "mcegold_cli_path": form.get("mcegold_cli_path", "").strip(),
        "connector_config_path": form.get("connector_config_path", "").strip(),
        "discovery_database_path": form.get("discovery_database_path", "").strip(),
        "grafana_dashboard_url": form.get("grafana_dashboard_url", settings.grafana_dashboard_url).strip(),
    }
    secret_values = {
        "mcegold_password": form.get("mcegold_password", ""),
        "mcegold_api_key": form.get("mcegold_api_key", ""),
    }
    clear_secrets = {
        "mcegold_password": bool(form.get("clear_mcegold_password")),
        "mcegold_api_key": bool(form.get("clear_mcegold_api_key")),
    }
    application_values, application_form_values, application_errors = parse_application_settings_form(request, form)
    errors: list[str] = []
    if not values["mcegold_cli_path"]:
        errors.append("MCEGold CLI executable path is required.")
    if not values["connector_config_path"]:
        errors.append("Connector config path is required.")
    if not values["discovery_database_path"]:
        errors.append("SQLite database path is required.")
    if not values["grafana_dashboard_url"]:
        errors.append("Grafana dashboard URL is required.")
    service_url_error = validate_optional_service_url(values["mcegold_data_services_url"])
    if service_url_error:
        errors.append(service_url_error)
    errors.extend(application_errors)

    if errors:
        return templates.TemplateResponse(
            request,
            "settings.html",
            page_context(
                request,
                portal_settings=portal_settings_context(
                    request,
                    form_values=values | application_form_values,
                    errors=errors,
                ),
            ),
            status_code=400,
        )

    local_config = read_portal_local_config(settings.portal_local_config_path)
    for field_name, value in values.items():
        local_key = str(PORTAL_LOCAL_CONFIG_FIELDS[field_name]["local"])
        if field_name in MCEGOLD_DATA_SERVICES_FIELDS and not value:
            local_config.pop(local_key, None)
        else:
            local_config[local_key] = value
    for field_name, value in secret_values.items():
        local_key = str(PORTAL_LOCAL_CONFIG_FIELDS[field_name]["local"])
        if clear_secrets[field_name]:
            local_config.pop(local_key, None)
        elif value:
            local_config[local_key] = value
    write_portal_local_config(local_config, settings.portal_local_config_path)
    try:
        save_application_settings(request, application_values)
    except ApplicationSettingError as exc:
        return templates.TemplateResponse(
            request,
            "settings.html",
            page_context(
                request,
                portal_settings=portal_settings_context(
                    request,
                    form_values=values | application_form_values,
                    errors=[str(exc)],
                ),
            ),
            status_code=400,
        )
    refresh_saved_portal_settings(local_config)
    invalidate_cached_discovery_client(request)
    return templates.TemplateResponse(
        request,
        "settings.html",
        page_context(
            request,
            portal_settings=portal_settings_context(request, saved=True),
        ),
    )


@router.post("/discovery/start")
@router.get("/discovery/start", include_in_schema=False)
def start_discovery(request: Request):
    client = get_discovery_client(request)
    if not isinstance(client, MceGoldCliDiscoveryClient):
        client = create_discovery_client()
        request.app.state.discovery_client = client
    try:
        get_or_open_shared_discovery_session(request, client)
    except CliDiscoveryError as exc:
        request.session["discovery_start_error"] = exc.to_safe_dict()
        return RedirectResponse("/?message=open_failed", status_code=303)
    return RedirectResponse("/discovery/sites", status_code=303)


@router.post("/discovery/end")
@router.get("/discovery/end", include_in_schema=False)
def end_discovery(request: Request):
    require_admin_controls_enabled()
    close_failed = False
    session_id = get_discovery_session_id(request)
    if session_id:
        client = get_discovery_client(request)
        if isinstance(client, MceGoldCliDiscoveryClient):
            try:
                client.close_request_session(session_id)
            except CliDiscoveryError:
                close_failed = True
    clear_discovery_session(request)
    target = "/?message=close_failed" if close_failed else "/"
    return RedirectResponse(target, status_code=303)


@router.get("/discovery/sites", response_class=HTMLResponse)
def discovery_sites(request: Request) -> HTMLResponse:
    redirect = require_discovery_session(request)
    if redirect:
        return redirect
    sites: list[Site] = []
    connector_error: dict[str, object] | None = None
    try:
        log_cli_call(request, "GetSites")
        sites = get_site_service(request).get_sites(
            discovery_session_id=get_discovery_session_id(request)
        )
        persist_discovered_sites(request, sites)
    except CliDiscoveryError as exc:
        if is_closed_cli_session_error(exc):
            clear_discovery_session(request)
        connector_error = exc.to_safe_dict()
    return templates.TemplateResponse(
        request,
        "sites.html",
        page_context(
            request,
            sites=sites,
            connector_error=connector_error,
            get_sites_diagnostics=get_get_sites_diagnostics(request),
        ),
    )


def should_persist_discovery_results(request: Request) -> bool:
    return True


def persist_discovered_sites(request: Request, sites: list[Site]) -> None:
    if not sites or not should_persist_discovery_results(request):
        return
    database = getattr(request.app.state, "database", None)
    db_path = getattr(database, "db_path", settings.discovery_database_path)
    try:
        with sqlite3.connect(db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            DiscoveredEntityStore(connection).save_sites(sites)
    except Exception:
        logger.exception("Failed to persist discovered sites.")


def persist_discovered_segments(request: Request, segments: list[Segment]) -> None:
    if not segments or not should_persist_discovery_results(request):
        return
    database = getattr(request.app.state, "database", None)
    db_path = getattr(database, "db_path", settings.discovery_database_path)
    try:
        with sqlite3.connect(db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            DiscoveredEntityStore(connection).save_segments(segments)
    except Exception:
        logger.exception("Failed to persist discovered segments.")


def persist_discovered_measurement_locations(
    request: Request,
    locations: list[MeasurementLocation],
    site_uuid: str,
) -> None:
    if not locations or not should_persist_discovery_results(request):
        return
    database = getattr(request.app.state, "database", None)
    db_path = getattr(database, "db_path", settings.discovery_database_path)
    rows = [location.model_dump() | {"site_uuid": site_uuid} for location in locations]
    try:
        with sqlite3.connect(db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            DiscoveredEntityStore(connection).save_measurement_locations(rows)
    except Exception:
        logger.exception("Failed to persist discovered measurement locations.")


def persist_discovered_measurements(
    request: Request,
    measurements: list[Measurement],
    location: MeasurementLocation,
) -> None:
    if not measurements or not should_persist_discovery_results(request):
        return
    database = getattr(request.app.state, "database", None)
    db_path = getattr(database, "db_path", settings.discovery_database_path)
    rows = [
        measurement.model_dump()
        | {
            "measurement_location_uuid": location.location_uuid,
            "segment_uuid": location.segment_uuid,
            "unit_uuid": location.unit_uuid,
        }
        for measurement in measurements
    ]
    try:
        with sqlite3.connect(db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            DiscoveredEntityStore(connection).save_measurements(rows)
    except Exception:
        logger.exception("Failed to persist discovered measurements.")


@router.post("/discovery/select-site")
async def select_site(request: Request) -> RedirectResponse:
    redirect = require_discovery_session(request)
    if redirect:
        return redirect
    form = await read_urlencoded_form(request)
    site_uuid = form.get("site_uuid", "")
    site_name = form.get("site_name", "")
    site_type = form.get("site_type", "")
    if not site_uuid:
        return RedirectResponse("/discovery/sites", status_code=303)
    store_selected_site(request, uuid=site_uuid, name=site_name, site_type=site_type)
    return RedirectResponse(f"/discovery/sites/{site_uuid}/segments", status_code=303)


@router.post("/discovery/select-segment")
async def select_segment(request: Request) -> RedirectResponse:
    redirect = require_discovery_session(request)
    if redirect:
        return redirect
    form = await read_urlencoded_form(request)
    site_uuid = form.get("site_uuid", "")
    segment_uuid = form.get("segment_uuid", "")
    segment_name = form.get("segment_name", "")
    segment_type = form.get("segment_type", "")
    if not site_uuid or not segment_uuid:
        return RedirectResponse("/discovery/sites", status_code=303)
    if get_selected_site(request, site_uuid) is None:
        return RedirectResponse("/discovery/sites", status_code=303)
    store_selected_segment(
        request,
        uuid=segment_uuid,
        name=segment_name,
        segment_type=segment_type,
    )
    return RedirectResponse(
        f"/discovery/sites/{site_uuid}/segments/{segment_uuid}/measurement-locations",
        status_code=303,
    )


@router.post("/discovery/select-measurement-location")
async def select_measurement_location(request: Request) -> RedirectResponse:
    redirect = require_discovery_session(request)
    if redirect:
        return redirect
    form = await read_urlencoded_form(request)
    site_uuid = form.get("site_uuid", "")
    segment_uuid = form.get("segment_uuid", "")
    location_uuid = form.get("location_uuid", "")
    location_name = form.get("location_name", "")
    location_type = form.get("location_type", "")
    value_class = form.get("value_class", "")
    unit = form.get("unit", "")
    if not site_uuid or not segment_uuid or not location_uuid:
        return RedirectResponse("/discovery/sites", status_code=303)
    if get_selected_segment(
        request,
        expected_site_uuid=site_uuid,
        expected_segment_uuid=segment_uuid,
    ) is None:
        return RedirectResponse("/discovery/sites", status_code=303)
    store_selected_measurement_location(
        request,
        uuid=location_uuid,
        name=location_name,
        location_type=location_type,
        value_class=value_class,
        unit=unit,
    )
    return RedirectResponse(
        f"/discovery/sites/{site_uuid}/segments/{segment_uuid}/measurement-locations/{location_uuid}/measurements",
        status_code=303,
    )


@router.get("/discovery/sites/{site_uuid}/segments", response_class=HTMLResponse)
def discovery_segments(
    request: Request,
    site_uuid: str,
    segment_type_uuid: str | None = None,
    max_items: str | None = None,
    searched: bool = False,
) -> HTMLResponse:
    redirect = require_discovery_session(request)
    if redirect:
        return redirect
    site = get_selected_site(request, site_uuid)
    if site is None:
        return workflow_context_required_response(request)
    segment_service = get_segment_service(request)
    segment_types = get_segment_type_entries(get_database_path(request))
    connector_error: dict[str, object] | None = None
    validation_error: str | None = None
    segments: list[Segment] = []
    parsed_max_items, validation_error = parse_segment_max_items(max_items)
    if searched and not validation_error:
        try:
            log_cli_call(request, "GetSegments")
            segments = segment_service.get_segments(
                site_uuid,
                segment_type_entries=segment_types,
                discovery_session_id=get_discovery_session_id(request),
                segment_type_uuid=segment_type_uuid,
                max_items=parsed_max_items,
            )
            persist_discovered_segments(request, segments)
        except CliDiscoveryError as exc:
            if is_closed_cli_session_error(exc):
                try:
                    refreshed_session_id = reopen_cli_session_for_retry(request)
                    if refreshed_session_id:
                        log_cli_call(request, "GetSegments")
                        segments = segment_service.get_segments(
                            site_uuid,
                            segment_type_entries=segment_types,
                            discovery_session_id=refreshed_session_id,
                            segment_type_uuid=segment_type_uuid,
                            max_items=parsed_max_items,
                        )
                        persist_discovered_segments(request, segments)
                    else:
                        connector_error = exc.to_safe_dict()
                except CliDiscoveryError as retry_exc:
                    if is_closed_cli_session_error(retry_exc):
                        clear_discovery_session(request)
                    connector_error = retry_exc.to_safe_dict()
            else:
                if is_closed_cli_session_error(exc):
                    clear_discovery_session(request)
                connector_error = exc.to_safe_dict()
    return templates.TemplateResponse(
        request,
        "segments.html",
        page_context(
            request,
            site=site,
            segments=segments,
            results_requested=searched,
            segment_types=segment_types,
            connector_error=connector_error,
            validation_error=validation_error,
            filters={
                "segment_type_uuid": segment_type_uuid or "",
                "max_items": str(parsed_max_items),
            },
            max_item_options=SEGMENT_MAX_ITEM_OPTIONS,
        ),
    )


@router.get(
    "/discovery/sites/{site_uuid}/segments/{segment_uuid}/measurement-locations",
    response_class=HTMLResponse,
)
def discovery_measurement_locations(
    request: Request,
    site_uuid: str,
    segment_uuid: str,
    measurement_location_type_uuid: str | None = None,
    max_items: str | None = None,
    searched: bool = False,
) -> HTMLResponse:
    redirect = require_discovery_session(request)
    if redirect:
        return redirect
    site = get_selected_site(request, site_uuid)
    segment = get_selected_segment(
        request,
        expected_site_uuid=site_uuid,
        expected_segment_uuid=segment_uuid,
    )
    if site is None or segment is None:
        return workflow_context_required_response(request)
    location_service = get_location_service(request)
    location_types = get_measurement_location_type_entries(get_database_path(request))
    connector_error: dict[str, object] | None = None
    validation_error: str | None = None
    locations: list[MeasurementLocation] = []
    parsed_max_items, validation_error = parse_measurement_location_max_items(max_items)
    if searched and not validation_error:
        try:
            log_cli_call(request, "GetMeasurementLocations")
            locations = location_service.get_measurement_locations(
                segment_uuid,
                location_type_entries=location_types,
                discovery_session_id=get_discovery_session_id(request),
                measurement_location_type_uuid=measurement_location_type_uuid,
                max_items=parsed_max_items,
            )
            persist_discovered_measurement_locations(request, locations, site_uuid)
        except CliDiscoveryError as exc:
            if is_closed_cli_session_error(exc):
                clear_discovery_session(request)
            connector_error = exc.to_safe_dict()
    return templates.TemplateResponse(
        request,
        "measurement_locations.html",
        page_context(
            request,
            site=site,
            segment=segment,
            locations=locations,
            results_requested=searched,
            location_types=location_types,
            connector_error=connector_error,
            validation_error=validation_error,
            filters={
                "measurement_location_type_uuid": measurement_location_type_uuid or "",
                "max_items": str(parsed_max_items),
            },
            max_item_options=MEASUREMENT_LOCATION_MAX_ITEM_OPTIONS,
        ),
    )


@router.get(
    "/discovery/sites/{site_uuid}/segments/{segment_uuid}/measurement-locations/{location_uuid}/measurements",
    response_class=HTMLResponse,
)
def discovery_measurements(
    request: Request,
    site_uuid: str,
    segment_uuid: str,
    location_uuid: str,
    recorded_from: str | None = None,
    recorded_to: str | None = None,
    max_items: str | None = None,
    searched: bool = False,
) -> HTMLResponse:
    redirect = require_discovery_session(request)
    if redirect:
        return redirect
    site = get_selected_site(request, site_uuid)
    segment = get_selected_segment(
        request,
        expected_site_uuid=site_uuid,
        expected_segment_uuid=segment_uuid,
    )
    location = get_selected_measurement_location(
        request,
        expected_site_uuid=site_uuid,
        expected_segment_uuid=segment_uuid,
        expected_location_uuid=location_uuid,
    )
    if site is None or segment is None or location is None:
        return workflow_context_required_response(request)
    default_recorded_from, default_recorded_to = default_measurement_preview_filters()
    display_recorded_from = recorded_from if searched else recorded_from or default_recorded_from
    display_recorded_to = recorded_to if searched else recorded_to or default_recorded_to
    measurement_service = get_measurement_service(request)
    connector_error: dict[str, object] | None = None
    validation_error: str | None = None
    measurements: list[Measurement] = []
    normalized_from, normalized_to, parsed_max_items, validation_error = validate_measurement_filters(
        recorded_from,
        recorded_to,
        max_items,
    )
    if searched and not validation_error:
        try:
            log_cli_call(request, "GetMeasurements")
            measurements = measurement_service.get_measurements(
                location_uuid,
                discovery_session_id=get_discovery_session_id(request),
                segment_uuid=segment_uuid,
                recorded_from=normalized_from,
                recorded_to=normalized_to,
                max_items=parsed_max_items,
                fallback_unit=location.unit,
            )
            persist_discovered_measurements(request, measurements, location)
        except CliDiscoveryError as exc:
            if is_closed_cli_session_error(exc):
                clear_discovery_session(request)
            connector_error = exc.to_safe_dict()
    return templates.TemplateResponse(
        request,
        "measurements.html",
        page_context(
            request,
            site=site,
            segment=segment,
            location=location,
            measurements=measurements,
            results_requested=searched,
            connector_error=connector_error,
            validation_error=validation_error,
            filters={
                "recorded_from": display_recorded_from or "",
                "recorded_to": display_recorded_to or "",
                "max_items": str(parsed_max_items),
            },
            max_item_options=MEASUREMENT_MAX_ITEM_OPTIONS,
        ),
    )


# Old explorer URLs now funnel users into the guided workflow.
@router.get("/sites", include_in_schema=False)
@router.get("/segments", include_in_schema=False)
@router.get("/assets", include_in_schema=False)
@router.get("/measurement-locations", include_in_schema=False)
@router.get("/measurements", include_in_schema=False)
def legacy_explorer_redirect() -> RedirectResponse:
    return RedirectResponse("/discovery/sites", status_code=307)


@router.get("/api/sites")
def api_sites(
    request: Request,
    site_type: str | None = None,
    status: str | None = None,
    search: str | None = None,
):
    session_id = get_discovery_session_id(request)
    try:
        return get_site_service(request).get_sites(
            site_type, status, search, discovery_session_id=session_id
        )
    except CliDiscoveryError as exc:
        return JSONResponse(status_code=502, content={"success": False, "error": exc.to_safe_dict()})


@router.get("/api/sites/{site_uuid}/segments", response_model=list[Segment])
def api_segments(
    request: Request,
    site_uuid: str,
    segment_type_uuid: str | None = None,
    max_items: str | None = None,
    segment_type: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[Segment]:
    require_site(request, site_uuid)
    parsed_max_items, validation_error = parse_segment_max_items(max_items)
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)
    segment_service = get_segment_service(request)
    return segment_service.get_segments(
        site_uuid,
        segment_type,
        status,
        search,
        segment_type_entries=get_segment_type_entries(get_database_path(request)),
        discovery_session_id=get_discovery_session_id(request),
        segment_type_uuid=segment_type_uuid,
        max_items=parsed_max_items,
    )


@router.get(
    "/api/sites/{site_uuid}/segments/{segment_uuid}/measurement-locations",
    response_model=list[MeasurementLocation],
)
def api_measurement_locations(
    request: Request,
    site_uuid: str,
    segment_uuid: str,
    measurement_location_type_uuid: str | None = None,
    max_items: str | None = None,
) -> list[MeasurementLocation]:
    require_segment(request, site_uuid, segment_uuid)
    parsed_max_items, validation_error = parse_measurement_location_max_items(max_items)
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)
    location_service = get_location_service(request)
    return location_service.get_measurement_locations(
        segment_uuid,
        location_type_entries=get_measurement_location_type_entries(get_database_path(request)),
        discovery_session_id=get_discovery_session_id(request),
        measurement_location_type_uuid=measurement_location_type_uuid,
        max_items=parsed_max_items,
    )


@router.get(
    "/api/sites/{site_uuid}/segments/{segment_uuid}/measurement-locations/{location_uuid}/measurements",
    response_model=list[Measurement],
)
def api_measurements(
    request: Request,
    site_uuid: str,
    segment_uuid: str,
    location_uuid: str,
    recorded_from: str | None = None,
    recorded_to: str | None = None,
    max_items: str | None = None,
) -> list[Measurement]:
    location = require_location(request, site_uuid, segment_uuid, location_uuid)
    normalized_from, normalized_to, parsed_max_items, validation_error = validate_measurement_filters(
        recorded_from,
        recorded_to,
        max_items,
    )
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)
    measurement_service = get_measurement_service(request)
    return measurement_service.get_measurements(
        location_uuid,
        discovery_session_id=get_discovery_session_id(request),
        segment_uuid=segment_uuid,
        recorded_from=normalized_from,
        recorded_to=normalized_to,
        max_items=parsed_max_items,
        fallback_unit=location.unit,
    )


@router.get("/api/reference-data/status")
def api_reference_data_status(request: Request) -> dict[str, object]:
    return get_reference_data_status(get_database_path(request))


@router.get("/api/reference-data/segment-types")
def api_reference_data_segment_types(request: Request) -> list[dict[str, str | None]]:
    return [reference_entry_json(entry) for entry in get_segment_type_entries(get_database_path(request))]


@router.get("/api/reference-data/measurement-location-types")
def api_reference_data_measurement_location_types(request: Request) -> list[dict[str, str | None]]:
    return [
        reference_entry_json(entry)
        for entry in get_measurement_location_type_entries(get_database_path(request))
    ]


@router.get("/api/reference-data/measurement-types")
def api_reference_data_measurement_types(request: Request) -> list[dict[str, str | None]]:
    return []


@router.get("/api/reference-data/units-of-measure")
def api_reference_data_units_of_measure(request: Request) -> list[dict[str, str | None]]:
    return [reference_entry_json(entry) for entry in get_unit_of_measure_entries(get_database_path(request))]
