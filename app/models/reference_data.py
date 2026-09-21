from pydantic import BaseModel


class ReferenceDataEntry(BaseModel):
    class_name: str
    uuid: str
    short_name: str | None = None
    full_name: str | None = None
    description: str | None = None
    type: str | None = None
    uom_quantity: str | None = None
    reference_unit_of_measure: str | None = None
    conversion_scale: str | None = None
    conversion_offset: str | None = None
    created: str | None = None
    last_edited: str | None = None
    info_source_uuid: str | None = None
    effective_status_type_uuid: str | None = None

    @property
    def display_name(self) -> str:
        return self.short_name or self.full_name or self.uuid
