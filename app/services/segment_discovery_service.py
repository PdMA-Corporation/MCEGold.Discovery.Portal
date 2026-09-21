from app.models import Segment
from app.services.discovery_client import DiscoveryClient
from app.services.reference_data_service import entry_matches_value


class SegmentDiscoveryService:
    def __init__(self, client: DiscoveryClient) -> None:
        self.client = client

    def get_segments(
        self,
        site_uuid: str | None = None,
        segment_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        segment_type_entries: list | None = None,
        discovery_session_id: str | None = None,
        segment_type_uuid: str | None = None,
        max_items: int | None = None,
    ) -> list[Segment]:
        client_kwargs = {
            "session_id": discovery_session_id,
            "segment_type_uuid": segment_type_uuid,
        }
        if max_items is not None:
            client_kwargs["max_items"] = max_items
        segments = self.client.get_segments(site_uuid, **client_kwargs)
        if segment_type_uuid:
            segments = [
                item for item in segments
                if item.segment_type_uuid == segment_type_uuid
                or entry_matches_value(item.segment_type, segment_type_uuid, segment_type_entries or [])
            ]
        elif segment_type:
            segments = [
                item for item in segments
                if entry_matches_value(item.segment_type, segment_type, segment_type_entries or [])
            ]
        if status:
            segments = [item for item in segments if item.status.casefold() == status.casefold()]
        if search:
            segments = [item for item in segments if search.casefold() in item.segment_name.casefold()]
        return segments

    def get_segment(self, segment_uuid: str) -> Segment | None:
        return next(
            (item for item in self.client.get_segments() if item.segment_uuid == segment_uuid),
            None,
        )
