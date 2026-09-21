from pydantic import BaseModel


class Segment(BaseModel):
    segment_uuid: str
    site_uuid: str
    segment_name: str
    segment_type: str
    segment_type_uuid: str | None = None
    segment_type_info_source_uuid: str | None = None
    segment_type_info_source_short_name: str | None = None
    info_source_uuid: str | None = None
    info_source_short_name: str | None = None
    status: str
    description: str
