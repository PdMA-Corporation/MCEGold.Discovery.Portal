# MeasurementLocationType reference-data comparison

## Inputs

- ShowMeasurementLocations JSON: captured local message input supplied to `scripts/compare_measurement_location_types.py`
- CCOM Reference Data XML: `docs/CCOM Reference Data.xml`
- Entity type: `MeasurementLocationType`

## Repository Findings

- `MeasurementLocationType` reference data is stored in the canonical CCOM Reference Data XML file.
- The portal loader reads XML `Entity` nodes and filters by `xsi:type = MeasurementLocationType`.
- Message comparison is by `MeasurementLocation.type.UUID`; `MeasurementLocation.UUID` values are not counted as type UUIDs.

## Summary

- Total MeasurementLocations in message: `46`
- Total distinct MeasurementLocationTypes in message: `25`
- Total MeasurementLocationTypes in PdMA Reference Data: `258`
- Count matched: `2`
- Count missing from reference data: `23`
- Count reference-only: `256`
- Count name mismatch: `0`

## Proposed Addendum

Missing message types were written to `docs/measurement-location-type-reference-addendum.csv` for review.
This file is a proposal only; the canonical XML reference data is not modified.

## Details

| Status | Type UUID | Type Name from CCOM Message | Type Name from Reference Data | Usage Count in Message | Example MeasurementLocation Name | Source file / table |
| --- | --- | --- | --- | ---: | --- | --- |
| MissingInReferenceData | `2c84b595-1756-47fb-b0e2-501058180039` | Amplitude, Decibel, Phase 1 |  | 1 | Amplitude, Decibel, 60 Hz, Phase 1, Stator |  |
| MissingInReferenceData | `591a27c4-7153-41b8-92eb-92610f6bd6fb` | Average Current, Fund RMS |  | 2 | Average Current, Stator |  |
| MissingInReferenceData | `f846b275-0127-443b-8b1d-fd8b5d6975e6` | Current 2 (THD) |  | 2 | Current 2 (THD), Stator |  |
| MissingInReferenceData | `565dac40-17ab-4417-ba8d-edf1c7a1e844` | Current Imbalance, Percentage |  | 2 | % Current Imbalance, Stator |  |
| MissingInReferenceData | `b92c4723-7426-4ae8-8ce9-4d856abf5925` | Current Phase 1, Speed |  | 1 | Fp Amplitude 1, Stator |  |
| MissingInReferenceData | `801c0e1b-482a-4f61-a6a2-cad77de33343` | Current, Startup |  | 2 | In-Rush Curr., Stator |  |
| MissingInReferenceData | `40b474a7-571e-45b6-9ba1-8d36abdb5181` | Current, Startup, Delta |  | 2 | Start Up Duration, Stator |  |
| MissingInReferenceData | `84de664e-acff-4661-be57-3e4eac6e533b` | Load, Variance, Maximum |  | 1 | Load, Variance, Maximum, Stator |  |
| MissingInReferenceData | `1a0179b9-458f-437a-a73d-ac70b54355fe` | Output Power Calc. (HP) |  | 2 | Output Power Calc. (HP), Stator |  |
| MissingInReferenceData | `e33144ab-5acb-4637-ae6a-736d615db373` | Peak Current, Phase 1 |  | 2 | Peak Amps 1, Stator |  |
| MissingInReferenceData | `5a9b9702-2138-4a03-8f7f-02533dc808b6` | Peak Current, Phase 2 |  | 2 | Peak Amps 2, Stator |  |
| MissingInReferenceData | `c86f6458-d7c0-4c95-8cb2-94a9cd45cbad` | Peak Current, Phase 3 |  | 2 | Peak Amps 3, Stator |  |
| MissingInReferenceData | `30c9a501-d8c2-48c5-b9ae-31073f12283b` | Power Factor, Average |  | 2 | Total PF, Stator |  |
| MissingInReferenceData | `1aa9f3c4-600f-400f-8b56-a945debd3a44` | Self Impedance Imbalance |  | 2 | Self Imped Imbalance, Stator |  |
| MissingInReferenceData | `d0b3f7ff-af75-4a1f-9945-74446f4b09ba` | Speed RPM |  | 1 | Speed RPM, Stator |  |
| MissingInReferenceData | `6f37356b-45c7-4db5-a709-5c1c03111d5b` | Speed RPM, Estimated |  | 2 | Estimated Speed, Stator |  |
| MissingInReferenceData | `5fc91007-8bc7-4d3b-bfbb-312af0899050` | Torque, Estimated |  | 2 | Estimated Torque (ft.-lb.), Stator |  |
| MissingInReferenceData | `4a261d9d-ba24-432b-b606-4d9283d2732e` | Total kVA |  | 2 | Total kVA, Stator |  |
| MissingInReferenceData | `8aae92ac-8103-4d15-a48a-baf9d022968a` | Total kVAR |  | 2 | Total kVAR, Stator |  |
| MissingInReferenceData | `12d9278c-3505-4a19-b37b-8618d0ad3635` | Total kW |  | 2 | Total kW, Stator |  |
| MissingInReferenceData | `feec5a71-c463-4912-aad4-b261f073616a` | Voltage 2-3 (THD) |  | 2 | Voltage 2-3 (THD), Stator |  |
| MissingInReferenceData | `1182857d-70cf-4dbf-b968-251b8584b2f4` | Voltage Average Line to Line, Fund RMS |  | 2 | Average Ph-Ph, Stator |  |
| MissingInReferenceData | `59e81924-1c13-4e9a-aa86-e1be0d45965f` | Voltage Line to Line Imbalance, Fund |  | 2 | Voltage Imbalance Ph-Ph, Stator |  |
| Matched | `12cc5ab0-b00d-4870-8d78-7a25dbe2d13b` | Efficiency Percentage | Efficiency Percentage | 2 | Efficiency Calc. (%), Stator | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| Matched | `71fbb63d-d323-44de-a659-dfb72a4daf86` | Load, Full Load Percentage | Load, Full Load Percentage | 2 | % FLA, Stator | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `4850d571-7363-4022-8149-a8c1e5a12bd8` |  | Acoustic | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `aae4f5a8-2491-4645-8e30-d378a6bcaa2c` |  | Acoustic, @Discrete Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `a6339ba1-abed-4c02-a58b-84c7cf1d568b` |  | Acoustic, Broadband | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `f6cd2ae2-48c3-4f01-8502-855d8c7a8865` |  | Acoustic, Narrowband | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `037aa318-1335-49f3-8fa8-541b443b1e45` |  | Acoustic, Ultrasonic | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `c48402d9-fe81-4d05-9632-b8a37a7e5f3f` |  | Altitude | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `fce6aab9-a1a5-4127-a329-d5b17a4ea83b` |  | Capacitance | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `e6495dbd-c8bf-4ff0-9316-9519db7ca5ca` |  | Capacitance to Ground | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `6575502b-876e-4832-9ea1-dd226f4b7431` |  | Capacitance to Ground, Armature | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `4abb5409-11d7-4ac8-82b6-ad4725a79501` |  | Capacitance to Ground, Field 1 Circuit | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `9fc28785-d0a2-44d0-95f2-ed8736ab937e` |  | Capacitance to Ground, Field 2 Circuit | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `65019924-b7c9-4d93-be2a-9dc39a14a2bc` |  | Capacitance to Ground, Field 3 Circuit | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `f39f93cd-acd8-44ff-bda1-613b0f2abe78` |  | Capacitance to Ground, Phase 1 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `3ddd7c7f-85c8-4b1a-bc4d-a3c9c6406b2a` |  | Capacitance to Ground, Phase 2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `681bf7b6-d291-4fad-b626-13efc820207f` |  | Capacitance to Ground, Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `00424618-6ded-4462-a29e-9373094a6088` |  | Conductivity | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `e9ee546e-fe81-42d2-a1b2-964ce1dfae71` |  | Current | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `58744e8e-94f0-4277-a4cb-a0d2224065ef` |  | Current Phase Imbalance, Percentage | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `ddd951be-5b31-4855-a789-65f6a7f216ca` |  | Current Phase Imbalance, Percentage, Phase 1 and Phase 2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `0588245e-961c-4d75-b5e5-f6099646ec46` |  | Current Phase Imbalance, Percentage, Phase 1 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `20cca67b-2eb4-4780-9f94-8d1ad3ff1fb0` |  | Current Phase Imbalance, Percentage, Phase 2 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `fe66037a-2a53-4b98-907d-658237b66121` |  | Current, Phase 1 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `67b6ac96-4d71-439d-b1b2-c05731aa753b` |  | Current, Phase 2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `ca64d386-add4-4398-99d3-6054a75028d3` |  | Current, Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `63bb4906-5f6d-498a-8e23-2a439ba2c162` |  | Diameter | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `75818c4c-90a1-4db3-8d5a-6f09350fa318` |  | Distance | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `de606e89-00dc-4b13-880b-cc2632423399` |  | Distance, Position, Shaft | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `f0221180-f4bf-4486-81bc-8bf0485746e8` |  | Distance, Position, Shaft, Axial | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `40612650-cbaf-4fb2-94da-23dcba18de8a` |  | Flow | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `b4be4920-13e7-4a02-9fd3-9cffd8ad5a38` |  | Flow, High Pressure Side | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `f4140524-9731-499a-ad50-0b284b3f32ff` |  | Flow, Inlet | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `9e1dd68d-95d7-4279-bcc5-c9d849361377` |  | Flow, Low Pressure Side | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `580bd580-7ee4-4845-9667-970f03c4de59` |  | Flow, Outlet | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `d4a5efd2-8544-490b-80af-3885ceb034ca` |  | Inductance | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `5d9b68f9-6e6d-4546-bd61-4f0691e5990d` |  | Inductance, Armature | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `5ca7de9d-5ddf-40ea-a360-f27167d36720` |  | Inductance, Field 1 Circuit | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `673f5e08-99bc-441f-b6a2-cc66d24128ef` |  | Inductance, Field 2 Circuit | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `13629d6e-51c8-497a-a593-55ecbd57982d` |  | Inductance, Field 3 Circuit | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `6c825eb6-45db-4bca-b5b5-6423f158669e` |  | Inductance, Phase 1 and Phase 2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `1ad0f930-6946-4dc5-9799-7d3c7d9c8de3` |  | Inductance, Phase 1 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `51906d5f-b156-4bf7-a623-1e2fd4d20477` |  | Inductance, Phase 2 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `f2397269-508a-4a2f-aeda-b6fdffb7ea7c` |  | Inductance, Phase Imbalance, Percentage | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `e113d336-b726-44ce-8e8c-5ec22075bf31` |  | Inductance, Phase Imbalance, Percentage, Phase 1 and Phase 2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `09cd8720-61a8-45d7-ba1a-282074900069` |  | Inductance, Phase Imbalance, Percentage, Phase 1 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `b3ddf1de-d3b2-42ed-8271-c9a0ad104a1d` |  | Inductance, Phase Imbalance, Percentage, Phase 2 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `1e2b3fa7-93eb-4ad8-a0ec-920d5e702a41` |  | Mass | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `b557ad40-c823-46b3-81a1-a949fd3d0022` |  | Power Factor Percentage | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `391db05f-4839-4ebd-a588-e3d35ee76f0f` |  | Pressure | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `400c6d6f-502c-4523-b4de-d5f5c356d6af` |  | Pressure, Differential | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `405328c3-722a-4f43-a3fa-3e2497db24f8` |  | Pressure, Discharge | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `6c5b0b00-c5e5-4626-9521-ade632b3ce85` |  | Pressure, High Pressure Side | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `dcbdf460-f01d-47c4-9c15-d9cd3e7ce3c9` |  | Pressure, Low Pressure Side | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `62571c87-daea-4849-8456-c16d763052a1` |  | Pressure, Total Head | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `9154a7ac-38d5-4cdf-9bcc-ca30ebc25386` |  | Resistance | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `5eaea36d-5302-4aa1-8d7a-fed84e8f5b46` |  | Resistance, Conductor Path | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `1b4cc54a-496b-45c9-af3b-8dcf6aca59e0` |  | Resistance, Conductor Path, Armature | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `04863c42-ce24-4c5f-adf9-7e7261d02e3d` |  | Resistance, Conductor Path, Field 1 Circuit | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `fb2b128e-956d-4e1f-835a-aeb3972a76bf` |  | Resistance, Conductor Path, Field 2 Circuit | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `bfe0737c-547f-4f53-92d3-1ded8752c7e5` |  | Resistance, Conductor Path, Field 3 Circuit | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `df34516e-ab9c-4e4d-9193-1ab735a33a0e` |  | Resistance, Conductor Path, Phase 1 and Phase 2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `ef06038d-022a-4c9e-90e8-d1bb6fd47589` |  | Resistance, Conductor Path, Phase 1 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `d744457c-0210-464a-a329-f3153a788fcd` |  | Resistance, Conductor Path, Phase 2 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `941f3ca4-e3ce-4b0a-b39e-131eb2d892bf` |  | Resistance, Conductor Path, Phase Imbalance, Percentage | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `26d78518-b559-4bb7-8165-4d5aac07daf5` |  | Resistance, Conductor Path, Phase Imbalance, Percentage, Phase 1 and Phase 2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `bd51e858-fa14-4095-b95b-833a9391bdd3` |  | Resistance, Conductor Path, Phase Imbalance, Percentage, Phase 1 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `35686f32-0a66-4a8c-9676-f070a1472681` |  | Resistance, Conductor Path, Phase Imbalance, Percentage, Phase 2 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `07c119c7-4b12-4a27-8d5c-e4ac596e9224` |  | Resistance, Lead to Ground | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `9f6662df-d1af-4ec9-9819-0a069609e993` |  | Resistance, Lead to Ground, Armature | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `cb534f92-8a86-4566-8d67-8cf3f528a7b2` |  | Resistance, Lead to Ground, Field 1 Circuit | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `db67ce25-8b1d-4601-8857-a1865b20d761` |  | Resistance, Lead to Ground, Field 2 Circuit | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `bba4ba97-93ea-4a1d-9225-7d742da12e07` |  | Resistance, Lead to Ground, Field 3 Circuit | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `dd7b13bc-fd2a-4346-843d-9c84c67c8f97` |  | Resistance, Lead to Ground, Phase 1 and Phase 2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `5425d9bd-212c-45c0-9082-142cde3cee44` |  | Resistance, Lead to Ground, Phase 1 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `2b4c4ef8-b7e0-40a4-916f-0e0be1268efa` |  | Resistance, Lead to Ground, Phase 2 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `5250ecef-c1e6-419d-9e7c-c5ae52cf3026` |  | Resistance, Resistance to Ground | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `cfce1e18-1db3-4972-98fe-e9f3e596975c` |  | Resistance, Resistance to Ground, Armature | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `5e34a8c2-416c-4f45-9975-5359d7859243` |  | Resistance, Resistance to Ground, Field 1 Circuit | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `4f921fe2-1ae8-4778-a4d5-ff2c369896fe` |  | Resistance, Resistance to Ground, Field 2 Circuit | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `cccbaa40-e757-4fbc-a612-587683caf589` |  | Resistance, Resistance to Ground, Field 3 Circuit | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `c41e733e-61fb-40cb-9065-a1b45bb5347d` |  | Sample | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `5d7ef52e-57e9-44b8-8ec9-64cbda05259d` |  | Sample, Gas | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `d7e71ae8-802a-4ae2-9640-6dc77053d577` |  | Sample, Liquid | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `146562c1-55ed-418d-be58-52110b81e337` |  | Sample, Liquid, Aqueous | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `e5a39f7a-0ad7-4216-88c7-b24aad22ac4e` |  | Sample, Liquid, Fuel | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `5acbf3b6-73ea-4712-990e-068e985ad36e` |  | Sample, Liquid, Lubrication | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `6fbd2401-2976-4dbd-97af-4a97e8bea43f` |  | Sample, Solid | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `d7a3f78d-69c0-4410-9862-0905b8fdda6b` |  | Size, Diameter | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `eadcce09-8f51-4da5-87c9-b75f22c83106` |  | Size, Height | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `5e4b6afc-ee83-4e6b-99c3-3a2a75beb912` |  | Size, Length | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `e3f20226-957f-4033-b591-5c2d2f80b0ac` |  | Size, Total Area Occupied | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `8091baad-a4ba-425b-8451-ce2b2b23c784` |  | Size, Width | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `fc569ffb-197b-45ef-a7e8-91349de6304e` |  | Speed | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `44ebf7b8-c8a2-4aab-b435-aa541a9f47d5` |  | Speed, Shaft | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `3eeea765-2be0-46c4-a466-5f44621ec15f` |  | Strain | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `358f2215-47ee-4b42-a70a-7ad3adff44fd` |  | Temperature | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `e3e38e39-6329-4fae-a050-f621ded39d67` |  | Temperature, Ambient | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `582e458a-1395-4da2-84ab-9474b2b516a1` |  | Temperature, Internal | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `e59e5182-f78c-4c0c-b639-481aa0c1abff` |  | Temperature, Internal, First Re-heat | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `db472d17-fab3-44c5-bc19-2c4f5b1ccf8f` |  | Temperature, Internal, High Pressure Side | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `03e28f19-ce2f-4055-afd7-fa7c39b3f430` |  | Temperature, Internal, Inlet | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `4f7878aa-a22e-461c-9186-18abed769fff` |  | Temperature, Internal, Low Pressure Side | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `0625f803-8b9b-468a-92fa-4e256748a048` |  | Temperature, Internal, Outlet | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `c953f747-4739-4d6c-8a2a-b067d6f05f2d` |  | Temperature, Internal, Second Re-heat | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `a19d53b5-6b6e-4e4b-8304-f109152af3ae` |  | Temperature, Surface | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `3950292c-1cae-4cf6-b805-4f8acc64bb38` |  | Thermographic | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `ed0347e7-93a3-4dd1-92e1-29e6af3e3c8c` |  | Torque | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `42d30b22-0c2e-4949-8460-7c4d5872a678` |  | Undetermined | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `727f639c-bf80-475e-b579-420f9321fcc7` |  | Uptime, Since Lubricant Adjustment | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `992fd843-4b63-4e47-be4c-b19c1b468149` |  | Uptime, Since Major Maintenance | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `bf1e2253-58c1-434d-b4cf-890e40446bb2` |  | Uptime, Since Startup | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `328db954-4ddc-4328-958f-4984d7359521` |  | Vibration | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `39c8d39e-b065-45a0-ac4a-56ff0a5aa21c` |  | Vibration, Absolute | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `0b952ff4-be13-492b-ac62-0193cb370f8c` |  | Vibration, Absolute, Casing | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `b75190b5-0dc9-48f7-afbd-019dd24dc07f` |  | Vibration, Absolute, Casing, @10X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `45c761fa-7206-44e0-893b-d5e88ccfe247` |  | Vibration, Absolute, Casing, @1X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `45d06ae7-2360-4431-99f1-4795c53297f0` |  | Vibration, Absolute, Casing, @2X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `539cc125-d795-4779-aaa4-a7ef67367ba2` |  | Vibration, Absolute, Casing, @3X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `e7306191-bb26-4b79-88b1-3ee712c67950` |  | Vibration, Absolute, Casing, @4X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `ffdd3383-ed32-4642-a651-f52fb1fe8fe6` |  | Vibration, Absolute, Casing, @5X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `c1b6e64d-6a4b-497d-8457-83ea0d9ac54a` |  | Vibration, Absolute, Casing, @6X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `945bcc50-078a-4419-a04b-356180dcd4df` |  | Vibration, Absolute, Casing, @7X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `bb4c7681-f0e3-401d-b86e-cea2c955fc4d` |  | Vibration, Absolute, Casing, @8X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `306665a5-bbff-4acc-b7f7-2ecf61ee9a8d` |  | Vibration, Absolute, Casing, @9X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `ba97b121-091f-4557-ac08-ccb74767fc3a` |  | Vibration, Absolute, Casing, @AC Line Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `32e69608-be0a-45fb-b804-3185c22f42bb` |  | Vibration, Absolute, Casing, @Background Frequency #1 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `af885f7c-4ea9-4881-bce6-28e1f10cf63c` |  | Vibration, Absolute, Casing, @Background Frequency #2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `f7200ce7-abff-41be-a08f-ae0fbc2d2d7b` |  | Vibration, Absolute, Casing, @Background Frequency #3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `ca21b350-b25f-4317-8c91-d0b23815ef3a` |  | Vibration, Absolute, Casing, @Ball Pass Inner Race Frequency (BPFI) | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `1bae2ae9-a97c-40f6-b8ff-9fd4887ea545` |  | Vibration, Absolute, Casing, @Ball Pass Outer Race Frequency (BPFO) | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `021111cc-b7f1-4a6c-9544-b2a5555bcefd` |  | Vibration, Absolute, Casing, @Ball Spin Frequency (BSF) | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `f43db25f-2c53-4ce1-94bf-62b333961647` |  | Vibration, Absolute, Casing, @Belt Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `3d2b1caa-a3b1-41f8-8d27-7b1feadd2703` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 1 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `1ea5c74c-6b91-46b5-95aa-12995b048855` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 10 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `ec07707b-1e94-4a41-91ac-dcdbffc82334` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 11 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `fdf2fd19-f034-48b2-93b3-e03cfa990266` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 12 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `62bda4b6-86e9-48ab-a29e-1d4711cd840b` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 13 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `e26209cf-37a3-4274-9967-22f352c64fc5` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 14 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `fe2656f1-2725-4107-b9a1-87f140db1031` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 15 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `81f04f28-55f0-4191-be35-29e9cb211c9a` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 16 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `f87b4495-2f07-4bc9-9555-0f7dcc40960f` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 17 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `7d30d698-0297-4365-a730-8e7c1005b6a2` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 18 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `bb7839d8-a333-4b99-8ef5-5605966eb555` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 19 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `d77ba521-3316-45cd-b8db-668494be1dbf` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `3c636206-6251-4568-831d-75c1643bb816` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 20 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `72eaaca0-2b3c-4e9c-b709-c09432019a1d` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 21 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `a8fce921-0731-4e37-a699-38a97329dad4` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 22 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `1d9a6e33-cd97-439c-8c8b-52356d6eaba8` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 23 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `2cc66f8e-ab54-4475-accc-7cd371ae9dd0` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 24 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `884f1f86-35f4-472d-aa43-76666f0b16cc` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 25 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `a142d49e-f3c8-42e3-abed-070b7f8981e6` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `7dced13e-2c7d-4ac0-9c48-7be174e08ea0` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 4 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `56b76553-74c6-44b8-b9d3-d4a474e68d8f` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 5 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `be2cf2b9-f657-47aa-951e-1627ddd35d4d` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 6 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `cd2e59a3-173d-41dc-b0b3-956cf84107ed` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 7 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `218997ac-8a88-4885-8d6a-72afe74a6e8a` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 8 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `d8032f0f-571a-47d7-84cd-fb06e949b10a` |  | Vibration, Absolute, Casing, @Blade Pass Frequency, Stage 9 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `5b018c9b-48b7-474e-9d05-96c3e7f14a33` |  | Vibration, Absolute, Casing, @Chain Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `ecd31b76-9ca8-47d4-ac7f-d2d254e687d2` |  | Vibration, Absolute, Casing, @Critical Frequency #1 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `b1aeef6d-66ba-4d22-b4d9-b1790d6bfb41` |  | Vibration, Absolute, Casing, @Critical Frequency #2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `e0baf12d-961f-4ea2-a6fd-dbd943ee1143` |  | Vibration, Absolute, Casing, @Critical Frequency #3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `2f8d3851-f4df-4db0-b0a7-eda278c2c654` |  | Vibration, Absolute, Casing, @Discrete Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `f67d6f65-d11a-4b26-a6f5-d1d2ed6abec4` |  | Vibration, Absolute, Casing, @Fundamental Train Frequency (FTF) | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `67983c60-f9e9-43b7-8549-9820b47bfd87` |  | Vibration, Absolute, Casing, @Gear, Hunting Tooth Frequency, Input Shaft Driver Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `2fc2d5d7-2e82-4746-a876-4901f6627edd` |  | Vibration, Absolute, Casing, @Gear, Hunting Tooth Frequency, Shaft B Driven Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `8d1ced2f-8b5b-47f2-a83c-856b54ba9774` |  | Vibration, Absolute, Casing, @Gear, Hunting Tooth Frequency, Shaft B Driver Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `31d70638-ad4e-4a75-aa02-4a0a646e0da5` |  | Vibration, Absolute, Casing, @Gear, Hunting Tooth Frequency, Shaft C Driven Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `27e1c36d-b9d3-4bc1-9e2f-670876bb66d8` |  | Vibration, Absolute, Casing, @Gear, Hunting Tooth Frequency, Shaft C Driver Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `0913abbf-4329-46e1-9148-a395fdb1393b` |  | Vibration, Absolute, Casing, @Gear, Hunting Tooth Frequency, Shaft D Driven Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `b102a261-917c-40e8-bceb-25829c70b21a` |  | Vibration, Absolute, Casing, @Gear, Hunting Tooth Frequency, Shaft D Driver Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `32846166-4246-4a9f-ab4f-7489fdb0562a` |  | Vibration, Absolute, Casing, @Gear, Hunting Tooth Frequency, Shaft E Driven Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `92964955-a84e-4e8c-85f7-6faf703179be` |  | Vibration, Absolute, Casing, @Gear, Hunting Tooth Frequency, Shaft E Driver Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `37e935d3-beb2-4a16-94f2-7072cb5fa4a1` |  | Vibration, Absolute, Casing, @Gear, Hunting Tooth Frequency, Shaft F Driven Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `1ae0fd61-c5a9-48f5-acfb-eb9623c8720b` |  | Vibration, Absolute, Casing, @Ghost Frequency, Shaft A-B Gears | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `fec72d64-0325-470b-a500-62a2ce7b7594` |  | Vibration, Absolute, Casing, @Ghost Frequency, Shaft B-C Gears | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `6edc4a03-f79c-4b4c-865f-b8e7f4f7099b` |  | Vibration, Absolute, Casing, @Ghost Frequency, Shaft C-D Gears | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `28a3611d-2f50-45a5-88a6-7fcb966d533f` |  | Vibration, Absolute, Casing, @Ghost Frequency, Shaft D-E Gears | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `8aedcca1-020d-407f-b493-39a95ee8dfb7` |  | Vibration, Absolute, Casing, @Ghost Frequency, Shaft E-F Gears | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `ffdaee0f-3b15-4677-9cf9-fdb2fc17897c` |  | Vibration, Absolute, Casing, @Lobe Frequency, Stage 1 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `3bcc900c-a9dc-48ac-a7bf-54df809f1c18` |  | Vibration, Absolute, Casing, @Lobe Frequency, Stage 2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `b2e200e4-9a3d-4d37-884b-d48703c4af87` |  | Vibration, Absolute, Casing, @Lobe Frequency, Stage 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `64de4a4f-0bfc-4d68-b011-2b89877c8338` |  | Vibration, Absolute, Casing, @Lobe Frequency, Stage 4 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `e8e3388e-5477-4961-88c5-5b140be834a2` |  | Vibration, Absolute, Casing, @Lobe Frequency, Stage 5 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `ab669ff6-e43f-45f9-93e6-a64a00554096` |  | Vibration, Absolute, Casing, @Lobe Frequency, Stage 6 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `b5274d59-2b45-4ca4-bb34-02ad4bfd0b1e` |  | Vibration, Absolute, Casing, @Mesh Frequency, Input Shaft Driver Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `47a6ac2c-73b1-4c64-b678-d28d312aee78` |  | Vibration, Absolute, Casing, @Mesh Frequency, Planetary Gear A | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `0c8d4d17-e359-416a-9012-0bc2f13e546b` |  | Vibration, Absolute, Casing, @Mesh Frequency, Planetary Gear B | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `d48a3c0c-5da9-4ed2-bd70-bb9cf0a82431` |  | Vibration, Absolute, Casing, @Mesh Frequency, Planetary Gear C | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `bfc92cbf-2a85-4859-8443-8b34977ca669` |  | Vibration, Absolute, Casing, @Mesh Frequency, Planetary Gear D | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `c7ef34dc-d351-4498-ae9c-d880d73cb53a` |  | Vibration, Absolute, Casing, @Mesh Frequency, Planetary Gear E | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `8707f562-9daf-4cc3-b8f8-307626b1ff69` |  | Vibration, Absolute, Casing, @Mesh Frequency, Planetary Gear F | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `706de816-db5a-45f0-a746-914f105cc938` |  | Vibration, Absolute, Casing, @Mesh Frequency, Ring Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `c25b0034-7184-422a-b004-c6047d8e30aa` |  | Vibration, Absolute, Casing, @Mesh Frequency, Shaft B Driven Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `948848f4-5463-4086-9e37-250a089e50eb` |  | Vibration, Absolute, Casing, @Mesh Frequency, Shaft B Driver Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `87e42473-fc78-4904-9d68-05d4cfc9b507` |  | Vibration, Absolute, Casing, @Mesh Frequency, Shaft C Driven Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `9b313913-8f93-4a01-ad5b-f2583fc84ac3` |  | Vibration, Absolute, Casing, @Mesh Frequency, Shaft C Driver Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `d2ec6c17-06a0-4928-adf9-bf71aa6fa9cb` |  | Vibration, Absolute, Casing, @Mesh Frequency, Shaft D Driven Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `a3683f2b-a9f1-4c20-a6f9-ddd7487f7ea8` |  | Vibration, Absolute, Casing, @Mesh Frequency, Shaft D Driver Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `00effc7c-2b90-4fd5-a5a5-93d25019c0ca` |  | Vibration, Absolute, Casing, @Mesh Frequency, Shaft E Driven Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `8f7d2d3d-e8d8-4b1b-8a9a-c82f13802530` |  | Vibration, Absolute, Casing, @Mesh Frequency, Shaft E Driver Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `c6f4b3b3-7619-40a0-b8b0-e6de1a50120b` |  | Vibration, Absolute, Casing, @Mesh Frequency, Shaft F Driven Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `43a1c2e0-2ae1-4e62-af55-c4a724380c0b` |  | Vibration, Absolute, Casing, @Mesh Frequency, Sun Gear | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `d80067b5-0226-47bd-a3cd-2d5a4f72c32e` |  | Vibration, Absolute, Casing, @Natural Frequency #1 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `37047771-1108-4b9b-893d-ab99bce53472` |  | Vibration, Absolute, Casing, @Natural Frequency #2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `26151367-bbee-4952-8f45-e7143838c462` |  | Vibration, Absolute, Casing, @Natural Frequency #3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `485f24a5-9778-44ca-a17d-5ecf8be96c95` |  | Vibration, Absolute, Casing, @Rotor Bar Pass Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `e0ea93c1-e490-4b77-a57f-bef034361d05` |  | Vibration, Absolute, Casing, @Slip Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `eecdb575-ba04-445b-8155-b6e30b46a3a8` |  | Vibration, Absolute, Casing, @Stator Slot Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `b25a5e9e-3dd3-46e9-8401-df98fafb805f` |  | Vibration, Absolute, Casing, @Torsional Resonance Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `6d2f2553-cdb5-4ea3-a60a-24f13e68de3b` |  | Vibration, Absolute, Casing, @Vane Pass Frequency, Stage 1 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `54db9db2-a009-4e64-a3b8-4110951eaa1e` |  | Vibration, Absolute, Casing, @Vane Pass Frequency, Stage 2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `3005a27e-c787-48ff-8582-a118cd70bbe1` |  | Vibration, Absolute, Casing, @Vane Pass Frequency, Stage 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `50442b2f-689b-4b11-b8cf-a552bdf7dc54` |  | Vibration, Absolute, Casing, @Vane Pass Frequency, Stage 4 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `30ea2e99-ba3d-4183-b04e-5ec8cbf56978` |  | Vibration, Absolute, Casing, @Vane Pass Frequency, Stage 5 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `8e4f5439-3d80-4826-a3b1-3c79065fc4be` |  | Vibration, Absolute, Casing, @Vane Pass Frequency, Stage 6 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `ee66fee7-b13d-4f84-939e-7a9ea262aa97` |  | Vibration, Absolute, Casing, Broadband | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `c2ebec2f-1102-42da-b3b4-27825c01684f` |  | Vibration, Absolute, Casing, Narrowband | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `522f48d0-5702-4ee6-bba8-d3cc9d1c4c9e` |  | Vibration, Absolute, Shaft | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `598f4be1-a1da-4c32-a6ae-be2e8ee40bd8` |  | Vibration, Absolute, Shaft, @10X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `d26c81dd-1efc-4376-a80e-05d9c43caaf8` |  | Vibration, Absolute, Shaft, @1X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `7870e2df-e456-4240-a5ab-d0b67aa75de0` |  | Vibration, Absolute, Shaft, @2X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `9d0bdb89-3273-40c5-a97e-833d6cd2fe71` |  | Vibration, Absolute, Shaft, @3X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `95d2ff82-519a-4342-be24-acd0d7bc9509` |  | Vibration, Absolute, Shaft, @4X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `680f023e-a80e-4610-9c2a-188ff057aa34` |  | Vibration, Absolute, Shaft, @5X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `649c7ed4-a7a5-4a1a-a6c3-35799760a9ca` |  | Vibration, Absolute, Shaft, @6X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `5017fea9-d8f0-46d8-9b4d-6bccbbce11a8` |  | Vibration, Absolute, Shaft, @7X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `63b9ac9f-b78f-4af3-af9a-283dc7c17eae` |  | Vibration, Absolute, Shaft, @8X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `cd709993-e3d1-4f78-b317-d68f8b862c65` |  | Vibration, Absolute, Shaft, @9X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `7227fb3b-cfdd-4981-9b45-ad5a5d4f3f4e` |  | Vibration, Absolute, Shaft, @Discrete Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `60152bcc-9e33-4e6e-8ef3-1cd9e8c5a24f` |  | Vibration, Absolute, Shaft, Broadband | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `a5027a1e-208a-4996-adad-1f7f590ecb61` |  | Vibration, Absolute, Shaft, Narrowband | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `d7fc8178-265b-426d-9185-a73bc32d981a` |  | Vibration, Relative | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `ecc4378a-5c2a-4ae4-b7d8-7b232f4d41f1` |  | Vibration, Relative, Shaft | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `5a178e7f-d98c-4be8-a1af-f8593242af8f` |  | Vibration, Relative, Shaft, @10X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `4f4c19c2-4d79-41d2-a035-dd1736d8e230` |  | Vibration, Relative, Shaft, @1X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `96fcbca9-e39a-4c00-8e77-965468f8d77a` |  | Vibration, Relative, Shaft, @2X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `f5883947-c222-4591-8c87-845b61c31ee7` |  | Vibration, Relative, Shaft, @3X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `f155fffb-056c-4bc7-ae44-f26a0786799b` |  | Vibration, Relative, Shaft, @4X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `d5e9a4b9-d215-4d4d-9cf1-a979ef95f817` |  | Vibration, Relative, Shaft, @5X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `999c8837-d346-4dea-b7a6-7845bfe1897f` |  | Vibration, Relative, Shaft, @6X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `e2e187be-001e-4c39-8bde-25b513ade587` |  | Vibration, Relative, Shaft, @7X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `89397ce2-502f-4e44-ac76-d0e6a355af58` |  | Vibration, Relative, Shaft, @8X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `3462b75a-0d56-4667-8d82-01ff440de99f` |  | Vibration, Relative, Shaft, @9X Running Speed Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `aac8e163-a46d-479b-bc91-d595b8e1a5f9` |  | Vibration, Relative, Shaft, @Discrete Frequency | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `74e64c07-4690-4c1f-a9d0-aad8ab879811` |  | Vibration, Relative, Shaft, Broadband | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `3930df27-07ea-49e1-8caf-4ee774423ada` |  | Vibration, Relative, Shaft, Narrowband | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `2c44ba1a-50ce-4a97-a267-4907f99627be` |  | Voltage | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `d0f78757-32ad-4611-8453-a27b203d7e18` |  | Voltage, DC Gap | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `4a5dec47-fcd2-47d6-850a-329a6c405998` |  | Voltage, Phase 1 and Phase 2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `4a88c6e5-477d-464b-b468-9c7b6a9c98a5` |  | Voltage, Phase 1 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `c7abe5d3-b88d-4649-ba15-3c68a19d90cf` |  | Voltage, Phase 1 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `2fc35111-a0dd-484c-b134-b8c171e4026f` |  | Voltage, Phase Imbalance, Percentage | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `25fa1c54-839e-4e3a-bba8-1565583cd177` |  | Voltage, Phase Imbalance, Percentage, Phase 1 and Phase 2 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `77a525f5-3e3d-485f-9bf2-3f2ac60a3a01` |  | Voltage, Phase Imbalance, Percentage, Phase 1 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `41923e79-199d-45e5-b7fe-ff6e02f08960` |  | Voltage, Phase Imbalance, Percentage, Phase 2 and Phase 3 | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `9c52d537-2fcf-46e2-adf0-ce9168667442` |  | Volume | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |
| ReferenceOnly | `7be11273-3e5d-4750-8e88-a619f112f665` |  | Work | 0 |  | docs/CCOM Reference Data.xml \| xsi:type=MeasurementLocationType |

