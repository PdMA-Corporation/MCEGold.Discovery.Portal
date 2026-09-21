# First-stage design

## Purpose and workflow

The first stage is a small customer-side reference portal for exploring the kinds of MCEGold objects used when planning Grafana dashboards. Discovery follows a deliberate top-down path: **Site → Segment → Measurement Location → Measurements**.

Starting at Site preserves operational context and prevents ambiguous results. Direct navigation to deeper explorer pages is intentionally avoided: users choose the parent object before seeing its children, and invalid parent-child URL combinations return a not-found response.

## Type filters

Each workflow level offers only filters relevant to that level. Sites can be filtered by site UUID, segments by segment type UUID, locations by location type UUID, and measurements by recorded time and result limits. Filters are represented in the query string, making a filtered view reproducible and easy to map to connector requests.

## CLI-backed discovery

The portal uses the MCEGold Connector CLI for discovery. A configured CLI path and connector configuration are required to retrieve customer data, and CLI errors are surfaced in the guided workflow without changing the selected context.

## Connector replacement boundary

`DiscoveryClient` defines source-neutral discovery operations with optional parent identifiers. The web routes use focused service classes, and those services depend only on this abstraction. The production implementation invokes the MCEGold Connector CLI and returns the same Pydantic models used by routes and templates.

## Asset and dashboard evolution

Asset is intentionally excluded from the first guided workflow. It can be added later at the Segment level once the desired relationship and selection behavior are settled. Preserving the selected path and exposing level-specific filters also creates the context a future Grafana dashboard generator will need to choose meaningful measurements.

## Planned features

- Object relationship explorer
- Grafana dashboard generator
- SQLite discovery cache
- AI-assisted measurement selection
