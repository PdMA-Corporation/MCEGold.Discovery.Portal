from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.models import Asset, Measurement, MeasurementLocation, Segment, Site
from app.services.discovery_client import DiscoveryClient


SENSITIVE_PATTERNS = [
    re.compile(r"(password\s*[=:]\s*)[^\s,;]+", re.IGNORECASE),
    re.compile(r"(apiKey\s*[=:]\s*)[^\s,;]+", re.IGNORECASE),
    re.compile(r"(userName\s*[=:]\s*)[^\s,;]+", re.IGNORECASE),
    re.compile(r"(Authorization\s*:\s*)[^\r\n]+", re.IGNORECASE),
    re.compile(r"(Basic\s+)[A-Za-z0-9+/=._:-]+", re.IGNORECASE),
    re.compile(r"(Bearer\s+)[A-Za-z0-9+/=._:-]+", re.IGNORECASE),
]
FULL_PAYLOAD_PROFILE = "Full"


def redact_sensitive(value: Any) -> str:
    text = "" if value is None else str(value)
    for pattern in SENSITIVE_PATTERNS:
        text = pattern.sub(r"\1***REDACTED***", text)
    return text


@dataclass
class CliDiscoveryError(Exception):
    friendly_message: str
    command: list[str]
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    timeout_seconds: int | None = None
    fault: dict[str, Any] | None = None
    diagnostics: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.friendly_message

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "message": self.friendly_message,
            "command": redact_command(self.command),
            "exitCode": self.exit_code,
            "timeoutSeconds": self.timeout_seconds,
            "stdout": redact_sensitive((self.stdout or "")[:4000]) or None,
            "stderr": redact_sensitive((self.stderr or "")[:1000]) or None,
            "fault": redact_fault(self.fault),
            "diagnostics": redact_diagnostics(self.diagnostics),
        }


def redact_command(command: list[str]) -> list[str]:
    redacted: list[str] = []
    redact_next = False
    for token in command:
        if redact_next:
            redacted.append("***REDACTED***")
            redact_next = False
            continue
        redacted.append(redact_sensitive(token))
        if token in {"--api-key-file", "--password-file"}:
            redact_next = True
    return redacted


