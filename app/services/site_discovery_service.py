from app.models import Site
from app.services.discovery_client import DiscoveryClient
from app.services.reference_data_service import entry_matches_value


class SiteDiscoveryService:
    def __init__(self, client: DiscoveryClient) -> None:
        self.client = client

    def get_sites(
        self,
        site_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        site_type_entries: list | None = None,
        discovery_session_id: str | None = None,
    ) -> list[Site]:
        sites = self.client.get_sites(discovery_session_id)
        if site_type:
            sites = [
                site for site in sites
                if entry_matches_value(site.site_type, site_type, site_type_entries or [])
            ]
        if status:
            sites = [site for site in sites if site.status.casefold() == status.casefold()]
        if search:
            sites = [site for site in sites if search.casefold() in site.site_name.casefold()]
        return sites

    def get_site(self, site_uuid: str, discovery_session_id: str | None = None) -> Site | None:
        return next(
            (
                site
                for site in self.client.get_sites(discovery_session_id)
                if site.site_uuid == site_uuid
            ),
            None,
        )
