import json
import sqlite3
import subprocess
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.services.mcegold_cli_discovery_client import (
    CliDiscoveryError,
    MceGoldCliDiscoveryClient,
    redact_sensitive,
)
from tests.fake_discovery_client import MockDiscoveryClient
from app.storage.database import initialize_database
from app.storage.discovered_entity_store import DiscoveredEntityStore


def completed(stdout: str, returncode: int = 0, stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, returncode=returncode, stderr=stderr)


def cli_client(path: str = r"C:\tools\MCEGold.Data.Services.Connector.Cli.exe") -> MceGoldCliDiscoveryClient:
    return MceGoldCliDiscoveryClient(
        cli_path=path,
        connector_config_path="configs/connector.config.json",
        timeout_seconds=5,
        max_items=12,
        include_raw=False,
        sleep_func=lambda _seconds: None,
    )


def successful_post_envelope(request_id: str = "request-1") -> str:
    return json.dumps({"success": True, "data": {"requestMessageId": request_id}})


def pending_read_envelope(code: str = "CommandFailed", raw_fault: str = "There are no messages in the queue") -> str:
    return json.dumps(
        {
            "success": False,
            "command": "request.read-response",
            "data": None,
            "fault": {
                "category": "remote",
                "code": code,
                "message": "Not Found",
                "statusCode": 404,
                "details": [],
            },
            "raw": {"fault": raw_fault},
        }
    )


def successful_sites_envelope() -> str:
    return json.dumps(
        {
            "success": True,
            "command": "request.read-response",
            "data": {"sites": [{"siteUuid": "site-1", "name": "Polled Site"}]},
            "fault": None,
            "raw": None,
        }
    )


def test_polling_first_read_success_posts_once_and_reuses_ids(monkeypatch) -> None:
    sleeps = []
    commands = []
    client = cli_client()
    client.sleep_func = sleeps.append

    def fake_run(command, **kwargs):
        commands.append(command)
        if "post" in command:
            return completed(successful_post_envelope("request-1"))
        return completed(successful_sites_envelope())

    monkeypatch.setattr(subprocess, "run", fake_run)

    sites = client.get_sites("session-1")

    post_commands = [command for command in commands if "post" in command]
    read_commands = [command for command in commands if "read-response" in command]
    assert len(post_commands) == 1
    assert len(read_commands) == 1
    assert sleeps == [0.5]
    assert read_commands[0][read_commands[0].index("--session-id") + 1] == "session-1"
    assert read_commands[0][read_commands[0].index("--request-id") + 1] == "request-1"
    assert "--include-raw" in read_commands[0]
    assert sites[0].site_name == "Polled Site"


def test_polling_one_pending_read_then_success(monkeypatch) -> None:
    sleeps = []
    read_request_ids = []
    call_count = {"read": 0, "post": 0}
    client = cli_client()
    client.sleep_func = sleeps.append

    def fake_run(command, **kwargs):
        if "post" in command:
            call_count["post"] += 1
            return completed(successful_post_envelope("request-1"))
        call_count["read"] += 1
        read_request_ids.append(command[command.index("--request-id") + 1])
        if call_count["read"] == 1:
            return completed(pending_read_envelope(), returncode=6)
        return completed(successful_sites_envelope())

    monkeypatch.setattr(subprocess, "run", fake_run)

    sites = client.get_sites("session-1")

    assert call_count == {"read": 2, "post": 1}
    assert sleeps == [0.5, 2.0]
    assert read_request_ids == ["request-1", "request-1"]
    assert sites[0].site_uuid == "site-1"


def test_polling_full_window_succeeds_on_sixth_attempt(monkeypatch) -> None:
    sleeps = []
    reads = 0
    client = cli_client()
    client.sleep_func = sleeps.append

    def fake_run(command, **kwargs):
        nonlocal reads
        if "post" in command:
            return completed(successful_post_envelope("request-1"))
        reads += 1
        if reads < 6:
            return completed(pending_read_envelope(), returncode=6)
        return completed(successful_sites_envelope())

    monkeypatch.setattr(subprocess, "run", fake_run)

    sites = client.get_sites("session-1")

    assert reads == 6
    assert sleeps == [0.5, 2.0, 2.0, 2.0, 2.0, 2.0]
    assert sites[0].site_name == "Polled Site"


def test_polling_final_timeout_does_not_repost_remove_or_close(monkeypatch) -> None:
    sleeps = []
    commands = []
    client = cli_client()
    client.sleep_func = sleeps.append

    def fake_run(command, **kwargs):
        commands.append(command)
        if "post" in command:
            return completed(successful_post_envelope("request-1"))
        return completed(pending_read_envelope(), returncode=6)

    monkeypatch.setattr(subprocess, "run", fake_run)

    try:
        client.get_sites("session-1")
    except CliDiscoveryError as exc:
        assert "Timed out waiting" in exc.friendly_message
        assert exc.diagnostics["attemptCount"] == 6
        assert exc.diagnostics["requestMessageId"] == "request-1"
    else:
        raise AssertionError("Expected CliDiscoveryError")

    assert len([command for command in commands if "post" in command]) == 1
    read_commands = [command for command in commands if "read-response" in command]
    assert len(read_commands) == 6
    assert all(command[command.index("--session-id") + 1] == "session-1" for command in read_commands)
    assert all(command[command.index("--request-id") + 1] == "request-1" for command in read_commands)
    assert not any("remove-response" in command for command in commands)
    assert not any("close-session" in command for command in commands)
    assert sleeps == [0.5, 2.0, 2.0, 2.0, 2.0, 2.0]


