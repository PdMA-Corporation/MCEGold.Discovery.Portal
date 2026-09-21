from datetime import datetime, timezone

from app.models import Measurement, MeasurementLocation, Segment, Site


def test_site_creation() -> None:
    site = Site(site_uuid="site-1", site_name="Tampa Plant", site_type="Plant", status="Active", region="Southeast", description="Test site")
    assert site.site_type == "Plant"


def test_segment_creation() -> None:
    segment = Segment(segment_uuid="segment-1", site_uuid="site-1", segment_name="Pump Train", segment_type="Pump Train", status="Active", description="Test segment")
    assert segment.site_uuid == "site-1"


def test_measurement_location_creation() -> None:
    location = MeasurementLocation(location_uuid="location-1", segment_uuid="segment-1", location_name="Motor DE", location_type="Bearing", type_uuid="type-1", status="Active", description="Drive end")
    assert location.location_type == "Bearing"


def test_measurement_creation() -> None:
    measurement = Measurement(measurement_uuid="measurement-1", location_uuid="location-1", measurement_name="Velocity", measurement_type="Vibration", value=1.2, unit="mm/s", timestamp_utc=datetime.now(timezone.utc), status="Normal")
    assert measurement.measurement_type == "Vibration"
