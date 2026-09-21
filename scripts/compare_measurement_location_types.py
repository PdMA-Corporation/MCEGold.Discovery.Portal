from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.services.reference_data_service import ReferenceDataService


DEFAULT_MESSAGE_PATH = Path("data/show-measurement-locations.json")
DEFAULT_REFERENCE_PATH = Path("docs/CCOM Reference Data.xml")
DEFAULT_REPORT_PATH = Path("docs/measurement-location-type-reference-comparison.md")
DEFAULT_ADDENDUM_PATH = Path("docs/measurement-location-type-reference-addendum.csv")


@dataclass(frozen=True)
class MessageType:
    uuid: str
    name: str
    usage_count: int
    example_location_name: str


@dataclass(frozen=True)
class ReferenceType:
    uuid: str
    name: str
    source: str


@dataclass(frozen=True)
class ComparisonRow:
    status: str
    uuid: str
    message_name: str
    reference_name: str
    usage_count: int
    example_location_name: str
    source: str


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare ShowMeasurementLocations MeasurementLocationType UUIDs with CCOM Reference Data XML."
    )
    parser.add_argument("--message-json", type=Path, default=DEFAULT_MESSAGE_PATH)
    parser.add_argument(
        "--reference-xml",
        dest="reference_xml",
        type=Path,
        default=DEFAULT_REFERENCE_PATH,
    )
    parser.add_argument("--sheet", default="CCOM Reference Data", help="Retained for compatibility; ignored for XML input.")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--addendum", type=Path, default=DEFAULT_ADDENDUM_PATH)
    args = parser.parse_args()

    message = load_json(args.message_json)
    message_locations = extract_measurement_locations(message)
    message_types = extract_message_types(message_locations)
    reference_types = extract_reference_types(args.reference_xml)
    rows = compare_types(message_types, reference_types)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        render_report(
            message_path=args.message_json,
            reference_path=args.reference_xml,
            total_locations=len(message_locations),
            message_types=message_types,
            reference_types=reference_types,
            rows=rows,
            addendum_path=args.addendum,
        ),
        encoding="utf-8",
    )

    missing = [row for row in rows if row.status == "MissingInReferenceData"]
    if missing:
        write_addendum(args.addendum, missing)

    print(f"Wrote {args.output}")
    if missing:
        print(f"Wrote {args.addendum}")
    print(
        "Summary: "
        f"{len(message_locations)} locations, "
        f"{len(message_types)} message types, "
        f"{len(reference_types)} reference types, "
        f"{sum(1 for row in rows if row.status == 'Matched')} matched, "
        f"{len(missing)} missing, "
        f"{sum(1 for row in rows if row.status == 'NameMismatch')} name mismatch"
    )


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def extract_measurement_locations(payload: Any) -> list[dict[str, Any]]:
    locations: list[dict[str, Any]] = []
    for group in measurement_location_groups(payload):
        for item in as_list(group.get("measurementLocation")):
            if isinstance(item, dict):
                locations.append(item)
    if locations:
        return locations
    return find_location_records(payload)


