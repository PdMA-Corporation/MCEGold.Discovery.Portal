import json
from pathlib import Path


def test_discovery_filter_manifest_shape() -> None:
    manifest_path = Path(__file__).parents[1] / "docs" / "discovery-filter-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    request_types = manifest["requestTypes"]
    assert {item["name"] for item in request_types} == {
        "GetSites",
        "GetSegments",
        "GetAssets",
        "GetMeasurementLocations",
        "GetMeasurements",
        "GetAssessments",
        "GetAssetSegmentEvents",
    }
    assert all(item["supportedInCli"] for item in request_types)
    assert all(item["fields"][0]["jsonPath"] == "requestType" for item in request_types)
    assert all(item["fields"][0]["required"] for item in request_types)

    local_only = [
        field
        for level in manifest["portalWorkflow"]
        for field in level["localOnlyFilters"]
    ]
    assert local_only
    assert all(field["portalLocalOnly"] is True for field in local_only)
    assert "mockOnlyFilters" not in {
        key for level in manifest["portalWorkflow"] for key in level
    }

