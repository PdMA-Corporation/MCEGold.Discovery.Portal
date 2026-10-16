from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import UUID


SUPPORTED_VALUE_TYPES = {"Boolean", "Integer", "Decimal", "String", "Uuid"}
REQUEST_SESSION_ID = "Discovery.RequestSessionId"
REQUEST_SESSION_STARTED_UTC = "Discovery.RequestSessionStartedUtc"
ENERGY_COST_RATE_SCALE = 6
ENERGY_COST_RATE_VALIDATION_MESSAGE = (
    "EnergyCost.RatePerKwh must be a non-negative decimal with no more than 6 decimal places."
)
DATA_RETENTION_MIN_DAYS = 30
DATA_RETENTION_MAX_DAYS = 730
DATA_RETENTION_DAYS_VALIDATION_MESSAGE = (
    f"DataRetention.Days must be an integer from {DATA_RETENTION_MIN_DAYS} to {DATA_RETENTION_MAX_DAYS}."
)


@dataclass(frozen=True)
class ApplicationSettingDefinition:
    setting_key: str
    value_type: str
    default_value: str | None


@dataclass(frozen=True)
class ApplicationSetting:
    setting_key: str
    setting_value: str | None
    value_type: str
    updated_utc: str


APPLICATION_SETTING_DEFAULTS: tuple[ApplicationSettingDefinition, ...] = (
    ApplicationSettingDefinition(REQUEST_SESSION_ID, "String", None),
    ApplicationSettingDefinition(REQUEST_SESSION_STARTED_UTC, "String", None),
    ApplicationSettingDefinition("EnergyCost.CurrencyUomUuid", "Uuid", None),
    ApplicationSettingDefinition("EnergyCost.RatePerKwh", "Decimal", None),
    ApplicationSettingDefinition("Collector.Enabled", "Boolean", "true"),
    ApplicationSettingDefinition("Collector.PollingIntervalSeconds", "Integer", "15"),
    ApplicationSettingDefinition("DataRetention.Enabled", "Boolean", "false"),
    ApplicationSettingDefinition("DataRetention.Days", "Integer", "90"),
)

APPLICATION_SETTING_DEFINITIONS = {
    definition.setting_key: definition for definition in APPLICATION_SETTING_DEFAULTS
}


class ApplicationSettingError(ValueError):
    pass