def test_polling_non_transient_404_raises_immediately(monkeypatch) -> None:
    sleeps = []
    reads = 0
    client = cli_client()
    client.sleep_func = sleeps.append

    def fake_run(command, **kwargs):
        nonlocal reads
        if "post" in command:
            return completed(successful_post_envelope("request-1"))
        reads += 1
        return completed(
            pending_read_envelope(raw_fault="Could not find Session"),
            returncode=6,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    try:
        client.get_sites("session-1")
    except CliDiscoveryError as exc:
        assert exc.fault["statusCode"] == 404
    else:
        raise AssertionError("Expected CliDiscoveryError")

    assert reads == 1
    assert sleeps == [0.5]


def test_polling_authentication_failure_raises_immediately(monkeypatch) -> None:
    sleeps = []
    reads = 0
    client = cli_client()
    client.sleep_func = sleeps.append

    def fake_run(command, **kwargs):
        nonlocal reads
        if "post" in command:
            return completed(successful_post_envelope("request-1"))
        reads += 1
        return completed(
            json.dumps(
                {
                    "success": False,
                    "command": "request.read-response",
                    "fault": {
                        "category": "authentication",
                        "code": "CommandFailed",
                        "message": "Unauthorized",
                        "statusCode": 401,
                        "details": [],
                    },
                }
            ),
            returncode=4,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    try:
        client.get_sites("session-1")
    except CliDiscoveryError as exc:
        assert exc.fault["category"] == "authentication"
    else:
        raise AssertionError("Expected CliDiscoveryError")

    assert reads == 1
    assert sleeps == [0.5]


def test_get_sites_uses_shared_post_wait_helper(monkeypatch) -> None:
    client = cli_client()
    calls = []

    def fake_helper(**kwargs):
        calls.append(kwargs)
        return json.loads(successful_sites_envelope()), "request-1", {}, {}

    monkeypatch.setattr(client, "_post_request_and_wait_for_response", fake_helper)

    sites = client.get_sites("session-1")

    assert calls[0]["request_type"] == "GetSites"
    assert sites[0].site_uuid == "site-1"


def test_get_segments_uses_shared_post_wait_helper(monkeypatch) -> None:
    client = cli_client()
    calls = []

    def fake_helper(**kwargs):
        calls.append(kwargs)
        return {"success": True, "data": {"showSegments": {"dataArea": {"segments": []}}}}, "request-1", {}, {}

    monkeypatch.setattr(client, "_post_request_and_wait_for_response", fake_helper)

    client.get_segments("site-1", "session-1")

    assert calls[0]["request_type"] == "GetSegments"


def test_get_measurement_locations_uses_shared_helper_and_parses_delayed_success(monkeypatch) -> None:
    sleeps = []
    reads = 0
    client = cli_client()
    client.sleep_func = sleeps.append

    def fake_run(command, **kwargs):
        nonlocal reads
        if "post" in command:
            return completed(successful_post_envelope("request-1"))
        reads += 1
        if reads == 1:
            return completed(pending_read_envelope(), returncode=6)
        return completed(json.dumps(show_measurement_locations_sample()))

    monkeypatch.setattr(subprocess, "run", fake_run)

    locations = client.get_measurement_locations("segment-1", "session-1")

    assert reads == 2
    assert sleeps == [0.5, 2.0]
    assert locations[1].location_name == "Average Current, Stator"


def test_get_measurements_uses_shared_post_wait_helper(monkeypatch) -> None:
    client = cli_client()
    calls = []

    def fake_helper(**kwargs):
        calls.append(kwargs)
        return {"success": True, "data": {"showMeasurements": {"dataArea": {"measurements": []}}}}, "request-1", {}, {}

    monkeypatch.setattr(client, "_post_request_and_wait_for_response", fake_helper)

    client.get_measurements("location-1", session_id="session-1", segment_uuid="segment-1")

    assert calls[0]["request_type"] == "GetMeasurements"


def test_mock_mode_still_returns_mock_sites() -> None:
    assert MockDiscoveryClient().get_sites()[0].site_name == "Tampa Plant"


def test_cli_command_construction_for_exe_path() -> None:
    client = cli_client(r"C:\tools\cli.exe")
    open_command = client.build_open_request_session_command()
    post_command = client.build_post_get_sites_command("session-1", "payload.json")
    close_command = client.build_close_request_session_command("session-1")

    assert open_command[:3] == [r"C:\tools\cli.exe", "request", "open-session"]
    assert post_command[:4] == [r"C:\tools\cli.exe", "request", "post", "--config"]
    assert "--type" not in post_command
    assert "get-sites" not in post_command
    assert post_command[post_command.index("--input") + 1] == "payload.json"
    assert close_command[:3] == [r"C:\tools\cli.exe", "request", "close-session"]


def test_cli_command_construction_for_dll_path() -> None:
    command = cli_client(r"C:\tools\cli.dll").build_open_request_session_command()

    assert command[:2] == ["dotnet", r"C:\tools\cli.dll"]
    assert "request" in command
    assert "open-session" in command


def test_cli_open_request_session_success_parses_session_id(monkeypatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: completed(json.dumps({"success": True, "data": {"sessionId": "session-1"}})),
    )

    assert cli_client().open_request_session() == "session-1"


def test_cli_open_request_session_success_false_returns_error(monkeypatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: completed(
            json.dumps({"success": False, "fault": {"code": "OpenFailed", "message": "Nope"}})
        ),
    )

    try:
        cli_client().open_request_session()
    except CliDiscoveryError as exc:
        assert exc.fault["code"] == "OpenFailed"
    else:
        raise AssertionError("Expected CliDiscoveryError")


def test_successful_cli_response_parsing(monkeypatch) -> None:
    envelope = {
        "success": True,
        "data": {
            "payload": {
                "DataArea": {
                    "Show": {
                        "Site": [
                            {
                                "UUID": "site-1",
                                "shortName": [{"text": "Real Site"}],
                                "type": {"shortName": [{"text": "Facility"}]},
                                "Status": "Active",
                                "Region": "North",
                                "Description": "From CLI",
                            }
                        ]
                    }
                }
            }
        },
        "fault": None,
    }

    def fake_run(command, **kwargs):
        if "post" in command:
            return completed(json.dumps({"success": True, "data": {"requestMessageId": "request-1"}}))
        return completed(json.dumps(envelope))

    monkeypatch.setattr(subprocess, "run", fake_run)

    sites = cli_client().get_sites("session-1")

    assert len(sites) == 1
    assert sites[0].site_uuid == "site-1"
    assert sites[0].site_name == "Real Site"
    assert sites[0].site_type == "Facility"


def test_get_sites_payload_requests_full_profile(monkeypatch) -> None:
    captured_command = []
    captured_payloads = []

    def fake_run(command, **kwargs):
        if "post" in command:
            captured_command.append(command)
            with open(command[command.index("--input") + 1], encoding="utf-8") as handle:
                captured_payloads.append(json.load(handle))
            return completed(json.dumps({"success": True, "data": {"requestMessageId": "request-1"}}))
        return completed(json.dumps({"success": True, "data": {"sites": []}}))

    monkeypatch.setattr(subprocess, "run", fake_run)

    cli_client().get_sites("session-1")

    assert "--type" not in captured_command[0]
    assert captured_payloads[0] == {
        "requestType": "GetSites",
        "payloadProfile": "Full",
        "maxItems": 12,
        "filters": {},
    }


def test_cli_error_includes_command_diagnostics(monkeypatch) -> None:
    fault = {"code": "InvalidUsage", "message": "Command-line validation failed."}

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: completed(json.dumps({"success": False, "fault": fault}), returncode=2, stderr="bad"),
    )

    try:
        cli_client().get_sites("session-1")
    except CliDiscoveryError as exc:
        safe = exc.to_safe_dict()
        diagnostics = safe["diagnostics"]
        assert safe["exitCode"] == 2
        assert safe["stdout"]
        assert safe["stderr"] == "bad"
        assert diagnostics["resolvedCliPath"].endswith("MCEGold.Data.Services.Connector.Cli.exe")
        assert diagnostics["workingDirectory"]
        assert "--type" not in diagnostics["argumentList"]
        assert diagnostics["inputPayloadPath"].endswith(".get-sites.json")
    else:
        raise AssertionError("Expected CliDiscoveryError")


def test_successful_mapping_from_data_sites(monkeypatch) -> None:
    envelope = {"success": True, "data": {"sites": [{"siteUuid": "abc", "name": "Mapped Site"}]}}
    def fake_run(command, **kwargs):
        if "post" in command:
            return completed(json.dumps({"success": True, "data": {"requestMessageId": "request-1"}}))
        return completed(json.dumps(envelope))

    monkeypatch.setattr(subprocess, "run", fake_run)

    site = cli_client().get_sites("session-1")[0]

    assert site.site_uuid == "abc"
    assert site.site_name == "Mapped Site"
    assert site.status == "Unknown"


def test_show_sites_shape_parser_returns_expected_sites() -> None:
    sample = {
        "success": True,
        "data": {
            "showSites": {
                "dataArea": {
                    "sites": [
                        {
                            "site": [
                                {
                                    "UUID": "73ffe278-862d-4226-b37c-b09bd32696af",
                                    "shortName": [{"text": "PdMA Facility"}],
                                    "type": {
                                        "UUID": "d99b1a17-ed17-4375-9e82-ccb99481dd8a",
                                        "shortName": [{"text": "Office Building"}],
                                    },
                                },
                                {
                                    "UUID": "11111111-1111-4111-8111-111111111111",
                                    "shortName": [{"text": "Site Two"}],
                                    "type": {"shortName": [{"text": "Facility"}]},
                                },
                            ]
                        },
                        {
                            "site": {
                                "UUID": "22222222-2222-4222-8222-222222222222",
                                "shortName": [{"text": "Site Three"}],
                                "type": {"shortName": [{"text": "Industrial Plant"}]},
                            }
                        },
                        {
                            "site": [
                                {
                                    "UUID": "33333333-3333-4333-8333-333333333333",
                                    "shortName": [{"text": "Site Four"}],
                                    "type": {"shortName": [{"text": "Vehicle"}]},
                                },
                                {
                                    "UUID": "44444444-4444-4444-8444-444444444444",
                                    "shortName": [{"text": "Site Five"}],
                                    "type": {"shortName": [{"text": "Mobile Object"}]},
                                },
                            ]
                        },
                    ]
                }
            }
        },
    }

    sites = cli_client()._parse_sites(sample)

    assert len(sites) == 5
    assert sites[0].site_name == "PdMA Facility"
    assert sites[0].site_uuid == "73ffe278-862d-4226-b37c-b09bd32696af"
    assert sites[0].site_type == "Office Building"


def test_show_sites_parser_supports_ccom_plural_short_names() -> None:
    sample = {
        "success": True,
        "data": {
            "payload": {
                "showSites": {
                    "dataArea": {
                        "sites": [
                            {
                                "count": 1,
                                "site": [
                                    {
                                        "@@type": "Site",
                                        "UUID": "7431b9cb-92e6-407b-a6ca-660ae95ec1de",
                                        "shortNames": [{"text": "Installation Site"}],
                                        "type": {
                                            "@@type": "SiteType",
                                            "UUID": "d99b1a17-ed17-4375-9e82-ccb99481dd8a",
                                            "shortNames": [{"text": "Office Building"}],
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                }
            }
        },
    }

    site = cli_client()._parse_sites(sample)[0]

    assert site.site_uuid == "7431b9cb-92e6-407b-a6ca-660ae95ec1de"
    assert site.site_name == "Installation Site"
    assert site.site_type == "Office Building"


def test_show_sites_parser_supports_sites_child_key_and_short_name_casing() -> None:
    sample = {
        "success": True,
        "data": {
            "payload": {
                "showSites": {
                    "dataArea": {
                        "sites": [
                            {
                                "count": 1,
                                "sites": [
                                    {
                                        "UUID": "site-1",
                                        "ShortNames": [{"text": "Installation Site"}],
                                        "type": {"ShortName": {"text": "Office Building"}},
                                    }
                                ],
                            }
                        ]
                    }
                }
            }
        },
    }

    sites = cli_client()._parse_sites(sample)

    assert len(sites) == 1
    assert sites[0].site_uuid == "site-1"
    assert sites[0].site_name == "Installation Site"
    assert sites[0].site_type == "Office Building"


def test_site_mapper_uses_leaf_record_and_does_not_stringify_type_dict() -> None:
    client = cli_client()
    wrapper = {
        "count": 1,
        "site": [
            {
                "@@type": "Site",
                "UUID": "7431b9cb-92e6-407b-a6ca-660ae95ec1de",
                "shortNames": [{"text": "Installation Site"}],
                "type": {
                    "@@type": "SiteType",
                    "UUID": "d99b1a17-ed17-4375-9e82-ccb99481dd8a",
                    "shortNames": [{"text": "Office Building"}],
                },
            }
        ],
    }

    records = client._as_record_list(wrapper)
    site = client._map_site(records[0])

    assert records == wrapper["site"]
    assert site.site_uuid == "7431b9cb-92e6-407b-a6ca-660ae95ec1de"
    assert site.site_name == "Installation Site"
    assert site.site_type == "Office Building"
    assert "{'@@type'" not in site.site_type


def test_site_mapper_handles_site_type_alias_without_raw_dict_fallback() -> None:
    site = cli_client()._map_site(
        {
            "UUID": "site-1",
            "shortName": {"text": "Site One"},
            "SiteType": {
                "UUID": "type-1",
                "ShortNames": [{"text": "Office Building"}],
            },
        }
    )

    assert site.site_name == "Site One"
    assert site.site_type == "Office Building"


def test_show_segments_shape_parser_returns_expected_segments() -> None:
    sample = {
        "success": True,
        "data": {
            "showSegments": {
                "dataArea": {
                    "show": {"recordSetCount": 2},
                    "segments": [
                        {
                            "count": 2,
                            "site": {
                                "@@type": "Site",
                                "UUID": "73ffe278-862d-4226-b37c-b09bd32696af",
                                "shortName": [{"text": "PdMA Facility"}],
                            },
                            "segments": [
                                {
                                    "@@type": "Segment",
                                    "UUID": "f6c64165-89f2-4466-9950-7e28f05ce053",
                                    "shortNames": [{"text": "AC Unit #1 Compressor"}],
                                    "type": {
                                        "@@type": "SegmentsType",
                                        "UUID": "6b1c4f9e-24be-41db-9083-4fc4b958af2e",
                                        "shortNames": [
                                            {
                                                "text": "Air Conditioning System, Vapor Compression, AC Unit, Hermetic"
                                            }
                                        ],
                                    },
                                },
                                {
                                    "@@type": "Segment",
                                    "UUID": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2",
                                    "shortNames": [{"text": "AC Unit #1 Fan"}],
                                    "type": {"shortNames": [{"text": "Fan"}]},
                                },
                            ],
                        }
                    ],
                }
            }
        },
    }

    segments = cli_client()._parse_segments(sample)

    assert len(segments) == 2
    assert segments[0].segment_name == "AC Unit #1 Compressor"
    assert segments[0].segment_uuid == "f6c64165-89f2-4466-9950-7e28f05ce053"
    assert segments[0].segment_type == "Air Conditioning System, Vapor Compression, AC Unit, Hermetic"
    assert segments[0].segment_type_uuid == "6b1c4f9e-24be-41db-9083-4fc4b958af2e"


def test_show_segments_parser_supports_segment_child_key_and_short_name_casing() -> None:
    sample = {
        "success": True,
        "data": {
            "payload": {
                "showSegments": {
                    "dataArea": {
                        "segments": [
                            {
                                "count": 1,
                                "site": {"UUID": "site-1"},
                                "segment": [
                                    {
                                        "UUID": "segment-1",
                                        "ShortNames": [{"text": "Compressor"}],
                                        "type": {
                                            "UUID": "type-1",
                                            "ShortName": {"text": "Compressor, Displacement, Rotary"},
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                }
            }
        },
    }

    segments = cli_client()._parse_segments(sample)

    assert len(segments) == 1
    assert segments[0].site_uuid == "site-1"
    assert segments[0].segment_uuid == "segment-1"
    assert segments[0].segment_name == "Compressor"
    assert segments[0].segment_type == "Compressor, Displacement, Rotary"
    assert segments[0].segment_type_uuid == "type-1"


def test_get_segments_payload_includes_site_and_optional_type(monkeypatch) -> None:
    captured_payloads = []

    def fake_run(command, **kwargs):
        if "post" in command:
            with open(command[command.index("--input") + 1], encoding="utf-8") as handle:
                captured_payloads.append(json.load(handle))
            return completed(json.dumps({"success": True, "data": {"requestMessageId": "request-1"}}))
        return completed(json.dumps({"success": True, "data": {"showSegments": {"dataArea": {"segments": []}}}}))

    monkeypatch.setattr(subprocess, "run", fake_run)

    cli_client().get_segments(
        "73ffe278-862d-4226-b37c-b09bd32696af",
        "session-1",
        "6b1c4f9e-24be-41db-9083-4fc4b958af2e",
        max_items=50,
    )

    assert captured_payloads[0]["requestType"] == "GetSegments"
    assert captured_payloads[0]["payloadProfile"] == "Full"
    assert captured_payloads[0]["maxItems"] == 50
    assert captured_payloads[0]["filters"]["siteUuid"] == "73ffe278-862d-4226-b37c-b09bd32696af"
    assert captured_payloads[0]["filters"]["typeUuid"] == "6b1c4f9e-24be-41db-9083-4fc4b958af2e"


def show_measurement_locations_sample() -> dict:
    def location(
        uuid: str,
        name: str,
        location_type: str,
        value_class: str,
        unit: str | None = None,
        unit_uuid: str | None = None,
        quantity: str | None = None,
    ) -> dict:
        item = {
            "@@type": "MeasurementLocation",
            "UUID": uuid,
            "shortNames": [{"text": name}],
            "type": {
                "@@type": "MeasurementLocationType",
                "UUID": f"type-{uuid[-4:]}",
                "shortNames": [{"text": location_type}],
            },
            "valueClass": value_class,
        }
        if unit:
            item["defaultUnitOfMeasure"] = {
                "@@type": "UnitOfMeasure",
                "UUID": unit_uuid or f"unit-{uuid[-4:]}",
                "shortNames": [{"text": unit}],
                "infoSource": {
                    "UUID": f"info-unit-{uuid[-4:]}",
                    "shortNames": [{"text": "Unit Source"}],
                },
            }
        if quantity:
            item["UOMQuantity"] = {
                "@@type": "UOMQuantity",
                "UUID": f"quantity-{uuid[-4:]}",
                "shortNames": [{"text": quantity}],
                "infoSource": {
                    "UUID": f"info-quantity-{uuid[-4:]}",
                    "shortNames": [{"text": "Quantity Source"}],
                },
            }
        item["infoSource"] = {
            "UUID": f"info-location-{uuid[-4:]}",
            "shortNames": [{"text": "Location Source"}],
        }
        item["type"]["infoSource"] = {
            "UUID": f"info-location-type-{uuid[-4:]}",
            "shortNames": [{"text": "Location Type Source"}],
        }
        return item

    locations = [
        location(
            "554113ec-d619-4998-93a3-e07f569e3931",
            "% Current Imbalance, Stator",
            "Current Imbalance, Percentage",
            "Percentage",
        ),
        location(
            "554113ec-d619-4998-93a3-e07f569e3932",
            "Average Current, Stator",
            "Average Current",
            "Measure",
            unit="Amperes",
            quantity="Electric Current",
        ),
        location(
            "554113ec-d619-4998-93a3-e07f569e3933",
            "Speed RPM, Stator",
            "Rotational Speed",
            "Measure",
            unit="Revolutions Per Minute (RPM)",
            quantity="Rotational Speed",
        ),
        location(
            "554113ec-d619-4998-93a3-e07f569e3934",
            "Pole Count, Stator",
            "Pole Count",
            "Number",
        ),
    ]
    for index in range(40):
        locations.append(
            location(
                f"554113ec-d619-4998-93a3-e07f569e39{35 + index:02d}",
                f"Generated Location {index + 1}, Stator",
                "Generated Type",
                "Measure",
                unit="Volts",
            )
        )
    return {
        "success": True,
        "data": {
            "showMeasurementLocations": {
                "dataArea": {
                    "show": {"recordSetCount": 44},
                    "measurementLocations": [
                        {
                            "count": 44,
                            "segment": {
                                "@@type": "Segment",
                                "UUID": "f6c64165-89f2-4466-9950-7e28f05ce053",
                                "shortNames": [{"text": "AC Unit #1 Compressor"}],
                            },
                            "measurementLocation": locations,
                        }
                    ],
                }
            }
        },
    }


def test_show_measurement_locations_shape_parser_returns_expected_locations() -> None:
    locations = cli_client()._parse_measurement_locations(show_measurement_locations_sample())

    assert len(locations) == 44
    assert locations[0].location_name == "% Current Imbalance, Stator"
    assert locations[0].location_uuid == "554113ec-d619-4998-93a3-e07f569e3931"
    assert locations[0].location_type == "Current Imbalance, Percentage"
    assert locations[0].value_class == "Percentage"
    assert next(item for item in locations if item.location_name == "Average Current, Stator").unit == "Amperes"
    assert next(item for item in locations if item.location_name == "Speed RPM, Stator").unit == "Revolutions Per Minute (RPM)"
    assert locations[0].unit == "%"
    average_current = next(item for item in locations if item.location_name == "Average Current, Stator")
    assert average_current.info_source_uuid == "info-location-3932"
    assert average_current.measurement_location_type_info_source_uuid == "info-location-type-3932"
    assert average_current.unit_info_source_uuid == "info-unit-3932"
    assert average_current.uom_quantity_uuid == "quantity-3932"
    assert average_current.uom_quantity_info_source_uuid == "info-quantity-3932"
    assert next(item for item in locations if item.location_name == "Pole Count, Stator").unit == "—"


def test_full_profile_named_info_source_response_persists_dim_info_source(tmp_path) -> None:
    locations = cli_client()._parse_measurement_locations(show_measurement_locations_sample())
    average_current = next(item for item in locations if item.location_name == "Average Current, Stator")
    db_path = tmp_path / "discovery_portal.db"
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        site_key = connection.execute(
            """
            INSERT INTO DimSite(SiteUuid, SiteName, FirstSeenUtc, LastSeenUtc)
            VALUES ('site-1', 'Site 1', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
            """
        ).lastrowid
        connection.execute(
            """
            INSERT INTO DimSegment(SegmentUuid, SegmentName, SiteUuid, SiteKey, FirstSeenUtc, LastSeenUtc)
            VALUES (?, 'Segment 1', 'site-1', ?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
            """,
            (average_current.segment_uuid, site_key),
        )
        DiscoveredEntityStore(connection).save_measurement_locations(
            [average_current.model_dump()]
        )
        info_sources = {
            row[0]: row[1]
            for row in connection.execute("SELECT InfoSourceUuid, ShortName FROM DimInfoSource")
        }

    assert info_sources == {
        "info-location-3932": "Location Source",
        "info-location-type-3932": "Location Type Source",
        "info-unit-3932": "Unit Source",
        "info-quantity-3932": "Quantity Source",
    }


def test_info_source_helper_extracts_uuid_and_optional_short_name() -> None:
    client = cli_client()

    named = client._info_source(
        {
            "infoSource": {
                "UUID": "info-runtime",
                "shortNames": [{"text": "Runtime Source"}],
            }
        }
    )
    uuid_only = client._info_source({"infoSource": {"UUID": "info-runtime-uuid-only"}})

    assert named == ("info-runtime", "Runtime Source")
    assert uuid_only == ("info-runtime-uuid-only", None)


def test_show_measurement_locations_parser_supports_plural_child_key_and_short_name_casing() -> None:
    sample = {
        "success": True,
        "data": {
            "payload": {
                "showMeasurementLocations": {
                    "dataArea": {
                        "measurementLocations": [
                            {
                                "count": 1,
                                "segment": {"UUID": "segment-1"},
                                "measurementLocations": [
                                    {
                                        "UUID": "location-1",
                                        "ShortNames": [{"text": "Average Current, Stator"}],
                                        "type": {
                                            "UUID": "type-1",
                                            "shortNames": [{"text": "Average Current"}],
                                        },
                                        "valueClass": "Measure",
                                        "defaultUnitOfMeasure": {
                                            "UUID": "unit-1",
                                            "ShortName": {"text": "Amperes"},
                                        },
                                        "UOMQuantity": {
                                            "ShortNames": [{"text": "Electric Current"}],
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                }
            }
        },
    }

    locations = cli_client()._parse_measurement_locations(sample)

    assert len(locations) == 1
    assert locations[0].segment_uuid == "segment-1"
    assert locations[0].location_uuid == "location-1"
    assert locations[0].location_name == "Average Current, Stator"
    assert locations[0].location_type == "Average Current"
    assert locations[0].unit == "Amperes"
    assert locations[0].unit_uuid == "unit-1"
    assert locations[0].uom_quantity == "Electric Current"


def test_get_measurement_locations_payload_includes_segment_and_optional_type(monkeypatch) -> None:
    captured_payloads = []

    def fake_run(command, **kwargs):
        if "post" in command:
            with open(command[command.index("--input") + 1], encoding="utf-8") as handle:
                captured_payloads.append(json.load(handle))
            return completed(json.dumps({"success": True, "data": {"requestMessageId": "request-1"}}))
        return completed(
            json.dumps(
                {"success": True, "data": {"showMeasurementLocations": {"dataArea": {"measurementLocations": []}}}}
            )
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    cli_client().get_measurement_locations(
        "f6c64165-89f2-4466-9950-7e28f05ce053",
        "session-1",
        "89f63bd9-15d6-49a5-991b-38a41ed6cd34",
        max_items=50,
    )

    assert captured_payloads[0]["requestType"] == "GetMeasurementLocations"
    assert captured_payloads[0]["payloadProfile"] == "Full"
    assert captured_payloads[0]["maxItems"] == 50
    assert captured_payloads[0]["filters"]["segmentUuid"] == "f6c64165-89f2-4466-9950-7e28f05ce053"
    assert captured_payloads[0]["filters"]["typeUuid"] == "89f63bd9-15d6-49a5-991b-38a41ed6cd34"


def show_measurements_sample() -> dict:
    return {
        "success": True,
        "data": {
            "showMeasurements": {
                "dataArea": {
                    "measurements": [
                        {
                            "count": 3,
                            "measurement": [
                                {
                                    "@@type": "SingleDataMeasurement",
                                    "UUID": "m-001",
                                    "recorded": {"dateTime": "2026-01-01T00:00:00Z"},
                                    "data": {
                                        "measure": {
                                            "value": {"numeric": 12.5},
                                            "UnitOfMeasure": {
                                                "UUID": "unit-amps",
                                                "shortNames": [{"text": "Amperes"}],
                                                "infoSource": {
                                                    "UUID": "info-unit-measurement",
                                                    "shortNames": [{"text": "Unit Runtime Source"}],
                                                },
                                            },
                                        }
                                    },
                                    "infoSource": {
                                        "UUID": "info-measurement",
                                        "shortNames": [{"text": "Measurement Runtime Source"}],
                                    },
                                    "measurementLocation": {
                                        "UUID": "55555555-5555-4555-8555-555555555555",
                                        "shortNames": [{"text": "Average Current, Stator"}],
                                    },
                                    "segment": {"UUID": "22222222-2222-4222-8222-222222222222"},
                                },
                                {
                                    "UUID": "m-002",
                                    "recorded": {"dateTime": "2026-01-01T00:01:00Z"},
                                    "data": {"percentage": {"numeric": 2.5}},
                                    "measurementLocation": {
                                        "UUID": "55555555-5555-4555-8555-555555555555"
                                    },
                                },
                                {
                                    "UUID": "m-003",
                                    "recorded": {"dateTime": "2026-01-01T00:02:00Z"},
                                    "data": {"number": {"numeric": 4}},
                                },
                            ],
                        }
                    ]
                }
            }
        },
    }


def test_show_measurements_shape_parser_extracts_values_and_units() -> None:
    measurements = cli_client()._parse_measurements(
        show_measurements_sample(),
        fallback_location_uuid="55555555-5555-4555-8555-555555555555",
        fallback_unit="%",
    )

    assert len(measurements) == 3
    assert measurements[0].measurement_uuid == "m-001"
    assert measurements[0].timestamp_utc.isoformat() == "2026-01-01T00:00:00+00:00"
    assert measurements[0].value == 12.5
    assert measurements[0].unit == "Amperes"
    assert measurements[0].unit_uuid == "unit-amps"
    assert measurements[0].info_source_uuid == "info-measurement"
    assert measurements[0].info_source_short_name == "Measurement Runtime Source"
    assert measurements[0].unit_info_source_uuid == "info-unit-measurement"
    assert measurements[0].unit_info_source_short_name == "Unit Runtime Source"
    assert measurements[1].value == 2.5
    assert measurements[1].unit == "%"
    assert measurements[2].value == 4.0
    assert measurements[2].location_uuid == "55555555-5555-4555-8555-555555555555"


def test_show_measurements_parser_supports_plural_child_key_and_short_name_casing() -> None:
    sample = {
        "success": True,
        "data": {
            "payload": {
                "showMeasurements": {
                    "dataArea": {
                        "measurements": [
                            {
                                "count": 1,
                                "measurements": [
                                    {
                                        "UUID": "measurement-1",
                                        "recorded": {"dateTime": "2026-01-01T00:00:00Z"},
                                        "data": {
                                            "measure": {
                                                "value": {"numeric": 42},
                                                "UnitOfMeasure": {
                                                    "UUID": "unit-1",
                                                    "ShortNames": [{"text": "Amperes"}],
                                                },
                                            }
                                        },
                                        "measurementLocation": {
                                            "UUID": "location-1",
                                            "ShortName": {"text": "Average Current, Stator"},
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                }
            }
        },
    }

    measurements = cli_client()._parse_measurements(
        sample,
        fallback_location_uuid="fallback-location",
        fallback_unit="fallback-unit",
    )

    assert len(measurements) == 1
    assert measurements[0].measurement_uuid == "measurement-1"
    assert measurements[0].location_uuid == "location-1"
    assert measurements[0].measurement_name == "Average Current, Stator"
    assert measurements[0].unit == "Amperes"
    assert measurements[0].unit_uuid == "unit-1"
    assert measurements[0].value == 42.0


def test_show_measurements_parser_extracts_lower_camel_unit_uuid() -> None:
    sample = {
        "success": True,
        "data": {
            "showMeasurements": {
                "dataArea": {
                    "measurements": [
                        {
                            "UUID": "measurement-1",
                            "recorded": {"dateTime": "2026-01-01T00:00:00Z"},
                            "data": {
                                "measure": {
                                    "value": {"numeric": 42},
                                    "unitOfMeasure": {
                                        "UUID": "unit-lower-camel",
                                        "shortNames": [{"text": "Amperes"}],
                                    },
                                }
                            },
                            "measurementLocation": {"UUID": "location-1"},
                        }
                    ]
                }
            }
        },
    }

    measurements = cli_client()._parse_measurements(
        sample,
        fallback_location_uuid="fallback-location",
        fallback_unit="fallback-unit",
    )

    assert measurements[0].unit_uuid == "unit-lower-camel"
    assert measurements[0].unit == "Amperes"


def test_get_measurements_payload_uses_only_supported_fields(monkeypatch) -> None:
    captured_payloads = []

    def fake_run(command, **kwargs):
        if "post" in command:
            with open(command[command.index("--input") + 1], encoding="utf-8") as handle:
                captured_payloads.append(json.load(handle))
            return completed(json.dumps({"success": True, "data": {"requestMessageId": "request-1"}}))
        return completed(json.dumps({"success": True, "data": {"showMeasurements": {"dataArea": {"measurements": []}}}}))

    monkeypatch.setattr(subprocess, "run", fake_run)
    client = MceGoldCliDiscoveryClient(
        cli_path=r"C:\tools\cli.exe",
        connector_config_path="config.json",
        measurement_max_items=25,
    )

    client.get_measurements(
        "55555555-5555-4555-8555-555555555555",
        session_id="session-1",
        segment_uuid="22222222-2222-4222-8222-222222222222",
    )

    payload = captured_payloads[0]
    payload_json = json.dumps(payload)
    assert "last_n_data" not in payload_json
    assert payload == {
        "requestType": "GetMeasurements",
        "payloadProfile": "Full",
        "maxItems": 25,
        "lastNData": 25,
        "filters": {
            "measurementLocationUuid": "55555555-5555-4555-8555-555555555555",
            "segmentUuid": "22222222-2222-4222-8222-222222222222",
        },
    }


def test_get_measurements_payload_includes_max_items_and_optional_dates_only(monkeypatch) -> None:
    captured_payloads = []

    def fake_run(command, **kwargs):
        if "post" in command:
            with open(command[command.index("--input") + 1], encoding="utf-8") as handle:
                captured_payloads.append(json.load(handle))
            return completed(json.dumps({"success": True, "data": {"requestMessageId": "request-1"}}))
        return completed(json.dumps({"success": True, "data": {"showMeasurements": {"dataArea": {"measurements": []}}}}))

    monkeypatch.setattr(subprocess, "run", fake_run)

    cli_client().get_measurements(
        "55555555-5555-4555-8555-555555555555",
        session_id="session-1",
        segment_uuid="22222222-2222-4222-8222-222222222222",
        recorded_from="2026-01-01T00:00:00Z",
        recorded_to="2026-01-02T00:00:00Z",
        max_items=250,
    )

    payload = captured_payloads[0]
    payload_json = json.dumps(payload)
    assert payload["maxItems"] == 250
    assert payload["payloadProfile"] == "Full"
    assert payload["lastNData"] == 250
    assert "last_n_data" not in payload_json
    assert payload["filters"]["recordedFrom"] == "2026-01-01T00:00:00Z"
    assert payload["filters"]["recordedTo"] == "2026-01-02T00:00:00Z"
    assert "measurementType" not in payload_json
    assert "unit" not in payload_json
    assert "status" not in payload_json


def test_get_measurements_payload_omits_blank_dates_and_mirrors_last_n_data(monkeypatch) -> None:
    captured_payloads = []

    def fake_run(command, **kwargs):
        if "post" in command:
            with open(command[command.index("--input") + 1], encoding="utf-8") as handle:
                captured_payloads.append(json.load(handle))
            return completed(json.dumps({"success": True, "data": {"requestMessageId": "request-1"}}))
        return completed(json.dumps({"success": True, "data": {"showMeasurements": {"dataArea": {"measurements": []}}}}))

    monkeypatch.setattr(subprocess, "run", fake_run)

    cli_client().get_measurements(
        "55555555-5555-4555-8555-555555555555",
        session_id="session-1",
        segment_uuid="22222222-2222-4222-8222-222222222222",
        recorded_from="",
        recorded_to="",
        max_items=100,
    )

    payload = captured_payloads[0]
    payload_json = json.dumps(payload)
    assert payload["maxItems"] == 100
    assert payload["payloadProfile"] == "Full"
    assert payload["lastNData"] == 100
    assert "last_n_data" not in payload_json
    assert "recordedFrom" not in payload["filters"]
    assert "recordedTo" not in payload["filters"]


def test_get_measurements_payload_mirrors_supported_max_items_to_last_n_data(monkeypatch) -> None:
    captured_payloads = []

    def fake_run(command, **kwargs):
        if "post" in command:
            with open(command[command.index("--input") + 1], encoding="utf-8") as handle:
                captured_payloads.append(json.load(handle))
            return completed(json.dumps({"success": True, "data": {"requestMessageId": "request-1"}}))
        return completed(json.dumps({"success": True, "data": {"showMeasurements": {"dataArea": {"measurements": []}}}}))

    monkeypatch.setattr(subprocess, "run", fake_run)
    client = cli_client()

    for selected_max_items in (50, 100, 250):
        client.get_measurements(
            "55555555-5555-4555-8555-555555555555",
            session_id="session-1",
            segment_uuid="22222222-2222-4222-8222-222222222222",
            max_items=selected_max_items,
        )

    assert [
        (payload["maxItems"], payload["lastNData"])
        for payload in captured_payloads
    ] == [(50, 50), (100, 100), (250, 250)]


def test_success_false_envelope_handling(monkeypatch) -> None:
    envelope = {
        "success": False,
        "fault": {"code": "RemoteFailure", "message": "No response"},
    }
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed(json.dumps(envelope)))

    try:
        cli_client().get_sites("session-1")
    except CliDiscoveryError as exc:
        assert exc.fault["code"] == "RemoteFailure"
    else:
        raise AssertionError("Expected CliDiscoveryError")


def test_fault_object_handling_with_nonzero_exit(monkeypatch) -> None:
    envelope = {"success": False, "fault": {"code": "BadConfig", "message": "Invalid"}}
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: completed(json.dumps(envelope), returncode=2, stderr="bad"),
    )

    try:
        cli_client().get_sites("session-1")
    except CliDiscoveryError as exc:
        assert exc.exit_code == 2
        assert exc.fault["code"] == "BadConfig"
    else:
        raise AssertionError("Expected CliDiscoveryError")


def test_invalid_json_handling(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed("not-json"))

    try:
        cli_client().get_sites("session-1")
    except CliDiscoveryError as exc:
        assert "invalid JSON" in exc.friendly_message
    else:
        raise AssertionError("Expected CliDiscoveryError")


def test_empty_stdout_handling(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed(""))

    try:
        cli_client().get_sites("session-1")
    except CliDiscoveryError as exc:
        assert "no JSON output" in exc.friendly_message
    else:
        raise AssertionError("Expected CliDiscoveryError")


def test_nonzero_exit_code_handling(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed("{}", returncode=1, stderr="failed"))

    try:
        cli_client().get_sites("session-1")
    except CliDiscoveryError as exc:
        assert exc.exit_code == 1
        assert exc.stderr == "failed"
    else:
        raise AssertionError("Expected CliDiscoveryError")


def test_timeout_handling(monkeypatch) -> None:
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=5, stderr="late")

    monkeypatch.setattr(subprocess, "run", raise_timeout)

    try:
        cli_client().get_sites("session-1")
    except CliDiscoveryError as exc:
        assert exc.timeout_seconds == 5
        assert "timed out" in exc.friendly_message
    else:
        raise AssertionError("Expected CliDiscoveryError")


def test_process_start_os_error_becomes_cli_discovery_error(monkeypatch) -> None:
    for error in (
        FileNotFoundError(2, "The system cannot find the file specified"),
        OSError("The CLI host could not be started"),
    ):
        def raise_os_error(*args, **kwargs):
            raise error

        monkeypatch.setattr(subprocess, "run", raise_os_error)

        try:
            cli_client(r"C:\missing\cli.exe").open_request_session()
        except CliDiscoveryError as exc:
            safe = exc.to_safe_dict()
            assert "could not be started" in exc.friendly_message
            assert exc.diagnostics["argumentList"][0] == r"C:\missing\cli.exe"
            assert safe["command"][0] == r"C:\missing\cli.exe"
            assert safe["diagnostics"]["argumentList"][0] == r"C:\missing\cli.exe"
        else:
            raise AssertionError("Expected CliDiscoveryError")


def test_missing_cli_path_handling() -> None:
    try:
        cli_client("").open_request_session()
    except CliDiscoveryError as exc:
        assert "MCEGOLD_CLI_PATH" in exc.friendly_message
    else:
        raise AssertionError("Expected CliDiscoveryError")


def test_cli_close_request_session_is_called_with_session_id(monkeypatch) -> None:
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return completed(json.dumps({"success": True, "data": {}}))

    monkeypatch.setattr(subprocess, "run", fake_run)

    cli_client().close_request_session("session-1")

    assert "close-session" in captured["command"]
    assert "session-1" in captured["command"]


def test_sensitive_value_redaction() -> None:
    text = "password=secret apiKey=abc userName=bob Authorization: Basic abc123 Bearer token456"

    redacted = redact_sensitive(text)

    assert "secret" not in redacted
    assert "abc123" not in redacted
    assert "token456" not in redacted
    assert "***REDACTED***" in redacted


def test_api_sites_in_mock_mode() -> None:
    with TestClient(app) as client:
        try:
            object.__setattr__(routes.settings, "connector_mode", "mock")
            app.state.discovery_client = MockDiscoveryClient()
            app.state.discovery_client_mode = "mock"
            response = client.get("/api/sites")
        finally:
            app.state.discovery_client = MockDiscoveryClient()
            app.state.discovery_client_mode = "mock"

    assert response.status_code == 200
    assert response.json()[0]["site_name"] == "Tampa Plant"


def test_api_sites_in_cli_error_mode_does_not_crash() -> None:
    with TestClient(app) as client:
        try:
            client.post("/discovery/connection-mode", data={"mode": "cli"})
            app.state.discovery_client = cli_client("")
            app.state.discovery_client_mode = "cli"
            response = client.get("/api/sites")
        finally:
            app.state.discovery_client = MockDiscoveryClient()
            app.state.discovery_client_mode = "mock"

    assert response.status_code == 502
    assert response.json()["success"] is False
    assert "MCEGOLD_CLI_PATH" in response.json()["error"]["message"]

