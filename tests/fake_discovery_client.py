from datetime import datetime, timezone

from app.models import Asset, Measurement, MeasurementLocation, Segment, Site
from app.services.discovery_client import DiscoveryClient

TAMPA = "11111111-1111-4111-8111-111111111111"
WEST_TEXAS = "22222222-2222-4222-8222-222222222222"
PHOENIX = "33333333-3333-4333-8333-333333333333"

PUMP_TRAIN = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1"
COMPRESSOR = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2"
COOLING_TOWER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa3"
WIND_TURBINE = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa4"
SOLAR_INVERTER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa5"

MOTOR_DE = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1"
PUMP_NDE = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2"
COMPRESSOR_DE = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb3"
TOWER_OUTLET = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb4"
TURBINE_MAIN = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb5"
INVERTER_CABINET = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb6"


class MockDiscoveryClient(DiscoveryClient):
    """Deterministic, related sample objects for guided discovery."""

    def get_sites(self, session_id: str | None = None) -> list[Site]:
        return [
            Site(site_uuid=TAMPA, site_name="Tampa Plant", site_type="Plant", status="Active", region="Southeast", description="Primary production facility"),
            Site(site_uuid=WEST_TEXAS, site_name="West Texas Renewable Farm", site_type="Renewable Farm", status="Active", region="Southwest", description="Wind generation facility"),
            Site(site_uuid=PHOENIX, site_name="Phoenix Solar Campus", site_type="Solar Campus", status="Maintenance", region="Southwest", description="Utility-scale solar installation"),
        ]

    def get_assets(self) -> list[Asset]:
        return []

    def get_segments(
        self,
        site_uuid: str | None = None,
        session_id: str | None = None,
        segment_type_uuid: str | None = None,
        max_items: int | None = None,
    ) -> list[Segment]:
        segments = [
            Segment(segment_uuid=PUMP_TRAIN, site_uuid=TAMPA, segment_name="Pump Train P-101", segment_type="Pump Train", status="Active", description="Primary process-water pump train"),
            Segment(segment_uuid=COMPRESSOR, site_uuid=TAMPA, segment_name="Compressor C-200", segment_type="Compressor", status="Active", description="Main plant air compressor"),
            Segment(segment_uuid=COOLING_TOWER, site_uuid=TAMPA, segment_name="Cooling Tower CT-2", segment_type="Cooling Tower", status="Maintenance", description="Secondary cooling tower"),
            Segment(segment_uuid=WIND_TURBINE, site_uuid=WEST_TEXAS, segment_name="Wind Turbine WT-12", segment_type="Wind Turbine", status="Active", description="Two-megawatt wind turbine"),
            Segment(segment_uuid=SOLAR_INVERTER, site_uuid=PHOENIX, segment_name="Solar Inverter INV-4", segment_type="Solar Inverter", status="Active", description="Block four power inverter"),
        ]
        results = [item for item in segments if site_uuid is None or item.site_uuid == site_uuid]
        if max_items is not None:
            results = results[:max_items]
        return results

    def get_measurement_locations(
        self,
        segment_uuid: str | None = None,
        session_id: str | None = None,
        measurement_location_type_uuid: str | None = None,
        max_items: int | None = None,
    ) -> list[MeasurementLocation]:
        locations = [
            MeasurementLocation(location_uuid=MOTOR_DE, segment_uuid=PUMP_TRAIN, location_name="Motor DE", location_type="Bearing", type_uuid="type-bearing-vibration", value_class="Measure", unit="mm/s", status="Active", description="Motor drive-end bearing"),
            MeasurementLocation(location_uuid=PUMP_NDE, segment_uuid=PUMP_TRAIN, location_name="Pump NDE", location_type="Bearing", type_uuid="type-bearing-vibration", value_class="Measure", unit="mm/s", status="Active", description="Pump non-drive-end bearing"),
            MeasurementLocation(location_uuid=COMPRESSOR_DE, segment_uuid=COMPRESSOR, location_name="Compressor Drive End", location_type="Bearing", type_uuid="type-bearing-temperature", value_class="Measure", unit="°C", status="Active", description="Compressor drive-end bearing"),
            MeasurementLocation(location_uuid=TOWER_OUTLET, segment_uuid=COOLING_TOWER, location_name="Tower Outlet", location_type="Process", type_uuid="type-process-temperature", value_class="Measure", unit="°C", status="Maintenance", description="Cooling-water outlet"),
            MeasurementLocation(location_uuid=TURBINE_MAIN, segment_uuid=WIND_TURBINE, location_name="Main Bearing", location_type="Bearing", type_uuid="type-bearing-vibration", value_class="Measure", unit="mm/s", status="Active", description="Turbine main bearing"),
            MeasurementLocation(location_uuid=INVERTER_CABINET, segment_uuid=SOLAR_INVERTER, location_name="Inverter Cabinet", location_type="Electrical", type_uuid="type-electrical-power", value_class="Number", unit="—", status="Active", description="Inverter output cabinet"),
        ]
        results = [
            item
            for item in locations
            if (segment_uuid is None or item.segment_uuid == segment_uuid)
            and (not measurement_location_type_uuid or item.type_uuid == measurement_location_type_uuid)
        ]
        if max_items is not None:
            results = results[:max_items]
        return results

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
        timestamp = datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc)
        measurements = [
            Measurement(measurement_uuid="m-001", location_uuid=MOTOR_DE, measurement_name="Overall Velocity", measurement_type="Vibration", value=2.41, unit="mm/s", timestamp_utc=timestamp, status="Normal"),
            Measurement(measurement_uuid="m-002", location_uuid=MOTOR_DE, measurement_name="Bearing Temperature", measurement_type="Temperature", value=63.7, unit="°C", timestamp_utc=timestamp, status="Normal"),
            Measurement(measurement_uuid="m-003", location_uuid=PUMP_NDE, measurement_name="Axial Velocity", measurement_type="Vibration", value=3.12, unit="mm/s", timestamp_utc=timestamp, status="Warning"),
            Measurement(measurement_uuid="m-004", location_uuid=COMPRESSOR_DE, measurement_name="Drive End Temperature", measurement_type="Temperature", value=71.2, unit="°C", timestamp_utc=timestamp, status="Normal"),
            Measurement(measurement_uuid="m-005", location_uuid=TOWER_OUTLET, measurement_name="Outlet Temperature", measurement_type="Temperature", value=29.4, unit="°C", timestamp_utc=timestamp, status="Normal"),
            Measurement(measurement_uuid="m-006", location_uuid=TURBINE_MAIN, measurement_name="Main Bearing Velocity", measurement_type="Vibration", value=4.05, unit="mm/s", timestamp_utc=timestamp, status="Warning"),
            Measurement(measurement_uuid="m-007", location_uuid=INVERTER_CABINET, measurement_name="Active Power", measurement_type="Power", value=487.0, unit="kW", timestamp_utc=timestamp, status="Normal"),
        ]
        results = [item for item in measurements if location_uuid is None or item.location_uuid == location_uuid]
        if recorded_from:
            from_dt = datetime.fromisoformat(recorded_from.replace("Z", "+00:00"))
            results = [item for item in results if item.timestamp_utc >= from_dt]
        if recorded_to:
            to_dt = datetime.fromisoformat(recorded_to.replace("Z", "+00:00"))
            results = [item for item in results if item.timestamp_utc <= to_dt]
        if max_items is not None:
            results = results[:max_items]
        return results

