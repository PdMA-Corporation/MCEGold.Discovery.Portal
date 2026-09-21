# Measurement Location reference-data study

Source payload: `ShowMeasurementLocations`, created `2026-06-23T20:10:38Z`, release `9.0`, version `1.0`.

## Payload summary

- Segment UUID: `f94e96ac-7567-4e0b-9da6-f47e735769d5`
- Segment name: `Segment Test`
- `show.recordSetCount`: `46`
- measurement location group `count`: `46`
- parsed measurement locations: `46`
- unique Measurement Location Types: `25`

Value classes:

- `Measure`: `29`
- `Percentage`: `15`
- `Number`: `2`

Default units observed on `Measure` rows:

- `Amperes`
- `Decibel`
- `Foot-Pounds`
- `Horsepower`
- `Kilovars`
- `Kilovolt-amperes`
- `Kilowatts`
- `Revolutions Per Minute (RPM)`
- `Seconds`
- `Volts`

## Shape confirmed

The payload uses the expected CCOM response path:

```text
showMeasurementLocations.dataArea.measurementLocations[].measurementLocation[]
```

Each group can carry parent segment context:

```text
showMeasurementLocations.dataArea.measurementLocations[].segment.UUID
showMeasurementLocations.dataArea.measurementLocations[].segment.shortNames[0].text
```

Each measurement location carries:

```text
UUID
shortNames[0].text
type.UUID
type.shortNames[0].text
valueClass
UOMQuantity.UUID
UOMQuantity.shortNames[0].text
defaultUnitOfMeasure.UUID
defaultUnitOfMeasure.shortNames[0].text
```

`Percentage` and `Number` rows often do not include `UOMQuantity` or `defaultUnitOfMeasure`, so the portal should continue using display fallbacks for those value classes.

## Naming pattern

Most entries appear as functional pairs:

- `{metric}, Stator`
- `{metric}, Drive Input Stator`

Examples:

- `% Current Imbalance, Stator`
- `% Current Imbalance, Drive Input Stator`
- `Average Current, Stator`
- `Average Current, Drive Input Stator`
- `Total kW, Stator`
- `Total kW, Drive Input Stator`

The pair pattern suggests the location name should remain the primary display label. The type name is the correct filter facet, but not specific enough to identify a row by itself because many pairs share the same type UUID.

## Reference-data implications

The Measurement Location Type dropdown should use `MeasurementLocationType.UUID` as the option value and display `MeasurementLocationType.shortNames[0].text`.

The response confirms that the request filter should stay UUID-based:

```json
{
  "filters": {
    "segmentUuid": "{selected_segment_uuid}",
    "typeUuid": "{selected_measurement_location_type_uuid}"
  }
}
```

Local filters still make sense for:

- `valueClass`
- text search over `shortNames[0].text`

The portal should not depend on status or description for this object, because neither appears in the observed payload.

## Parser checks

The current parser behavior matches this study payload:

- Reads the parent `segment.UUID` for `segment_uuid`.
- Reads `shortNames[0].text` for the measurement location display name.
- Reads `type.UUID` and `type.shortNames[0].text`.
- Reads `valueClass`.
- Reads `defaultUnitOfMeasure` when present.
- Reads `UOMQuantity` when present.
- Falls back to `%` for `Percentage` rows without a unit.
- Falls back to a placeholder for `Number` rows without a unit.

The important regression anchor from this payload is count and diversity: a real Segment can return at least `46` locations across `25` types, with a mix of `Measure`, `Percentage`, and `Number` value classes.
