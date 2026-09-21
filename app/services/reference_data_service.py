from __future__ import annotations

from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree

from app.core.config import settings
from app.models import ReferenceDataEntry


REFERENCE_CATEGORIES = (
    "segment_types",
    "measurement_location_types",
    "measurement_types",
    "units_of_measure",
)

CCOM_NAMESPACE = "http://www.mimosa.org/ccom4"
XSI_TYPE_ATTRIBUTE = "{http://www.w3.org/2001/XMLSchema-instance}type"


def _split_class_names(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.casefold() == "nan":
        return None
    return text


def _norm(value: str) -> str:
    return "".join(ch for ch in value.casefold() if ch.isalnum())


def _q(name: str) -> str:
    return f"{{{CCOM_NAMESPACE}}}{name}"


def _child_text(element: ElementTree.Element, name: str) -> str | None:
    child = element.find(_q(name))
    return _clean(child.text) if child is not None else None


def _child_scalar(element: ElementTree.Element, name: str) -> str | None:
    child = element.find(_q(name))
    if child is None:
        child = next((item for item in element if item.tag.split("}", 1)[-1].casefold() == name.casefold()), None)
    if child is None:
        return None
    direct = _clean(child.text)
    if direct:
        return direct
    for child_name in ("Numeric", "Value", "Text"):
        nested = child.find(_q(child_name))
        if nested is None:
            nested = next(
                (item for item in child if item.tag.split("}", 1)[-1].casefold() == child_name.casefold()),
                None,
            )
        value = _clean(nested.text) if nested is not None else None
        if value:
            return value
    return None


def _child_uuid(element: ElementTree.Element, name: str) -> str | None:
    child = element.find(_q(name))
    if child is None:
        return None
    return _child_text(child, "UUID")


def entry_matches_value(candidate: str | None, selected: str | None, entries: Iterable[ReferenceDataEntry]) -> bool:
    if not selected:
        return True
    if not candidate:
        return False

    candidate_norm = _norm(candidate)
    selected_norm = _norm(selected)
    if candidate_norm == selected_norm:
        return True

    for entry in entries:
        aliases = [
            entry.uuid,
            entry.display_name,
            entry.short_name,
            entry.full_name,
            entry.type,
            entry.uom_quantity,
            entry.reference_unit_of_measure,
        ]
        selected_matches_entry = any(_norm(alias) == selected_norm for alias in aliases if alias)
        candidate_matches_entry = any(_norm(alias) == candidate_norm for alias in aliases if alias)
        if selected_matches_entry and candidate_matches_entry:
            return True
    return False


class ReferenceDataService:
    def __init__(
        self,
        file_path: str,
        sheet_name: str,
        class_mapping: dict[str, list[str]] | None = None,
    ) -> None:
        self.file_path = Path(file_path)
        self.sheet_name = sheet_name
        self.class_mapping = class_mapping or {
            "segment_types": _split_class_names(settings.reference_class_segment_types),
            "measurement_location_types": _split_class_names(
                settings.reference_class_measurement_location_types
            ),
            "measurement_types": _split_class_names(settings.reference_class_measurement_types),
            "units_of_measure": _split_class_names(settings.reference_class_units_of_measure),
        }
        self._entries: dict[str, list[ReferenceDataEntry]] = {
            category: [] for category in REFERENCE_CATEGORIES
        }
        self._classes_loaded: dict[str, list[str]] = {
            category: [] for category in REFERENCE_CATEGORIES
        }
        self._all_entries: list[ReferenceDataEntry] = []
        self.status = "not_loaded"
        self.warning: str | None = None

    def load(self) -> None:
        self._entries = {category: [] for category in REFERENCE_CATEGORIES}
        self._classes_loaded = {category: [] for category in REFERENCE_CATEGORIES}
        self._all_entries = []
        self.warning = None

        if not self.file_path.exists():
            self.status = "missing"
            self.warning = f"Reference data file not found: {self.file_path}"
            return

        try:
            self._all_entries = self._load_xml_entries()
            class_values = sorted({entry.class_name for entry in self._all_entries})

            for category in REFERENCE_CATEGORIES:
                configured = self.class_mapping.get(category, [])
                classes = self._resolve_classes(category, configured, class_values)
                self._classes_loaded[category] = classes
                self._entries[category] = self._entries_for_classes(classes)

            self.status = "loaded"
            unresolved = [
                category for category in REFERENCE_CATEGORIES if not self._classes_loaded[category]
            ]
            if unresolved:
                self.warning = "Could not map reference classes for: " + ", ".join(unresolved)
        except Exception as exc:
            self.status = "failed"
            self.warning = f"Reference data load failed: {exc}"

    def is_loaded(self) -> bool:
        return self.status == "loaded"

    def get_segment_types(self) -> list[ReferenceDataEntry]:
        return self._entries["segment_types"]

    def get_measurement_location_types(self) -> list[ReferenceDataEntry]:
        return self._entries["measurement_location_types"]

    def get_measurement_types(self) -> list[ReferenceDataEntry]:
        return self._entries["measurement_types"]

    def get_units_of_measure(self) -> list[ReferenceDataEntry]:
        return self._entries["units_of_measure"]

    def get_entries_by_class(self, class_name: str) -> list[ReferenceDataEntry]:
        return self._entries_for_classes([class_name])

    def get_all_entries(self) -> list[ReferenceDataEntry]:
        return list(self._all_entries)

    def get_classes_loaded(self) -> list[str]:
        return sorted({class_name for names in self._classes_loaded.values() for class_name in names})

    def get_classes_loaded_by_category(self) -> dict[str, list[str]]:
        return self._classes_loaded

    def get_status(self) -> dict[str, object]:
        return {
            "status": self.status,
            "isLoaded": self.is_loaded(),
            "filePath": str(self.file_path),
            "sheetName": self.sheet_name,
            "warning": self.warning,
            "classesLoaded": self.get_classes_loaded_by_category(),
            "counts": {
                "segmentTypes": len(self.get_segment_types()),
                "measurementLocationTypes": len(self.get_measurement_location_types()),
                "measurementTypes": len(self.get_measurement_types()),
                "unitsOfMeasure": len(self.get_units_of_measure()),
            },
        }

    def _load_xml_entries(self) -> list[ReferenceDataEntry]:
        root = ElementTree.parse(self.file_path).getroot()
        entries: list[ReferenceDataEntry] = []
        for entity in root.findall(_q("Entity")):
            class_name = _clean(entity.attrib.get(XSI_TYPE_ATTRIBUTE))
            uuid = _child_text(entity, "UUID")
            if not uuid or not class_name:
                continue
            entries.append(
                ReferenceDataEntry(
                    class_name=class_name,
                    uuid=uuid,
                    short_name=_child_text(entity, "ShortName"),
                    full_name=_child_text(entity, "FullName"),
                    description=_child_text(entity, "Description"),
                    type=_child_uuid(entity, "Type") or _child_text(entity, "Type"),
                    uom_quantity=_child_uuid(entity, "UOMQuantity") or _child_text(entity, "UOMQuantity"),
                    reference_unit_of_measure=_child_uuid(entity, "ReferenceUnitOfMeasure")
                    or _child_text(entity, "ReferenceUnitOfMeasure"),
                    conversion_scale=_child_scalar(entity, "ConversionScale"),
                    conversion_offset=_child_scalar(entity, "ConversionOffset"),
                    created=_child_text(entity, "Created"),
                    last_edited=_child_text(entity, "LastEdited"),
                    info_source_uuid=_child_uuid(entity, "InfoSource"),
                    effective_status_type_uuid=_child_uuid(entity, "EffectiveStatusType"),
                )
            )
        return sorted(entries, key=lambda entry: (entry.class_name.casefold(), entry.display_name.casefold()))

    def _entries_for_classes(self, classes: list[str]) -> list[ReferenceDataEntry]:
        class_set = set(classes)
        entries = [entry for entry in self._all_entries if entry.class_name in class_set]
        return sorted(entries, key=lambda entry: entry.display_name.casefold())

    def _resolve_classes(
        self,
        category: str,
        configured: list[str],
        available_classes: list[str],
    ) -> list[str]:
        exact = [class_name for class_name in configured if class_name in available_classes]
        if exact:
            return exact

        return [
            class_name
            for class_name in available_classes
            if self._class_matches_category(class_name, category)
        ]

    def _class_matches_category(self, class_name: str, category: str) -> bool:
        normalized = _norm(class_name)
        if category == "segment_types":
            return "segment" in normalized and "type" in normalized
        if category == "measurement_location_types":
            return "measurementlocation" in normalized and "type" in normalized
        if category == "measurement_types":
            return (
                "measurement" in normalized
                and "type" in normalized
                and "measurementlocation" not in normalized
            )
        if category == "units_of_measure":
            return "unit" in normalized or normalized in {"uom", "uomquantity"}
        return False
