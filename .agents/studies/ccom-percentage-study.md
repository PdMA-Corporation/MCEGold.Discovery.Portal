# CCOM Percentage Study

## Executive Summary

This read-only review examined a local copy of the CCOM 4.1.0 draft JSON schema files used during internal research.

No normative definition was found that explicitly states whether a generic CCOM `Percentage` value must be exchanged as `72.4` or `0.724`.

The schema defines `Percentage` as its own core type and as a distinct `ValueClass`, separate from `Measure` and `Number`. The `Percentage` core type is based on `NumericType` and does not carry a `UnitOfMeasure`. Unit conversion metadata (`conversionScale`, `conversionOffset`, `referenceUnitOfMeasure`) is defined for `UnitOfMeasure` and `UOMQuantity`, not for `Percentage`.

One property, `Measurement.confidence`, references `Percentage` and documents a 0-to-100 confidence scale. That is a property-specific statement, not a general representation rule for every CCOM percentage.

For the MCEGold Discovery Portal demo, percentage values should be treated as numeric values with no unit conversion. The Portal should not silently rescale `0.724` to `72.4`, or the reverse, unless a specific data source contract or property-specific rule explicitly requires it.

## Files Examined

- `CCOM.json`
- `CoreComponentType_2p0.json`

These are the only JSON schema files present in the specified schema directory.

Search terms reviewed:

- `Percentage`
- `Percent`
- `valueClass`
- `Measure`
- `Number`
- `UnitOfMeasure`
- `UOMQuantity`
- `referenceUnitOfMeasure`
- `defaultUnitOfMeasure`
- `conversionScale`
- `conversionOffset`

Term counts:

| Term | Matches |
| --- | ---: |
| `Percentage` | 15 |
| `Percent` | 15 |
| `valueClass` | 6 |
| `Measure` | 340 |
| `Number` | 24 |
| `UnitOfMeasure` | 18 |
| `UOMQuantity` | 13 |
| `referenceUnitOfMeasure` | 1 |
| `defaultUnitOfMeasure` | 1 |
| `conversionScale` | 4 |
| `conversionOffset` | 4 |

## Findings

### ValueClass

`CCOM.json#/definitions/02-CoreTypes/definitions/ValueClass` defines `ValueClass` as a string enum.

Relevant enum values include:

- `Measure`
- `Number`
- `Percentage`
- `Probability`

Finding: `Percentage` is explicitly represented as a separate value class. It is not only a `Measure`, and it is not only a `Number`.

### Percentage

`CCOM.json#/definitions/02-CoreTypes/definitions/Percentage` defines `Percentage` as a core type with:

- `id`: `Percentage`
- `allOf`: `CoreComponentType_2p0.json#/definitions/NumericType`

The definition does not include:

- `unitOfMeasure`
- `uomQuantity`
- `referenceUnitOfMeasure`
- `defaultUnitOfMeasure`
- `conversionScale`
- `conversionOffset`
- a minimum or maximum value
- examples showing `72.4` versus `0.724`

Finding: the schema says `Percentage` is numeric, but does not give a general storage/exchange scale rule.

### Number

`CoreComponentType_2p0.json#/definitions/NumericType` defines the underlying numeric type used by `Percentage`.

Relevant structure:

- `numeric`: string or number
- `@format`: enum values `integer`, `decimal`, `real`, `percentage`

Finding: `NumericType` can be marked with format `percentage`, but it does not define a percent scaling convention.

### Measure

`CCOM.json#/definitions/02-CoreTypes/definitions/Measure` defines `Measure` as an object with:

- `value`: `CoreComponentType_2p0.json#/definitions/NumericType`
- `unitOfMeasure`: `CCOM.json#/definitions/03-Core/definitions/UnitOfMeasure`

`CoreComponentType_2p0.json#/definitions/MeasureType` also defines measure-like data with a numeric value and a unit code.

Finding: `Measure` has unit semantics. `Percentage` does not share the `Measure` object structure and does not include `unitOfMeasure`.

### Unit of Measure

`CCOM.json#/definitions/03-Core/definitions/UnitOfMeasure` defines:

- `conversionScale`
- `conversionOffset`
- `uomQuantity`

Finding: unit conversion metadata belongs to `UnitOfMeasure`. The `Percentage` definition does not reference `UnitOfMeasure`.

### Reference Unit

`CCOM.json#/definitions/03-Core/definitions/UOMQuantity/properties/referenceUnitOfMeasure` references `UnitOfMeasure`.

Finding: reference units are modeled through `UOMQuantity`, not through `Percentage`.

### Default Unit

`defaultUnitOfMeasure` appears once:

`CCOM.json#/definitions/09-MeasurementLocations/definitions/MeasurementLocation/properties/defaultUnitOfMeasure`

