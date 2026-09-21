from pydantic import BaseModel


class Site(BaseModel):
    site_uuid: str
    site_name: str
    site_type: str
    site_type_uuid: str | None = None
    site_type_info_source_uuid: str | None = None
    site_type_info_source_short_name: str | None = None
    info_source_uuid: str | None = None
    info_source_short_name: str | None = None
    status: str
    region: str
    description: str
