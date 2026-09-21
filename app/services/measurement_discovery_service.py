from app.models import Measurement
from app.services.discovery_client import DiscoveryClient
from app.services.reference_data_service import entry_matches_value


class MeasurementDiscoveryService:
    def __init__(self, client: DiscoveryClient) -> None:
        self.client = client

    def get_measurements(
        self,
        location_uuid: str | None = None,
        measurement_type: str | None = None,
        unit: str | None = None,
        status: str | None = None,
        search: str | None = None,
        measurement_type_entries: list | None = None,
        unit_entries: list | None = None,
        discovery_session_id: str | None = None,
        segment_uuid: str | None = None,
        recorded_from: str | None = None,
        recorded_to: str | None = None,
        max_items: int | None = None,
        fallback_unit: str | None = None,
    ) -> list[Measurement]:
        measurements = self.client.get_measurements(
            location_uuid,
            session_id=discovery_session_id,
            segment_uuid=segment_uuid,
            recorded_from=recorded_from,
            recorded_to=recorded_to,
            max_items=max_items,
            fallback_unit=fallback_unit,
        )
        if measurement_type:
            measurements = [
                item for item in measurements
                if entry_matches_value(item.measurement_type, measurement_type, measurement_type_entries or [])
            ]
        if unit:
            measurements = [
                item for item in measurements
                if entry_matches_value(item.unit, unit, unit_entries or [])
            ]
        if status:
            measurements = [item for item in measurements if item.status.casefold() == status.casefold()]
        if search:
            measurements = [item for item in measurements if search.casefold() in item.measurement_name.casefold()]
        return measurements