It references `UnitOfMeasure`.

Finding: `defaultUnitOfMeasure` is a `MeasurementLocation` property. It is not part of the `Percentage` type.

### Conversion Scale

`conversionScale` appears under:

`CCOM.json#/definitions/03-Core/definitions/UnitOfMeasure/properties/conversionScale`

It references `NumericType`.

Finding: `conversionScale` is unit conversion metadata for `UnitOfMeasure`; no percentage-specific conversion rule was found.

### Conversion Offset

`conversionOffset` appears under:

`CCOM.json#/definitions/03-Core/definitions/UnitOfMeasure/properties/conversionOffset`

It references `NumericType`.

Finding: `conversionOffset` is unit conversion metadata for `UnitOfMeasure`; no percentage-specific offset rule was found.

## Normative Statements

Short excerpts from the schema:

- `CCOM.json`, line 77: "as a fraction of 100"
- `CoreComponentType_2p0.json`, line 424: "does not require a unit"

Relevant schema locations:

- `CCOM.json:75-79`: `Percentage`
- `CCOM.json:54-62`: `Measure`
- `CCOM.json:128-184`: `ValueContent`
- `CCOM.json:251-269`: `ValueClass`
- `CCOM.json:640-653`: `UnitOfMeasure`
- `CCOM.json:663-667`: `UOMQuantity.referenceUnitOfMeasure`
- `CCOM.json:2100-2102`: `MeasurementLocation.defaultUnitOfMeasure`
- `CCOM.json:2647-2649`: `Measurement.confidence`
- `CoreComponentType_2p0.json:421-450`: `NumericType`
- `CoreComponentType_2p0.json:383-418`: `MeasureType`

## Examples Found

No standalone JSON example payloads were found in the specified schema directory.

Schema examples or example-like references found:

| File | Schema/entity | JSON path | Example value |
| --- | --- | --- | --- |
| `CoreComponentType_2p0.json` | `NumericType` | `#/definitions/NumericType/properties/@format/enum/3` | `percentage` |
| `CCOM.json` | `Measurement.confidence` | `#/definitions/18-Measurements/definitions/Measurement/properties/confidence/description` | `0` and `100` as described bounds |
| `CCOM.json` | `CPBMeasurement` | `#/definitions/18-Measurements/definitions/CPBMeasurement/description` | Uses the phrase `Constant Percentage Band`, not a percentage value |
| `CCOM.json` | `HealthAssessment.confidence` | `#/definitions/25-HealthAndPrognosticAssessments/definitions/HealthAssessment/properties/confidence` | References `Percentage`; no numeric example |
| `CCOM.json` | `RemainingLifeAssessment.confidence` | `#/definitions/25-HealthAndPrognosticAssessments/definitions/RemainingLifeAssessment/properties/confidence` | References `Percentage`; no numeric example |

No exact payload example was found showing either:

- `72.4`
- `0.724`

## Gaps in the Specification

The JSON schema does not explicitly define:

- whether all percentage values are exchanged as whole percent values such as `72.4`
- whether all percentage values are exchanged as fractional values such as `0.724`
- whether generic `Percentage` has a valid range
- whether generic `Percentage` participates in unit conversion
- whether generic `Percentage` has a reference unit
- whether generic `Percentage` has a default unit
- whether `NumericType` format `percentage` changes the expected scale of the numeric value
- display formatting rules for percentages

The schema does define property-specific ranges in at least one place. `Measurement.confidence` documents a confidence scale with endpoints 0 and 100. This does not establish a universal rule for every `Percentage`.

## Recommendation for MCEGold Discovery Portal

What CCOM explicitly specifies:

- `Percentage` is a core type based on `NumericType`.
- `Percentage` is a distinct `ValueClass`.
- `Measure` is the core value type that carries `unitOfMeasure`.
- `UnitOfMeasure` contains conversion metadata.
- `UOMQuantity` can reference a reference unit of measure.
- `MeasurementLocation` can have a default unit of measure.

What CCOM leaves implementation-defined or unspecified:

- Whether a generic percentage is represented as `72.4` or `0.724`.
- Whether a generic percentage has a universal valid range.
- How percentages should be displayed.
- Whether a `NumericType` with `@format` set to `percentage` implies any scaling.

What the Discovery Portal should do for this demo:

- Store and display percentage values exactly as received unless a specific upstream contract says otherwise.
- Do not apply unit conversion to `Percentage` values.
- Do not attach a `UnitOfMeasure` to percentage values unless the incoming CCOM entity explicitly models the value as a `Measure`.
- For known property-specific cases such as `Measurement.confidence`, treat 0-to-100 semantics as property-specific metadata, not a global percentage rule.
- Document any demo assumption separately from the CCOM standard if the Portal chooses to display values with a percent sign.

