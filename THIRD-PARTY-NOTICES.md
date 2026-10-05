# Third-Party Notices

Unless otherwise noted, MCEGold Discovery Portal source code is licensed under the MIT License in `LICENSE`.

Third-party materials included with or referenced by this project remain subject to their respective licenses and notices. They are not relicensed by the Portal MIT License.

## MIMOSA CCOM Reference Data

This project uses MIMOSA CCOM reference data to demonstrate standards-based interoperability with MCEGold Data Services workflows.

The reference data file is:

```text
docs/CCOM Reference Data.xml
```

MIMOSA CCOM materials remain owned or licensed by MIMOSA and/or its licensors and are subject to the applicable MIMOSA License Agreement. The CCOM reference data is not licensed under the MCEGold Discovery Portal MIT License.

Preserve existing MIMOSA copyright, proprietary, and license notices when redistributing this material with the Portal source or with a future MCEGold Discovery runtime image.

## MCEGold Data Services Connector

The MCEGold Data Services Connector CLI/tooling layer may be open source for users to inspect, modify, and adapt for integration workflows.

The `MCEGold.Data.Services.Connector` runtime/library used by the CLI remains proprietary. Including its binary/runtime dependency in an official self-contained CLI package or an official MCEGold Discovery runtime image does not make the proprietary Connector source code open source.

Applicable proprietary notices for the `MCEGold.Data.Services.Connector` runtime/library remain in force.

## Grafana

The single-image appliance includes Grafana OSS for local dashboard viewing. Grafana OSS is distributed by Grafana Labs under its own license terms and is not relicensed by the MCEGold Discovery Portal MIT License.

## Grafana SQLite Datasource Plugin

The single-image appliance includes the `frser-sqlite-datasource` plugin version `4.0.6` so Grafana can query the shared SQLite database at `/data/discovery_portal.db`. The plugin remains subject to its own upstream license and notices.