def measurement_location_groups(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        groups: list[dict[str, Any]] = []
        for item in value:
            groups.extend(measurement_location_groups(item))
        return groups
    if not isinstance(value, dict):
        return []
    if "measurementLocation" in value:
        return [value]
    for key in (
        "showMeasurementLocations",
        "dataArea",
        "measurementLocations",
        "payload",
        "data",
        "raw",
        "response",
    ):
        if key in value:
            groups = measurement_location_groups(value[key])
            if groups:
                return groups
    return []


def find_location_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        records: list[dict[str, Any]] = []
        for item in value:
            records.extend(find_location_records(item))
        return records
    if not isinstance(value, dict):
        return []
    if looks_like_measurement_location(value):
        return [value]
    records = []
    for item in value.values():
        records.extend(find_location_records(item))
    return records


def looks_like_measurement_location(value: dict[str, Any]) -> bool:
    keys = {key.casefold() for key in value}
    return "type" in keys and bool(keys & {"uuid", "shortnames", "shortname", "valueclass"})


def extract_message_types(locations: list[dict[str, Any]]) -> dict[str, MessageType]:
    counts: Counter[str] = Counter()
    names: dict[str, str] = {}
    examples: dict[str, str] = {}

    for location in locations:
        type_node = location.get("type") or location.get("Type") or {}
        if not isinstance(type_node, dict):
            continue
        raw_uuid = first_value(type_node, ("UUID", "uuid"))
        if not raw_uuid:
            continue
        uuid = normalize_uuid(raw_uuid)
        counts[uuid] += 1
        names.setdefault(
            uuid,
            text_value(type_node.get("shortNames"))
            or text_value(type_node.get("shortName"))
            or str(raw_uuid),
        )
        examples.setdefault(
            uuid,
            text_value(location.get("shortNames"))
            or text_value(location.get("shortName"))
            or str(first_value(location, ("UUID", "uuid")) or ""),
        )

    return {
        uuid: MessageType(
            uuid=uuid,
            name=names.get(uuid, ""),
            usage_count=count,
            example_location_name=examples.get(uuid, ""),
        )
        for uuid, count in counts.items()
    }


def extract_reference_types(reference_path: Path) -> dict[str, ReferenceType]:
    service = ReferenceDataService(str(reference_path), "CCOM Reference Data")
    service.load()
    if not service.is_loaded():
        raise RuntimeError(service.warning or "Reference data XML could not be loaded.")

    source = f"{reference_path.as_posix()} | xsi:type=MeasurementLocationType"
    reference_types: dict[str, ReferenceType] = {}
    for entry in service.get_entries_by_class("MeasurementLocationType"):
        uuid = normalize_uuid(entry.uuid)
        name = entry.display_name
        reference_types[uuid] = ReferenceType(uuid=uuid, name=name, source=source)
    return reference_types


def compare_types(
    message_types: dict[str, MessageType],
    reference_types: dict[str, ReferenceType],
) -> list[ComparisonRow]:
    rows: list[ComparisonRow] = []
    all_uuids = sorted(set(message_types) | set(reference_types))
    for uuid in all_uuids:
        message = message_types.get(uuid)
        reference = reference_types.get(uuid)
        if message and reference:
            status = "Matched" if names_match(message.name, reference.name) else "NameMismatch"
        elif message:
            status = "MissingInReferenceData"
        else:
            status = "ReferenceOnly"

        rows.append(
            ComparisonRow(
                status=status,
                uuid=uuid,
                message_name=message.name if message else "",
                reference_name=reference.name if reference else "",
                usage_count=message.usage_count if message else 0,
                example_location_name=message.example_location_name if message else "",
                source=reference.source if reference else "",
            )
        )
    return sorted(rows, key=lambda row: (status_sort_key(row.status), row.message_name.casefold(), row.reference_name.casefold(), row.uuid))


def render_report(
    message_path: Path,
    reference_path: Path,
    total_locations: int,
    message_types: dict[str, MessageType],
    reference_types: dict[str, ReferenceType],
    rows: list[ComparisonRow],
    addendum_path: Path,
) -> str:
    counts = Counter(row.status for row in rows)
    lines = [
        "# MeasurementLocationType reference-data comparison",
        "",
        "## Inputs",
        "",
        f"- ShowMeasurementLocations JSON: `{message_path.as_posix()}`",
        f"- CCOM Reference Data XML: `{reference_path.as_posix()}`",
        "- Entity type: `MeasurementLocationType`",
        "",
        "## Repository Findings",
        "",
        "- `MeasurementLocationType` reference data is stored in the canonical CCOM Reference Data XML file.",
        "- The portal loader reads XML `Entity` nodes and filters by `xsi:type = MeasurementLocationType`.",
        "- Message comparison is by `MeasurementLocation.type.UUID`; `MeasurementLocation.UUID` values are not counted as type UUIDs.",
        "",
        "## Summary",
        "",
        f"- Total MeasurementLocations in message: `{total_locations}`",
        f"- Total distinct MeasurementLocationTypes in message: `{len(message_types)}`",
        f"- Total MeasurementLocationTypes in PdMA Reference Data: `{len(reference_types)}`",
        f"- Count matched: `{counts['Matched']}`",
        f"- Count missing from reference data: `{counts['MissingInReferenceData']}`",
        f"- Count reference-only: `{counts['ReferenceOnly']}`",
        f"- Count name mismatch: `{counts['NameMismatch']}`",
        "",
    ]

    if counts["MissingInReferenceData"]:
        lines.extend(
            [
                "## Proposed Addendum",
                "",
                f"Missing message types were written to `{addendum_path.as_posix()}` for review.",
                "This file is a proposal only; the canonical XML reference data is not modified.",
                "",
            ]
        )

    lines.extend(
        [
            "## Details",
            "",
            "| Status | Type UUID | Type Name from CCOM Message | Type Name from Reference Data | Usage Count in Message | Example MeasurementLocation Name | Source file / table |",
            "| --- | --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    escape_md(row.status),
                    f"`{escape_md(row.uuid)}`",
                    escape_md(row.message_name),
                    escape_md(row.reference_name),
                    str(row.usage_count),
                    escape_md(row.example_location_name),
                    escape_md(row.source),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def write_addendum(path: Path, rows: list[ComparisonRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "Class",
                "UUID",
                "ShortName",
                "FullName",
                "UsageCountInMessage",
                "ExampleMeasurementLocationName",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "Class": "MeasurementLocationType",
                    "UUID": row.uuid,
                    "ShortName": row.message_name,
                    "FullName": "",
                    "UsageCountInMessage": row.usage_count,
                    "ExampleMeasurementLocationName": row.example_location_name,
                }
            )


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def first_value(record: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def text_value(value: Any) -> str | None:
    if isinstance(value, list) and value:
        return text_value(value[0])
    if isinstance(value, dict):
        for key in ("text", "Text", "value", "Value"):
            text = clean(value.get(key))
            if text:
                return text
    return clean(value)


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.casefold() == "nan":
        return None
    return text


def normalize_uuid(value: Any) -> str:
    return str(value).strip().lower()


def normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())


def names_match(left: str, right: str) -> bool:
    return normalize_name(left) == normalize_name(right)


def status_sort_key(status: str) -> int:
    return {
        "MissingInReferenceData": 0,
        "NameMismatch": 1,
        "Matched": 2,
        "ReferenceOnly": 3,
    }.get(status, 9)


def escape_md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    main()
