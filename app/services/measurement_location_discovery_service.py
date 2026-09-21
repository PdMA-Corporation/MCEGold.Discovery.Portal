from app.models import MeasurementLocation
from app.services.discovery_client import DiscoveryClient
from app.services.reference_data_service import entry_matches_value


class MeasurementLocationDiscoveryService:
    def __init__(self, client: DiscoveryClient) -> None:
        self.client = client

    def get_measurement_locations(
        self,
        segment_uuid: str | None = None,
        location_type: str | None = None,
        location_type_entries: list | None = None,
        discovery_session_id: str | None = None,
        measurement_location_type_uuid: str | None = None,
        max_items: int | None = None,
    ) -> list[MeasurementLocation]:
        server_type_uuid = measurement_location_type_uuid
        client_kwargs = {
            "session_id": discovery_session_id,
            "measurement_location_type_uuid": server_type_uuid,
        }
        if max_items is not None:
            client_kwargs["max_items"] = max_items
        locations = self.client.get_measurement_locations(segment_uuid, **client_kwargs)
        if location_type and not measurement_location_type_uuid:
            locations = [
                item for item in locations
                if item.type_uuid == location_type
                or entry_matches_value(item.location_type, location_type, location_type_entries or [])
            ]
        return locations

    def get_location(
        self,
        location_uuid: str,
        segment_uuid: str | None = None,
        discovery_session_id: str | None = None,
    ) -> MeasurementLocation | None:
        return next(
            (
                item
                for item in self.client.get_measurement_locations(
                    segment_uuid,
                    session_id=discovery_session_id,
                )
                if item.location_uuid == location_uuid
            ),
            None,
        )
