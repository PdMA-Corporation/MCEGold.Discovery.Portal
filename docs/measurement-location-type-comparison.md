# MeasurementLocationType comparison workflow

Use this workflow to compare a local `ShowMeasurementLocations` CCOM response against the canonical CCOM Reference Data XML file.

## Reference data location

Measurement Location Type reference records are stored in:

```text
docs/CCOM Reference Data.xml
```

`Entity` nodes with `xsi:type = MeasurementLocationType` are the reference records used for this comparison. The comparison uses `UUID` first and uses `ShortName` or `FullName` only for display and name-mismatch detection.

## Sample message location

By default, the script reads a local ShowMeasurementLocations JSON response from:

```text
data/show-measurement-locations.json
```

This captured message is not checked in with the repository. Use `--message-json` to point the script at a local capture when the default file is absent.

The JSON can be either the raw CCOM message:

```text
showMeasurementLocations.dataArea.measurementLocations[].measurementLocation[]
```

or an envelope containing the message under `data`, `raw`, `payload`, or `response`.

Do not store credentials or live connector configuration in the sample JSON. The comparison is local-file only and does not make ISBM calls.

## Run

From the `MCEGold.Discovery.Portal` directory:

```powershell
.\.venv\Scripts\python.exe scripts\compare_measurement_location_types.py
```

To use a different message file:

```powershell
.\.venv\Scripts\python.exe scripts\compare_measurement_location_types.py --message-json path\to\show-measurement-locations.json
```

The default output is:

```text
docs/measurement-location-type-reference-comparison.md
```

If the message contains type UUIDs that are missing from the XML reference data, the script also writes a proposed addendum:

```text
docs/measurement-location-type-reference-addendum.csv
```

The addendum is review-only. The script does not modify `docs/CCOM Reference Data.xml`.

## Status meanings

- `Matched`: the type UUID exists in both the message and the XML reference data, and the display names match after whitespace/case normalization.
- `MissingInReferenceData`: the type UUID exists in the message but does not exist in the XML reference data.
- `ReferenceOnly`: the type UUID exists in the XML reference data but is not used by this message.
- `NameMismatch`: the type UUID exists in both, but the CCOM message name differs from the XML reference display name.

Always evaluate missing records by `MeasurementLocation.type.UUID`. Do not compare or count `MeasurementLocation.UUID` values as type UUIDs.
