from datetime import datetime
from pydantic import BaseModel


class Measurement(BaseModel):
    measurement_uuid: str
    location_uuid: str
    measurement_name: str
    measurement_type: str
    value: float
    unit: str
    unit_uuid: str | None = None
    timestamp_utc: datetime
    status: str
    info_source_uuid: str | None = None
    info_source_short_name: str | None = None
    unit_info_source_uuid: str | None = None
    unit_info_source_short_name: str | None = None
