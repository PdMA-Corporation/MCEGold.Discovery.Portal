from pydantic import BaseModel


class MeasurementLocation(BaseModel):
    location_uuid: str
    segment_uuid: str
    location_name: str
    location_type: str
    type_uuid: str = ""
    value_class: str = ""
    unit: str = ""
    unit_uuid: str | None = None
    reference_unit_uuid: str | None = None
    conversion_scale: float | None = None
    conversion_offset: float | None = None
    uom_quantity: str = ""
    uom_quantity_uuid: str | None = None
    info_source_uuid: str | None = None
    info_source_short_name: str | None = None
    measurement_location_type_info_source_uuid: str | None = None
    measurement_location_type_info_source_short_name: str | None = None
    unit_info_source_uuid: str | None = None
    unit_info_source_short_name: str | None = None
    uom_quantity_info_source_uuid: str | None = None
    uom_quantity_info_source_short_name: str | None = None
    status: str = "Unknown"
    description: str = ""
