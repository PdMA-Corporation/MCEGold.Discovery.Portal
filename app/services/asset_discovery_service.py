from app.models import Asset
from app.services.discovery_client import DiscoveryClient


class AssetDiscoveryService:
    def __init__(self, client: DiscoveryClient) -> None:
        self.client = client

    def get_assets(self) -> list[Asset]:
        return self.client.get_assets()
