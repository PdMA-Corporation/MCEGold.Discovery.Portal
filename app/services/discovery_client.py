from abc import ABC, abstractmethod

from app.models import Asset, Measurement, MeasurementLocation, Segment, Site


class DiscoveryClient(ABC):
    """Source-neutral interface for discovering MCEGold objects."""

    @abstractmethod
    def get_sites(self, session_id: str | None = None) -> list[Site]: ...

    @abstractmethod
    def get_assets(self) -> list[Asset]: ...

    @abstractmethod
    def get_segments(
        self,
        site_uuid: str | None = None,
        session_id: str | None = None,
        segment_type_uuid: str | None = None,
        max_items: int | None = None,
    ) -> list[Segment]: ...

    @abstractmethod
    def get_measurement_locations(
        self,
        segment_uuid: str | None = None,
        session_id: str | None = None,
        measurement_location_type_uuid: str | None = None,
        max_items: int | None = None,
    ) -> list[MeasurementLocation]: ...

    @abstractmethod
    def get_measurements(
        self,
        location_uuid: str | None = None,
        session_id: str | None = None,
        segment_uuid: str | None = None,
        recorded_from: str | None = None,
        recorded_to: str | None = None,
        max_items: int | None = None,
        fallback_unit: str | None = None,
    ) -> list[Measurement]: ...
