from app.services.measurement_discovery_service import MeasurementDiscoveryService
from app.services.measurement_location_discovery_service import MeasurementLocationDiscoveryService
from tests.fake_discovery_client import MOTOR_DE, PUMP_TRAIN, TAMPA, MockDiscoveryClient
from app.services.segment_discovery_service import SegmentDiscoveryService
from app.services.site_discovery_service import SiteDiscoveryService


def test_mock_client_returns_related_data() -> None:
    client = MockDiscoveryClient()
    assert client.get_sites()
    assert client.get_segments(TAMPA)
    assert all(item.site_uuid == TAMPA for item in client.get_segments(TAMPA))
    assert client.get_measurement_locations(PUMP_TRAIN)
    assert all(item.segment_uuid == PUMP_TRAIN for item in client.get_measurement_locations(PUMP_TRAIN))
    assert client.get_measurements(MOTOR_DE)
    assert all(item.location_uuid == MOTOR_DE for item in client.get_measurements(MOTOR_DE))


def test_services_return_non_empty_lists() -> None:
    client = MockDiscoveryClient()
    assert SiteDiscoveryService(client).get_sites()
    assert SegmentDiscoveryService(client).get_segments(TAMPA)
    assert MeasurementLocationDiscoveryService(client).get_measurement_locations(PUMP_TRAIN)
    assert MeasurementDiscoveryService(client).get_measurements(MOTOR_DE)


def test_site_type_filter() -> None:
    results = SiteDiscoveryService(MockDiscoveryClient()).get_sites(site_type="Plant")
    assert results and all(item.site_type == "Plant" for item in results)


def test_segment_type_filter() -> None:
    results = SegmentDiscoveryService(MockDiscoveryClient()).get_segments(TAMPA, segment_type="Pump Train")
    assert results and all(item.segment_type == "Pump Train" for item in results)


def test_location_type_filter() -> None:
    results = MeasurementLocationDiscoveryService(MockDiscoveryClient()).get_measurement_locations(PUMP_TRAIN, location_type="Bearing")
    assert results and all(item.location_type == "Bearing" for item in results)


def test_measurement_type_filter() -> None:
    results = MeasurementDiscoveryService(MockDiscoveryClient()).get_measurements(MOTOR_DE, measurement_type="Vibration")
    assert results and all(item.measurement_type == "Vibration" for item in results)