def redact_fault(fault: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(fault, dict):
        return None
    safe = json.loads(json.dumps(fault, default=str))
    for key, value in list(safe.items()):
        if isinstance(value, str):
            safe[key] = redact_sensitive(value)
    return safe


def redact_diagnostics(diagnostics: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(diagnostics, dict):
        return None
    safe = json.loads(json.dumps(diagnostics, default=str))
    if isinstance(safe.get("argumentList"), list):
        safe["argumentList"] = redact_command([str(item) for item in safe["argumentList"]])
    for key in ("resolvedCliPath", "workingDirectory", "inputPayloadPath", "stdout", "stderr"):
        if isinstance(safe.get(key), str):
            safe[key] = redact_sensitive(safe[key])
    return safe


class MceGoldCliDiscoveryClient(DiscoveryClient):
    def __init__(
        self,
        cli_path: str,
        connector_config_path: str,
        timeout_seconds: int = 60,
        max_items: int = 100,
        segment_max_items: int = 100,
        measurement_location_max_items: int = 100,
        measurement_max_items: int = 100,
        include_raw: bool = False,
        environment_overrides: dict[str, str] | None = None,
        sleep_func: Callable[[float], None] = time.sleep,
    ) -> None:
        self.cli_path = cli_path
        self.connector_config_path = connector_config_path
        self.timeout_seconds = timeout_seconds
        self.max_items = max_items
        self.segment_max_items = segment_max_items
        self.measurement_location_max_items = measurement_location_max_items
        self.measurement_max_items = measurement_max_items
        self.include_raw = include_raw
        self.environment_overrides = environment_overrides or {}
        self.sleep_func = sleep_func
        self.last_error: CliDiscoveryError | None = None
        self.last_command: list[str] | None = None
        self.last_command_diagnostics: dict[str, Any] | None = None
        self.last_get_sites_diagnostics: dict[str, Any] = self._empty_get_sites_diagnostics()
        self.last_response_polling_diagnostics: dict[str, Any] | None = None

    def open_request_session(self) -> str:
        self.last_error = None
        command = self.build_open_request_session_command()
        envelope = self._run_json_command(command, "The MCEGold CLI could not open a request session.")
        session_id = self._extract_session_id(envelope)
        if not session_id:
            raise self._record_error(
                CliDiscoveryError(
                    "The MCEGold CLI opened a request session but did not return a session ID.",
                    command=command,
                )
            )
        return session_id

    def close_request_session(self, session_id: str) -> None:
        self.last_error = None
        command = self.build_close_request_session_command(session_id)
        self._run_json_command(command, "The MCEGold CLI could not close the request session.")

    def get_sites(self, session_id: str | None = None) -> list[Site]:
        self.last_error = None
        self.last_get_sites_diagnostics = self._empty_get_sites_diagnostics()
        if not self.cli_path:
            raise self._record_error(
                CliDiscoveryError(
                    "MCEGOLD_CLI_PATH is not configured.",
                    command=[],
                )
            )
        if not session_id:
            raise self._record_error(
                CliDiscoveryError(
                    "An active request session is required before calling GetSites.",
                    command=[],
                )
            )

        payload = {
            "requestType": "GetSites",
            "payloadProfile": FULL_PAYLOAD_PROFILE,
            "maxItems": self.max_items,
            "filters": {},
        }
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".get-sites.json",
            encoding="utf-8",
            delete=False,
        ) as file:
            json.dump(payload, file)
            payload_path = file.name

        try:
            completed_get_sites = False
            read_envelope, _request_id, post_diagnostics, read_diagnostics = (
                self._post_request_and_wait_for_response(
                    session_id=session_id,
                    payload_path=payload_path,
                    request_type="GetSites",
                    post_failure_message="The MCEGold CLI could not post the GetSites request.",
                    read_failure_message="The MCEGold CLI could not read the GetSites response.",
                    missing_request_id_message=(
                        "The MCEGold CLI posted GetSites but did not return a request message ID."
                    ),
                )
            )
            completed_get_sites = True
        finally:
            if completed_get_sites:
                Path(payload_path).unlink(missing_ok=True)

        sites = self._parse_sites(read_envelope)
        if not sites and isinstance(read_envelope, dict) and "success" not in read_envelope:
            sites = self._parse_sites({"data": read_envelope})
        self.last_get_sites_diagnostics = {
            "called": True,
            "envelopeSuccess": read_envelope.get("success") if isinstance(read_envelope, dict) else None,
            "rawReceived": bool(isinstance(read_envelope, dict) and read_envelope.get("raw")),
            "parsedSiteCount": len(sites),
            "postCommand": post_diagnostics,
            "readCommand": read_diagnostics,
        }
        return sites

    def build_open_request_session_command(self) -> list[str]:
        command = self._base_command()
        command.extend(
            [
                "request",
                "open-session",
                "--config",
                self.connector_config_path,
                "--output",
                "json",
            ]
        )
        if self.include_raw:
            command.append("--include-raw")
        return command

    def build_close_request_session_command(self, session_id: str) -> list[str]:
        command = self._base_command()
        command.extend(
            [
                "request",
                "close-session",
                "--config",
                self.connector_config_path,
                "--session-id",
                session_id,
                "--output",
                "json",
            ]
        )
        if self.include_raw:
            command.append("--include-raw")
        return command

    def build_post_get_sites_command(self, session_id: str, payload_path: str) -> list[str]:
        return self.build_post_request_command(session_id, payload_path)

    def build_post_request_command(
        self, session_id: str, payload_path: str
    ) -> list[str]:
        command = self._base_command()
        command.extend(
            [
                "request",
                "post",
                "--config",
                self.connector_config_path,
                "--session-id",
                session_id,
                "--input",
                payload_path,
                "--output",
                "json",
            ]
        )
        if self.include_raw:
            command.append("--include-raw")
        return command

    def build_read_response_command(
        self,
        session_id: str,
        request_id: str,
        force_include_raw: bool = False,
    ) -> list[str]:
        command = self._base_command()
        command.extend(
            [
                "request",
                "read-response",
                "--config",
                self.connector_config_path,
                "--session-id",
                session_id,
                "--request-id",
                request_id,
                "--output",
                "json",
            ]
        )
        if self.include_raw or force_include_raw:
            command.append("--include-raw")
        return command

    def build_get_sites_command(self, payload_path: str) -> list[str]:
        """Backward-compatible alias for tests/docs from the earlier atomic phase."""
        return self.build_post_get_sites_command("<session-id>", payload_path)

    def _base_command(self) -> list[str]:
        cli_path = self.cli_path
        return ["dotnet", cli_path] if cli_path.lower().endswith(".dll") else [cli_path]

    def get_assets(self) -> list[Asset]:
        return []

    def get_segments(
        self,
        site_uuid: str | None = None,
        session_id: str | None = None,
        segment_type_uuid: str | None = None,
        max_items: int | None = None,
    ) -> list[Segment]:
        self.last_error = None
        if not session_id:
            raise self._record_error(
                CliDiscoveryError(
                    "An active request session is required before calling GetSegments.",
                    command=[],
                )
            )
        if not site_uuid:
            raise self._record_error(
                CliDiscoveryError("A selected site UUID is required for GetSegments.", command=[])
            )

        filters = {"siteUuid": site_uuid}
        if segment_type_uuid:
            filters["typeUuid"] = segment_type_uuid
        payload = {
            "requestType": "GetSegments",
            "payloadProfile": FULL_PAYLOAD_PROFILE,
            "maxItems": max_items if max_items is not None else self.segment_max_items,
            "filters": filters,
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".get-segments.json",
            encoding="utf-8",
            delete=False,
        ) as file:
            json.dump(payload, file)
            payload_path = file.name

        try:
            read_envelope, _, _, _ = self._post_request_and_wait_for_response(
                session_id=session_id,
                payload_path=payload_path,
                request_type="GetSegments",
                post_failure_message="The MCEGold CLI could not post the GetSegments request.",
                read_failure_message="The MCEGold CLI could not read the GetSegments response.",
                missing_request_id_message=(
                    "The MCEGold CLI posted GetSegments but did not return a request message ID."
                ),
            )
        finally:
            Path(payload_path).unlink(missing_ok=True)

        return self._parse_segments(read_envelope, fallback_site_uuid=site_uuid)

    def get_measurement_locations(
        self,
        segment_uuid: str | None = None,
        session_id: str | None = None,
        measurement_location_type_uuid: str | None = None,
        max_items: int | None = None,
    ) -> list[MeasurementLocation]:
        self.last_error = None
        if not session_id:
            raise self._record_error(
                CliDiscoveryError(
                    "An active request session is required before calling GetMeasurementLocations.",
                    command=[],
                )
            )
        if not segment_uuid:
            raise self._record_error(
                CliDiscoveryError(
                    "A selected segment UUID is required for GetMeasurementLocations.",
                    command=[],
                )
            )

        filters = {"segmentUuid": segment_uuid}
        if measurement_location_type_uuid:
            filters["typeUuid"] = measurement_location_type_uuid
        payload = {
            "requestType": "GetMeasurementLocations",
            "payloadProfile": FULL_PAYLOAD_PROFILE,
            "maxItems": max_items if max_items is not None else self.measurement_location_max_items,
            "filters": filters,
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".get-measurement-locations.json",
            encoding="utf-8",
            delete=False,
        ) as file:
            json.dump(payload, file)
            payload_path = file.name

        try:
            read_envelope, _, _, _ = self._post_request_and_wait_for_response(
                session_id=session_id,
                payload_path=payload_path,
                request_type="GetMeasurementLocations",
                post_failure_message=(
                    "The MCEGold CLI could not post the GetMeasurementLocations request."
                ),
                read_failure_message=(
                    "The MCEGold CLI could not read the GetMeasurementLocations response."
                ),
                missing_request_id_message=(
                    "The MCEGold CLI posted GetMeasurementLocations but did not return a request message ID."
                ),
            )
        finally:
            Path(payload_path).unlink(missing_ok=True)

        return self._parse_measurement_locations(
            read_envelope,
            fallback_segment_uuid=segment_uuid,
        )

    def get_measurements(
        self,
        location_uuid: str | None = None,
        session_id: str | None = None,
        segment_uuid: str | None = None,
        recorded_from: str | None = None,
        recorded_to: str | None = None,
        max_items: int | None = None,
        fallback_unit: str | None = None,
    ) -> list[Measurement]:
        self.last_error = None
        if not session_id:
            raise self._record_error(
                CliDiscoveryError(
                    "An active request session is required before calling GetMeasurements.",
                    command=[],
                )
            )
        if not location_uuid:
            raise self._record_error(
                CliDiscoveryError(
                    "A selected measurement location UUID is required for GetMeasurements.",
                    command=[],
                )
            )
        if not segment_uuid:
            raise self._record_error(
                CliDiscoveryError(
                    "A selected segment UUID is required for GetMeasurements.",
                    command=[],
                )
            )

        filters = {
            "measurementLocationUuid": location_uuid,
            "segmentUuid": segment_uuid,
        }
        if recorded_from:
            filters["recordedFrom"] = recorded_from
        if recorded_to:
            filters["recordedTo"] = recorded_to
        effective_max_items = max_items if max_items is not None else self.measurement_max_items
        payload: dict[str, Any] = {
            "requestType": "GetMeasurements",
            "payloadProfile": FULL_PAYLOAD_PROFILE,
            "maxItems": effective_max_items,
            "lastNData": effective_max_items,
            "filters": filters,
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".get-measurements.json",
            encoding="utf-8",
            delete=False,
        ) as file:
            json.dump(payload, file)
            payload_path = file.name

        try:
            read_envelope, _, _, _ = self._post_request_and_wait_for_response(
                session_id=session_id,
                payload_path=payload_path,
                request_type="GetMeasurements",
                post_failure_message="The MCEGold CLI could not post the GetMeasurements request.",
                read_failure_message="The MCEGold CLI could not read the GetMeasurements response.",
                missing_request_id_message=(
                    "The MCEGold CLI posted GetMeasurements but did not return a request message ID."
                ),
            )
        finally:
            Path(payload_path).unlink(missing_ok=True)

        return self._parse_measurements(
            read_envelope,
            fallback_location_uuid=location_uuid,
            fallback_unit=fallback_unit or "",
        )

    def get_status(self) -> dict[str, Any]:
        return {
            "mode": "cli",
            "configured": bool(self.cli_path),
            "status": "error" if self.last_error else "ok",
            "error": self.last_error.to_safe_dict() if self.last_error else None,
        }

    def _empty_get_sites_diagnostics(self) -> dict[str, Any]:
        return {
            "called": False,
            "envelopeSuccess": None,
            "rawReceived": False,
            "parsedSiteCount": 0,
            "postCommand": None,
            "readCommand": None,
        }

    def _record_error(self, error: CliDiscoveryError) -> CliDiscoveryError:
        self.last_error = error
        return error

    def _run_json_command(self, command: list[str], failure_message: str) -> dict[str, Any]:
        if not self.cli_path:
            raise self._record_error(
                CliDiscoveryError("MCEGOLD_CLI_PATH is not configured.", command=command)
            )

        self.last_command = command
        self.last_command_diagnostics = self._command_diagnostics(command)
        try:
            completed = subprocess.run(
                command,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self.timeout_seconds,
                check=False,
                env=self._command_environment(),
            )
        except subprocess.TimeoutExpired as exc:
            diagnostics = self._command_diagnostics(command, stderr=exc.stderr)
            self.last_command_diagnostics = diagnostics
            raise self._record_error(
                CliDiscoveryError(
                    f"{failure_message} The command timed out.",
                    command=command,
                    timeout_seconds=self.timeout_seconds,
                    stderr=exc.stderr,
                    diagnostics=diagnostics,
                )
            )
        except OSError as exc:
            diagnostics = self._command_diagnostics(command, stderr=str(exc))
            self.last_command_diagnostics = diagnostics
            raise self._record_error(
                CliDiscoveryError(
                    f"{failure_message} The CLI process could not be started: {exc}.",
                    command=command,
                    stderr=str(exc),
                    diagnostics=diagnostics,
                )
            )

        diagnostics = self._command_diagnostics(
            command,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        self.last_command_diagnostics = diagnostics
        if completed.returncode != 0:
            fault = self._try_parse_fault(completed.stdout)
            raise self._record_error(
                CliDiscoveryError(
                    failure_message,
                    command=command,
                    exit_code=completed.returncode,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                    fault=fault,
                    diagnostics=diagnostics,
                )
            )

        if not completed.stdout.strip():
            raise self._record_error(
                CliDiscoveryError(
                    f"{failure_message} The CLI returned no JSON output.",
                    command=command,
                    exit_code=completed.returncode,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                    diagnostics=diagnostics,
                )
            )

        try:
            envelope = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise self._record_error(
                CliDiscoveryError(
                    f"{failure_message} The CLI returned invalid JSON: {exc.msg}.",
                    command=command,
                    exit_code=completed.returncode,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                    diagnostics=diagnostics,
                )
            )

        fault = envelope.get("fault") if isinstance(envelope, dict) else None
        if isinstance(envelope, dict) and envelope.get("success") is False:
            raise self._record_error(
                CliDiscoveryError(
                    failure_message,
                    command=command,
                    exit_code=completed.returncode,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                    fault=fault if isinstance(fault, dict) else None,
                    diagnostics=diagnostics,
                )
            )
        return envelope if isinstance(envelope, dict) else {"data": envelope}

    def _command_diagnostics(
        self,
        command: list[str],
        stdout: str | None = None,
        stderr: str | None = None,
    ) -> dict[str, Any]:
        input_payload_path = None
        if "--input" in command:
            index = command.index("--input") + 1
            if index < len(command):
                input_payload_path = command[index]
        return {
            "resolvedCliPath": str(Path(self.cli_path).expanduser().resolve(strict=False))
            if self.cli_path
            else "",
            "workingDirectory": str(Path.cwd()),
            "argumentList": command,
            "inputPayloadPath": input_payload_path,
            "stdout": (stdout or "")[:4000],
            "stderr": (stderr or "")[:4000],
        }

    def _post_request_and_wait_for_response(
        self,
        session_id: str,
        payload_path: str,
        request_type: str,
        post_failure_message: str,
        read_failure_message: str,
        missing_request_id_message: str,
    ) -> tuple[dict[str, Any], str, dict[str, Any] | None, dict[str, Any] | None]:
        post_command = self.build_post_request_command(session_id, payload_path)
        post_envelope = self._run_json_command(post_command, post_failure_message)
        post_diagnostics = self.last_command_diagnostics
        request_id = self._extract_request_message_id(post_envelope)
        if not request_id:
            raise self._record_error(
                CliDiscoveryError(
                    missing_request_id_message,
                    command=post_command,
                )
            )

        read_envelope = self._read_response_with_polling(
            session_id=session_id,
            request_message_id=request_id,
            request_type=request_type,
            failure_message=read_failure_message,
        )
        return read_envelope, request_id, post_diagnostics, self.last_command_diagnostics

    def _read_response_with_polling(
        self,
        session_id: str,
        request_message_id: str,
        request_type: str,
        failure_message: str,
    ) -> dict[str, Any]:
        delays = [0.5, 2.0, 2.0, 2.0, 2.0, 2.0]
        attempts: list[dict[str, Any]] = []
        elapsed_wait = 0.0
        self.last_response_polling_diagnostics = {
            "requestType": request_type,
            "sessionId": session_id,
            "requestMessageId": request_message_id,
            "attemptCount": 0,
            "elapsedWaitSeconds": 0.0,
            "result": None,
            "attempts": attempts,
        }
        last_pending_error: CliDiscoveryError | None = None

        for index, delay in enumerate(delays, start=1):
            self.sleep_func(delay)
            elapsed_wait += delay
            command = self.build_read_response_command(
                session_id,
                request_message_id,
                force_include_raw=True,
            )
            try:
                envelope = self._run_json_command(command, failure_message)
            except CliDiscoveryError as exc:
                if not self._is_pending_response_error(exc):
                    raise self._record_error(self._without_raw_stdout(exc))
                last_pending_error = exc
                attempts.append({"attempt": index, "result": "pending"})
                self.last_response_polling_diagnostics.update(
                    {
                        "attemptCount": index,
                        "elapsedWaitSeconds": elapsed_wait,
                        "result": "pending",
                        "lastFault": redact_fault(exc.fault),
                    }
                )
                continue

            attempts.append({"attempt": index, "result": "success"})
            self.last_response_polling_diagnostics.update(
                {
                    "attemptCount": index,
                    "elapsedWaitSeconds": elapsed_wait,
                    "result": "success",
                }
            )
            self.last_error = None
            self.last_command_diagnostics = self._without_raw_diagnostics(
                self.last_command_diagnostics
            )
            return envelope

        timeout_command = self.build_read_response_command(
            session_id,
            request_message_id,
            force_include_raw=True,
        )
        diagnostics = {
            "requestType": request_type,
            "sessionId": session_id,
            "requestMessageId": request_message_id,
            "attemptCount": len(delays),
            "elapsedWaitSeconds": elapsed_wait,
            "lastFault": redact_fault(last_pending_error.fault if last_pending_error else None),
            "polling": self.last_response_polling_diagnostics,
        }
        self.last_response_polling_diagnostics.update(
            {
                "attemptCount": len(delays),
                "elapsedWaitSeconds": elapsed_wait,
                "result": "timeout",
                "lastFault": diagnostics["lastFault"],
            }
        )
        raise self._record_error(
            CliDiscoveryError(
                "Timed out waiting for the MCEGold Data Services response. "
                "The Portal stopped waiting for the asynchronous response; "
                "the underlying request may still complete later.",
                command=timeout_command,
                fault=last_pending_error.fault if last_pending_error else None,
                diagnostics=diagnostics,
            )
        )

    def _is_pending_response_error(self, error: CliDiscoveryError) -> bool:
        fault = error.fault if isinstance(error.fault, dict) else {}
        if fault.get("category") != "remote":
            return False
        if fault.get("statusCode") != 404:
            return False
        if fault.get("code") not in {"CommandFailed", "ResponseNotAvailable"}:
            return False

        envelope = self._try_parse_envelope(error.stdout)
        raw = envelope.get("raw") if isinstance(envelope, dict) else None
        if isinstance(raw, dict):
            return str(raw.get("fault") or "").casefold() == "there are no messages in the queue"
        return fault.get("code") == "ResponseNotAvailable"

    def _without_raw_stdout(self, error: CliDiscoveryError) -> CliDiscoveryError:
        return CliDiscoveryError(
            friendly_message=error.friendly_message,
            command=error.command,
            exit_code=error.exit_code,
            stdout=self._stdout_without_raw(error.stdout),
            stderr=error.stderr,
            timeout_seconds=error.timeout_seconds,
            fault=error.fault,
            diagnostics=self._without_raw_diagnostics(error.diagnostics),
        )

    def _without_raw_diagnostics(
        self,
        diagnostics: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(diagnostics, dict):
            return diagnostics
        safe = dict(diagnostics)
        safe["stdout"] = self._stdout_without_raw(
            safe.get("stdout") if isinstance(safe.get("stdout"), str) else None
        )
        return safe

    def _stdout_without_raw(self, stdout: str | None) -> str | None:
        envelope = self._try_parse_envelope(stdout)
        if not envelope:
            return stdout
        if "raw" in envelope:
            envelope["raw"] = None
        return json.dumps(envelope)

    def _command_environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(self.environment_overrides)
        return environment

    def _try_parse_fault(self, stdout: str | None) -> dict[str, Any] | None:
        envelope = self._try_parse_envelope(stdout)
        if isinstance(envelope, dict) and isinstance(envelope.get("fault"), dict):
            return envelope["fault"]
        return None

    def _try_parse_envelope(self, stdout: str | None) -> dict[str, Any]:
        if not stdout:
            return {}
        try:
            envelope = json.loads(stdout)
        except json.JSONDecodeError:
            return {}
        return envelope if isinstance(envelope, dict) else {}

    def _extract_session_id(self, envelope: dict[str, Any]) -> str | None:
        data = envelope.get("data")
        for path in (
            ["sessionId"],
            ["requestSessionId"],
            ["id"],
            ["SessionId"],
            ["RequestSessionId"],
        ):
            value = self._get_path(data, path)
            if value:
                return str(value)
        raw = envelope.get("raw")
        for path in (
            ["sessionId"],
            ["requestSessionId"],
            ["id"],
            ["SessionId"],
            ["RequestSessionId"],
        ):
            value = self._get_path(raw, path)
            if value:
                return str(value)
        return None

    def _extract_request_message_id(self, envelope: dict[str, Any]) -> str | None:
        data = envelope.get("data")
        for path in (
            ["requestMessageId"],
            ["messageId"],
            ["id"],
            ["RequestMessageId"],
            ["MessageId"],
        ):
            value = self._get_path(data, path)
            if value:
                return str(value)
        return None

    def _parse_sites(self, envelope: Any) -> list[Site]:
        candidates = self._candidate_site_records(envelope)
        return [self._map_site(record) for record in candidates if isinstance(record, dict)]

    def _parse_segments(self, envelope: Any, fallback_site_uuid: str = "") -> list[Segment]:
        records = self._candidate_segment_records(envelope)
        return [
            self._map_segment(segment, group_site_uuid or fallback_site_uuid)
            for group_site_uuid, segment in records
            if isinstance(segment, dict)
        ]

    def _parse_measurement_locations(
        self,
        envelope: Any,
        fallback_segment_uuid: str = "",
    ) -> list[MeasurementLocation]:
        records = self._candidate_measurement_location_records(envelope)
        return [
            self._map_measurement_location(location, group_segment_uuid or fallback_segment_uuid)
            for group_segment_uuid, location in records
            if isinstance(location, dict)
        ]

    def _parse_measurements(
        self,
        envelope: Any,
        fallback_location_uuid: str = "",
        fallback_unit: str = "",
    ) -> list[Measurement]:
        records = self._candidate_measurement_records(envelope)
        return [
            self._map_measurement(record, fallback_location_uuid, fallback_unit)
            for record in records
            if isinstance(record, dict)
        ]

    def _candidate_measurement_records(self, envelope: Any) -> list[dict[str, Any]]:
        roots: list[Any] = []
        if isinstance(envelope, dict):
            data = envelope.get("data")
            raw = envelope.get("raw")
            roots.extend(
                [
                    self._get_path(data, ["showMeasurements", "dataArea", "measurements"]),
                    self._get_path(raw, ["showMeasurements", "dataArea", "measurements"]),
                    data,
                    raw,
                ]
            )
        else:
            roots.append(envelope)

        records: list[dict[str, Any]] = []
        for root in roots:
            records.extend(self._measurement_records_from_groups(root))
        return self._dedupe_measurement_records(records)

    def _measurement_records_from_groups(self, value: Any) -> list[dict[str, Any]]:
        if value is None:
            return []
        if isinstance(value, list):
            records: list[dict[str, Any]] = []
            for item in value:
                records.extend(self._measurement_records_from_groups(item))
            return records
        if isinstance(value, dict):
            if "showMeasurements" in value:
                return self._measurement_records_from_groups(
                    self._get_path(value, ["showMeasurements", "dataArea", "measurements"])
                )
            if "dataArea" in value:
                return self._measurement_records_from_groups(
                    self._get_path(value, ["dataArea", "measurements"])
                )
            if "measurement" in value or "measurements" in value:
                measurement_items = value.get("measurement") or value.get("measurements")
                return [
                    measurement
                    for measurement in self._as_list(measurement_items)
                    if isinstance(measurement, dict)
                ]
            if self._looks_like_measurement(value):
                return [value]
            for key in ("measurements", "payload", "data", "response"):
                if key in value:
                    nested = self._measurement_records_from_groups(value[key])
                    if nested:
                        return nested
        return []

    def _looks_like_measurement(self, value: dict[str, Any]) -> bool:
        keys = {key.casefold() for key in value}
        return bool(keys & {"uuid", "recorded", "data"}) and "data" in keys

    def _dedupe_measurement_records(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for record in records:
            key = str(self._first(record, ["UUID", "uuid", "MeasurementUUID", "measurementUuid"]) or id(record))
            if key not in seen:
                seen.add(key)
                deduped.append(record)
        return deduped

    def _candidate_measurement_location_records(
        self,
        envelope: Any,
    ) -> list[tuple[str, dict[str, Any]]]:
        roots: list[Any] = []
        if isinstance(envelope, dict):
            data = envelope.get("data")
            raw = envelope.get("raw")
            roots.extend(
                [
                    self._get_path(
                        data,
                        ["showMeasurementLocations", "dataArea", "measurementLocations"],
                    ),
                    self._get_path(
                        raw,
                        ["showMeasurementLocations", "dataArea", "measurementLocations"],
                    ),
                    data,
                    raw,
                ]
            )
        else:
            roots.append(envelope)

        records: list[tuple[str, dict[str, Any]]] = []
        for root in roots:
            records.extend(self._measurement_location_records_from_groups(root))
        return self._dedupe_measurement_location_records(records)

    def _measurement_location_records_from_groups(
        self,
        value: Any,
    ) -> list[tuple[str, dict[str, Any]]]:
        if value is None:
            return []
        if isinstance(value, list):
            records: list[tuple[str, dict[str, Any]]] = []
            for item in value:
                records.extend(self._measurement_location_records_from_groups(item))
            return records
        if isinstance(value, dict):
            if "showMeasurementLocations" in value:
                return self._measurement_location_records_from_groups(
                    self._get_path(value, ["showMeasurementLocations", "dataArea", "measurementLocations"])
                )
            if "dataArea" in value:
                return self._measurement_location_records_from_groups(
                    self._get_path(value, ["dataArea", "measurementLocations"])
                )
            if "measurementLocation" in value or "measurementLocations" in value:
                segment_uuid = str(self._get_path(value, ["segment", "UUID"]) or "")
                location_items = value.get("measurementLocation") or value.get("measurementLocations")
                return [
                    (segment_uuid, location)
                    for location in self._as_list(location_items)
                    if isinstance(location, dict)
                ]
            if self._looks_like_measurement_location(value):
                return [("", value)]
            for key in ("measurementLocations", "payload", "data", "response"):
                if key in value:
                    nested = self._measurement_location_records_from_groups(value[key])
                    if nested:
                        return nested
        return []

    def _looks_like_measurement_location(self, value: dict[str, Any]) -> bool:
        keys = {key.casefold() for key in value}
        return bool(keys & {"uuid", "shortnames", "valueclass", "defaultunitofmeasure"})

    def _dedupe_measurement_location_records(
        self,
        records: list[tuple[str, dict[str, Any]]],
    ) -> list[tuple[str, dict[str, Any]]]:
        seen: set[str] = set()
        deduped: list[tuple[str, dict[str, Any]]] = []
        for segment_uuid, record in records:
            key = str(
                self._first(
                    record,
                    ["UUID", "uuid", "MeasurementLocationUUID", "measurementLocationUuid"],
                )
                or id(record)
            )
            if key not in seen:
                seen.add(key)
                deduped.append((segment_uuid, record))
        return deduped

    def _candidate_segment_records(self, envelope: Any) -> list[tuple[str, dict[str, Any]]]:
        roots: list[Any] = []
        if isinstance(envelope, dict):
            data = envelope.get("data")
            raw = envelope.get("raw")
            roots.extend(
                [
                    self._get_path(data, ["showSegments", "dataArea", "segments"]),
                    self._get_path(raw, ["showSegments", "dataArea", "segments"]),
                    data,
                    raw,
                ]
            )
        else:
            roots.append(envelope)

        records: list[tuple[str, dict[str, Any]]] = []
        for root in roots:
            records.extend(self._segment_records_from_groups(root))
        return self._dedupe_segment_records(records)

    def _segment_records_from_groups(self, value: Any) -> list[tuple[str, dict[str, Any]]]:
        if value is None:
            return []
        if isinstance(value, list):
            records: list[tuple[str, dict[str, Any]]] = []
            for item in value:
                records.extend(self._segment_records_from_groups(item))
            return records
        if isinstance(value, dict):
            if "showSegments" in value:
                return self._segment_records_from_groups(
                    self._get_path(value, ["showSegments", "dataArea", "segments"])
                )
            if "dataArea" in value:
                return self._segment_records_from_groups(
                    self._get_path(value, ["dataArea", "segments"])
                )
            if ("segment" in value or "segments" in value) and "site" in value:
                site_uuid = str(self._get_path(value, ["site", "UUID"]) or "")
                segment_items = value.get("segment") or value.get("segments")
                return [
                    (site_uuid, segment)
                    for segment in self._as_list(segment_items)
                    if isinstance(segment, dict)
                ]
            if self._looks_like_segment(value):
                return [("", value)]
            for key in ("segments", "payload", "data", "response"):
                if key in value:
                    nested = self._segment_records_from_groups(value[key])
                    if nested:
                        return nested
        return []

    def _looks_like_segment(self, value: dict[str, Any]) -> bool:
        keys = {key.casefold() for key in value}
        return bool(keys & {"uuid", "shortnames", "type"})

    def _dedupe_segment_records(
        self, records: list[tuple[str, dict[str, Any]]]
    ) -> list[tuple[str, dict[str, Any]]]:
        seen: set[str] = set()
        deduped: list[tuple[str, dict[str, Any]]] = []
        for site_uuid, record in records:
            key = str(self._first(record, ["UUID", "uuid", "SegmentUUID", "segmentUuid"]) or id(record))
            if key not in seen:
                seen.add(key)
                deduped.append((site_uuid, record))
        return deduped

    def _map_segment(self, record: dict[str, Any], site_uuid: str) -> Segment:
        segment_uuid = str(
            self._first(record, ["UUID", "uuid", "SegmentUUID", "segmentUuid"])
            or "unknown-segment"
        )
        segment_type_node = record.get("type") or record.get("Type") or {}
        segment_type = (
            self._get_first_short_name(segment_type_node)
            or "Unknown"
        )
        segment_type_uuid = (
            self._first(segment_type_node, ["UUID", "uuid"]) if isinstance(segment_type_node, dict) else None
        )
        info_source = self._info_source(record)
        segment_type_info_source = self._info_source(segment_type_node)
        return Segment(
            segment_uuid=segment_uuid,
            site_uuid=site_uuid,
            segment_name=str(
                self._get_first_short_name(record)
                or segment_uuid
            ),
            segment_type=str(segment_type),
            segment_type_uuid=str(segment_type_uuid) if segment_type_uuid else None,
            segment_type_info_source_uuid=segment_type_info_source[0],
            segment_type_info_source_short_name=segment_type_info_source[1],
            info_source_uuid=info_source[0],
            info_source_short_name=info_source[1],
            status="Unknown",
            description="",
        )

    def _map_measurement_location(
        self,
        record: dict[str, Any],
        segment_uuid: str,
    ) -> MeasurementLocation:
        location_uuid = str(
            self._first(
                record,
                ["UUID", "uuid", "MeasurementLocationUUID", "measurementLocationUuid"],
            )
            or "unknown-measurement-location"
        )
        location_type_node = record.get("type") or record.get("Type") or {}
        location_type = (
            self._get_first_short_name(location_type_node)
            or "Unknown"
        )
        location_type_uuid = (
            self._first(location_type_node, ["UUID", "uuid"])
            if isinstance(location_type_node, dict)
            else None
        )
        value_class = str(self._first(record, ["valueClass", "ValueClass"]) or "")
        default_unit = record.get("defaultUnitOfMeasure") or record.get("DefaultUnitOfMeasure") or {}
        uom_quantity = record.get("UOMQuantity") or record.get("uomQuantity") or {}
        reference_unit = {}
        if isinstance(uom_quantity, dict):
            reference_unit = (
                uom_quantity.get("referenceUnitOfMeasure")
                or uom_quantity.get("ReferenceUnitOfMeasure")
                or {}
            )
        unit = (
            self._get_first_short_name(default_unit)
            or ""
        )
        if not unit and value_class.casefold() == "percentage":
            unit = "%"
        if not unit and value_class.casefold() == "number":
            unit = "—"
        unit_uuid = (
            self._first(default_unit, ["UUID", "uuid"]) if isinstance(default_unit, dict) else None
        )
        uom_quantity_uuid = (
            self._first(uom_quantity, ["UUID", "uuid"]) if isinstance(uom_quantity, dict) else None
        )
        reference_unit_uuid = (
            self._first(reference_unit, ["UUID", "uuid"]) if isinstance(reference_unit, dict) else None
        )
        location_info_source = self._info_source(record)
        location_type_info_source = self._info_source(location_type_node)
        unit_info_source = self._info_source(default_unit)
        uom_quantity_info_source = self._info_source(uom_quantity)
        return MeasurementLocation(
            location_uuid=location_uuid,
            segment_uuid=segment_uuid,
            location_name=str(
                self._get_first_short_name(record)
                or location_uuid
            ),
            location_type=str(location_type),
            type_uuid=str(location_type_uuid) if location_type_uuid else "",
            value_class=value_class,
            unit=unit,
            unit_uuid=str(unit_uuid) if unit_uuid else None,
            reference_unit_uuid=str(reference_unit_uuid) if reference_unit_uuid else None,
            conversion_scale=self._optional_numeric(
                self._first(default_unit, ["conversionScale", "ConversionScale"])
                if isinstance(default_unit, dict)
                else None
            ),
            conversion_offset=self._optional_numeric(
                self._first(default_unit, ["conversionOffset", "ConversionOffset"])
                if isinstance(default_unit, dict)
                else None
            ),
            uom_quantity_uuid=str(uom_quantity_uuid) if uom_quantity_uuid else None,
            uom_quantity=str(
                self._get_first_short_name(uom_quantity)
                or ""
            ),
            info_source_uuid=location_info_source[0],
            info_source_short_name=location_info_source[1],
            measurement_location_type_info_source_uuid=location_type_info_source[0],
            measurement_location_type_info_source_short_name=location_type_info_source[1],
            unit_info_source_uuid=unit_info_source[0],
            unit_info_source_short_name=unit_info_source[1],
            uom_quantity_info_source_uuid=uom_quantity_info_source[0],
            uom_quantity_info_source_short_name=uom_quantity_info_source[1],
            status="Unknown",
            description="",
        )

    def _map_measurement(
        self,
        record: dict[str, Any],
        fallback_location_uuid: str,
        fallback_unit: str,
    ) -> Measurement:
        measurement_uuid = str(
            self._first(record, ["UUID", "uuid", "MeasurementUUID", "measurementUuid"])
            or "unknown-measurement"
        )
        data = record.get("data") or record.get("Data") or {}
        value, unit, value_class, unit_node = self._measurement_value_unit(data, fallback_unit)
        location = record.get("measurementLocation") or record.get("MeasurementLocation") or {}
        timestamp = self._measurement_timestamp(record)
        location_name = (
            self._get_first_short_name(location)
            or "Measurement"
        )
        location_uuid = (
            self._first(location, ["UUID", "uuid"]) if isinstance(location, dict) else None
        )
        info_source = self._info_source(record)
        unit_info_source = self._info_source(unit_node)
        unit_uuid = self._first(unit_node, ["UUID", "uuid"]) if isinstance(unit_node, dict) else None
        return Measurement(
            measurement_uuid=measurement_uuid,
            location_uuid=str(location_uuid or fallback_location_uuid),
            measurement_name=str(location_name),
            measurement_type=value_class,
            value=value,
            unit=unit,
            unit_uuid=str(unit_uuid) if unit_uuid else None,
            timestamp_utc=timestamp,
            status="Unknown",
            info_source_uuid=info_source[0],
            info_source_short_name=info_source[1],
            unit_info_source_uuid=unit_info_source[0],
            unit_info_source_short_name=unit_info_source[1],
        )

    def _measurement_value_unit(self, data: Any, fallback_unit: str) -> tuple[float, str, str, dict[str, Any]]:
        if not isinstance(data, dict):
            return 0.0, fallback_unit, "Unknown", {}
        measure = data.get("measure") or data.get("Measure")
        if isinstance(measure, dict):
            value_node = measure.get("value") or measure.get("Value") or {}
            unit_node = (
                measure.get("UnitOfMeasure")
                or measure.get("unitOfMeasure")
                or measure.get("unitOfMeasure".lower())
                or {}
            )
            unit = (
                self._get_first_short_name(unit_node)
                or fallback_unit
            )
            return self._numeric_value(value_node), unit, "Measure", unit_node if isinstance(unit_node, dict) else {}
        percentage = data.get("percentage") or data.get("Percentage")
        if isinstance(percentage, dict):
            return self._numeric_value(percentage), fallback_unit or "%", "Percentage", {}
        number = data.get("number") or data.get("Number")
        if isinstance(number, dict):
            return self._numeric_value(number), fallback_unit, "Number", {}
        return 0.0, fallback_unit, "Unknown", {}

    def _numeric_value(self, value: Any) -> float:
        if isinstance(value, dict):
            value = value.get("numeric") or value.get("Numeric") or 0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _optional_numeric(self, value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _measurement_timestamp(self, record: dict[str, Any]) -> datetime:
        recorded = record.get("recorded") or record.get("Recorded") or {}
        value = self._first(recorded, ["dateTime", "DateTime"]) if isinstance(recorded, dict) else None
        if isinstance(value, str) and value:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass
        return datetime.now(timezone.utc)

    def _candidate_site_records(self, envelope: Any) -> list[dict[str, Any]]:
        roots: list[Any] = []
        if isinstance(envelope, dict):
            data = envelope.get("data")
            roots.extend(
                [
                    self._get_path(data, ["showSites", "dataArea", "sites"]),
                    self._get_path(data, ["showSites", "dataArea", "sites", "site"]),
                    data,
                    self._get_path(data, ["sites"]),
                    self._get_path(data, ["Sites"]),
                    self._get_path(data, ["Site"]),
                    self._get_path(data, ["payload"]),
                    self._get_path(data, ["payload", "DataArea", "Show", "Site"]),
                    self._get_path(data, ["payload", "DataArea", "Show", "Sites"]),
                    self._get_path(data, ["payload", "DataArea", "Show", "Sites", "Site"]),
                    self._get_path(data, ["DataArea", "Show", "Site"]),
                    self._get_path(data, ["DataArea", "Show", "Sites"]),
                    self._get_path(data, ["DataArea", "Show", "Sites", "Site"]),
                ]
            )
            raw = envelope.get("raw")
            roots.extend(
                [
                    self._get_path(raw, ["showSites", "dataArea", "sites"]),
                    self._get_path(raw, ["showSites", "dataArea", "sites", "site"]),
                ]
            )
            if self.include_raw or not any(self._as_record_list(root) for root in roots):
                roots.append(raw)
        else:
            roots.append(envelope)

        records: list[dict[str, Any]] = []
        for root in roots:
            records.extend(self._as_record_list(root))
        return self._dedupe_records(records)

    def _as_record_list(self, value: Any) -> list[dict[str, Any]]:
        if value is None:
            return []
        if isinstance(value, list):
            records: list[dict[str, Any]] = []
            for item in value:
                records.extend(self._as_record_list(item))
            return records
        if isinstance(value, dict):
            if self._looks_like_site(value):
                return [value]
            for key in (
                "showSites",
                "dataArea",
                "sites",
                "site",
                "Sites",
                "Site",
                "payload",
                "data",
                "DataArea",
                "Show",
                "response",
            ):
                if key in value:
                    nested = self._as_record_list(value[key])
                    if nested:
                        return nested
        return []

    def _as_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        return value if isinstance(value, list) else [value]

    def _looks_like_site(self, value: dict[str, Any]) -> bool:
        keys = {key.casefold() for key in value}
        return bool(
            keys
            & {
                "uuid",
                "siteuuid",
                "site_uuid",
                "name",
                "shortname",
                "shortnames",
                "fullname",
                "description",
                "type",
            }
        )

    def _dedupe_records(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for record in records:
            key = str(self._first(record, ["UUID", "uuid", "SiteUUID", "siteUuid", "site_uuid"]) or id(record))
            if key not in seen:
                seen.add(key)
                deduped.append(record)
        return deduped

    def _map_site(self, record: dict[str, Any]) -> Site:
        site_uuid = str(
            self._first(record, ["UUID", "uuid", "SiteUUID", "siteUuid", "site_uuid"])
            or "unknown-site"
        )
        name = (
            self._get_first_short_name(record)
            or self._text_list_value(record.get("fullName"))
            or self._text_list_value(record.get("FullName"))
            or self._scalar_first(record, ["Name", "name", "FullName", "fullName"])
            or site_uuid
        )
        site_type = (
            self._nested_type_name(record.get("type"))
            or self._nested_type_name(record.get("Type"))
            or self._nested_type_name(record.get("siteType"))
            or self._nested_type_name(record.get("SiteType"))
            or self._scalar_first(record, ["siteType", "SiteType"])
            or ""
        )
        site_type_node = record.get("type") or record.get("Type") or record.get("siteType") or record.get("SiteType") or {}
        site_type_uuid = self._first(site_type_node, ["UUID", "uuid"]) if isinstance(site_type_node, dict) else None
        info_source = self._info_source(record)
        site_type_info_source = self._info_source(site_type_node)
        return Site(
            site_uuid=site_uuid,
            site_name=name,
            site_type=site_type,
            site_type_uuid=str(site_type_uuid) if site_type_uuid else None,
            site_type_info_source_uuid=site_type_info_source[0],
            site_type_info_source_short_name=site_type_info_source[1],
            info_source_uuid=info_source[0],
            info_source_short_name=info_source[1],
            status=str(self._first(record, ["Status", "status"]) or "Unknown"),
            region=str(self._first(record, ["Region", "region"]) or ""),
            description=str(self._first(record, ["Description", "description"]) or ""),
        )

    def _info_source(self, value: Any) -> tuple[str | None, str | None]:
        if not isinstance(value, dict):
            return None, None
        node = value.get("infoSource") or value.get("InfoSource")
        if not isinstance(node, dict):
            return None, None
        uuid = self._first(node, ["UUID", "uuid"])
        short_name = self._get_first_short_name(node)
        return (str(uuid) if uuid else None, str(short_name) if short_name else None)

    def _get_first_short_name(self, value: Any) -> str | None:
        if isinstance(value, str) and value:
            return value
        if isinstance(value, list) and value:
            return self._get_first_short_name(value[0])
        if not isinstance(value, dict):
            return None
        for key in ("shortNames", "ShortNames", "shortName", "ShortName"):
            text = self._get_first_short_name(value.get(key))
            if text:
                return text
        for key in ("text", "Text", "value", "Value"):
            text = value.get(key)
            if isinstance(text, str) and text:
                return text
        return None

    def _text_list_value(self, value: Any) -> str | None:
        if isinstance(value, list) and value:
            return self._text_list_value(value[0])
        if isinstance(value, dict):
            for key in ("text", "Text", "value", "Value"):
                if value.get(key):
                    return str(value[key])
        if isinstance(value, str) and value:
            return value
        return None

    def _nested_type_name(self, value: Any) -> str | None:
        if isinstance(value, str) and value:
            return value
        if not isinstance(value, dict):
            return None
        return self._get_first_short_name(value) or self._text_list_value(
            value.get("fullName")
        ) or self._text_list_value(value.get("FullName"))

    def _scalar_first(self, record: dict[str, Any], keys: list[str]) -> str | None:
        for key in keys:
            value = record.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    def _first(self, record: dict[str, Any], keys: list[str]) -> Any:
        for key in keys:
            if key in record and record[key] not in (None, ""):
                return record[key]
        return None

    def _get_path(self, value: Any, path: list[str]) -> Any:
        current = value
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current