def create_application_setting_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ApplicationSetting (
            SettingKey TEXT PRIMARY KEY,
            SettingValue TEXT NULL,
            ValueType TEXT NOT NULL,
            UpdatedUtc TEXT NOT NULL
        )
        """
    )


def seed_default_application_settings(connection: sqlite3.Connection) -> None:
    create_application_setting_table(connection)
    connection.executemany(
        """
        INSERT OR IGNORE INTO ApplicationSetting (
            SettingKey,
            SettingValue,
            ValueType,
            UpdatedUtc
        )
        VALUES (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        """,
        [
            (definition.setting_key, definition.default_value, definition.value_type)
            for definition in APPLICATION_SETTING_DEFAULTS
        ],
    )


class ApplicationSettingsRepository:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def get_setting(self, setting_key: str) -> ApplicationSetting | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT SettingKey, SettingValue, ValueType, UpdatedUtc
                FROM ApplicationSetting
                WHERE SettingKey = ?
                """,
                (setting_key,),
            ).fetchone()
        return _setting_from_row(row) if row else None

    def get_request_session(self) -> tuple[str | None, str | None]:
        with self._connect() as connection:
            values = dict(connection.execute(
                "SELECT SettingKey, SettingValue FROM ApplicationSetting WHERE SettingKey IN (?, ?)",
                (REQUEST_SESSION_ID, REQUEST_SESSION_STARTED_UTC),
            ).fetchall())
        session_id = values.get(REQUEST_SESSION_ID)
        if not session_id or not session_id.strip():
            return None, None
        return session_id, values.get(REQUEST_SESSION_STARTED_UTC)

    def set_request_session(self, session_id: str | None, started_utc: str | None) -> None:
        """Publish or clear the Collector's session record as one atomic update."""
        if not session_id or not session_id.strip():
            session_id, started_utc = None, None
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO ApplicationSetting (SettingKey, SettingValue, ValueType, UpdatedUtc)
                VALUES (?, ?, 'String', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                ON CONFLICT(SettingKey) DO UPDATE SET
                    SettingValue = excluded.SettingValue,
                    ValueType = excluded.ValueType,
                    UpdatedUtc = excluded.UpdatedUtc
                """,
                ((REQUEST_SESSION_ID, session_id), (REQUEST_SESSION_STARTED_UTC, started_utc)),
            )
            connection.commit()

    def get_all_settings(self) -> dict[str, ApplicationSetting]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT SettingKey, SettingValue, ValueType, UpdatedUtc
                FROM ApplicationSetting
                ORDER BY SettingKey
                """
            ).fetchall()
        return {row["SettingKey"]: _setting_from_row(row) for row in rows}

    def set_setting(self, setting_key: str, value: Any) -> ApplicationSetting:
        definition = _definition(setting_key)
        serialized_value = _serialize_known_value(definition, value)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ApplicationSetting (
                    SettingKey,
                    SettingValue,
                    ValueType,
                    UpdatedUtc
                )
                VALUES (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                ON CONFLICT(SettingKey) DO UPDATE SET
                    SettingValue = excluded.SettingValue,
                    ValueType = excluded.ValueType,
                    UpdatedUtc = excluded.UpdatedUtc
                """,
                (definition.setting_key, serialized_value, definition.value_type),
            )
            connection.commit()
        setting = self.get_setting(setting_key)
        if setting is None:
            raise ApplicationSettingError(f"Application setting was not saved: {setting_key}")
        return setting

    def get_boolean(self, setting_key: str) -> bool | None:
        setting = self._known_setting(setting_key, "Boolean")
        if setting.setting_value is None:
            return None
        value = setting.setting_value.strip().casefold()
        if value == "true":
            return True
        if value == "false":
            return False
        raise ApplicationSettingError(f"{setting_key} must be Boolean.")

    def get_integer(self, setting_key: str) -> int | None:
        setting = self._known_setting(setting_key, "Integer")
        if setting.setting_value is None:
            return None
        try:
            return int(setting.setting_value)
        except ValueError as exc:
            raise ApplicationSettingError(f"{setting_key} must be Integer.") from exc

    def get_decimal(self, setting_key: str) -> Decimal | None:
        setting = self._known_setting(setting_key, "Decimal")
        if setting.setting_value is None:
            return None
        try:
            return Decimal(setting.setting_value)
        except InvalidOperation as exc:
            raise ApplicationSettingError(f"{setting_key} must be Decimal.") from exc

    def get_uuid(self, setting_key: str) -> str | None:
        setting = self._known_setting(setting_key, "Uuid")
        if setting.setting_value is None:
            return None
        try:
            UUID(setting.setting_value)
        except ValueError as exc:
            raise ApplicationSettingError(f"{setting_key} must be Uuid.") from exc
        return setting.setting_value

    def _known_setting(self, setting_key: str, value_type: str) -> ApplicationSetting:
        definition = _definition(setting_key)
        if definition.value_type != value_type:
            raise ApplicationSettingError(f"{setting_key} is not a {value_type} setting.")
        setting = self.get_setting(setting_key)
        if setting is None:
            raise ApplicationSettingError(f"Application setting is missing: {setting_key}")
        if setting.value_type != definition.value_type:
            raise ApplicationSettingError(f"{setting_key} must have ValueType {definition.value_type}.")
        return setting

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection


def _definition(setting_key: str) -> ApplicationSettingDefinition:
    definition = APPLICATION_SETTING_DEFINITIONS.get(setting_key)
    if definition is None:
        raise ApplicationSettingError(f"Unknown application setting: {setting_key}")
    if definition.value_type not in SUPPORTED_VALUE_TYPES:
        raise ApplicationSettingError(f"Unsupported application setting type: {definition.value_type}")
    return definition


def _serialize_known_value(definition: ApplicationSettingDefinition, value: Any) -> str | None:
    if value is None:
        if definition.setting_key in {"EnergyCost.CurrencyUomUuid", "EnergyCost.RatePerKwh"}:
            return None
        raise ApplicationSettingError(f"{definition.setting_key} cannot be null.")
    if definition.value_type == "Boolean":
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str) and value.strip().casefold() in {"true", "false"}:
            return value.strip().casefold()
        raise ApplicationSettingError(f"{definition.setting_key} must be Boolean.")
    if definition.value_type == "Integer":
        try:
            integer_value = int(value)
        except (TypeError, ValueError) as exc:
            raise ApplicationSettingError(f"{definition.setting_key} must be Integer.") from exc
        if definition.setting_key == "Collector.PollingIntervalSeconds" and integer_value <= 0:
            raise ApplicationSettingError("Collector.PollingIntervalSeconds must be greater than zero.")
        if (
            definition.setting_key == "DataRetention.Days"
            and not DATA_RETENTION_MIN_DAYS <= integer_value <= DATA_RETENTION_MAX_DAYS
        ):
            raise ApplicationSettingError(DATA_RETENTION_DAYS_VALIDATION_MESSAGE)
        return str(integer_value)
    if definition.value_type == "Decimal":
        try:
            decimal_value = Decimal(str(value))
        except InvalidOperation as exc:
            raise ApplicationSettingError(f"{definition.setting_key} must be Decimal.") from exc
        if definition.setting_key == "EnergyCost.RatePerKwh":
            validate_energy_cost_rate(decimal_value)
        return format(decimal_value, "f")
    if definition.value_type == "Uuid":
        text = str(value).strip()
        try:
            UUID(text)
        except ValueError as exc:
            raise ApplicationSettingError(f"{definition.setting_key} must be Uuid.") from exc
        return text
    if definition.value_type == "String":
        return str(value)
    raise ApplicationSettingError(f"Unsupported application setting type: {definition.value_type}")


def _setting_from_row(row: sqlite3.Row) -> ApplicationSetting:
    return ApplicationSetting(
        setting_key=row["SettingKey"],
        setting_value=row["SettingValue"],
        value_type=row["ValueType"],
        updated_utc=row["UpdatedUtc"],
    )


def validate_energy_cost_rate(value: Decimal) -> None:
    if value < 0 or _decimal_scale(value) > ENERGY_COST_RATE_SCALE:
        raise ApplicationSettingError(ENERGY_COST_RATE_VALIDATION_MESSAGE)


def _decimal_scale(value: Decimal) -> int:
    exponent = value.as_tuple().exponent
    return abs(exponent) if exponent < 0 else 0
