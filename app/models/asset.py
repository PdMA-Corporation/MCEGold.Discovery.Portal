from uuid import UUID

from pydantic import BaseModel


class Asset(BaseModel):
    name: str
    uuid: UUID
    site_uuid: UUID
    asset_type: str
