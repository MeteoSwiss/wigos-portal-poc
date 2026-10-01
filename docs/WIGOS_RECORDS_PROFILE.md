# WIGOS profile of OGC API - Records Part 1 — PoC v0.2

## 1. Purpose

This profile defines the discovery projection used by the WIGOS Portal PoC against **wmdr2-devt v0.4.0**. One catalogue record describes one WIGOS Facility. The catalogue record is derived/rebuildable; canonical WMDR2 JSON remains authoritative.

## 2. Core semantics

1. One OGC Record represents one WIGOS Facility.
2. WMDR2 JSON is canonical; the catalogue record is a discovery projection.
3. Record `id` is the root WMDR2 WSI.
4. Record `time` is Facility lifetime only.
5. Controlled discovery values use Concept `url` as the machine value where available; compact Concept `id` is a fallback, not a replacement URI.
6. An Observation is current when at least one `Configuration.time` contains the evaluation date. Operating status remains independent.
7. Programme affiliation dates, when supplied, constrain `currentProgrammes` separately from Configuration validity.
8. Fixed facilities are fully supported. Moving facilities use the root current/latest point for the map while `temporalGeometry` remains canonical history.

## 3. Standard/core properties

| OGC Record member | WMDR2 source / meaning |
|---|---|
| `id` | root WSI |
| `geometry` | current Facility geometry/current position |
| `time` | Facility lifetime |
| `properties.type` | `wigosFacility` |
| `properties.title` | Facility title |
| `properties.description` | Facility description when present |
| `properties.externalIds` | generic OGC external identifiers, preserved unchanged |
| `properties.additionalIds` | additional WSI values when present |
| `properties.contacts` | Facility OGC Contacts with contextual roles |
| `links` | canonical WMDR2 JSON and other record links |

The projector does **not** inject the WSI into generic `externalIds`; primary identity already resides in Record `id`.

## 4. WIGOS discovery/query properties

Arrays contain unique values. Controlled values are canonical URIs when Concept `url` is available.

| Property | Type | Meaning |
|---|---|---|
| `facilityType` | URI/string | Facility type |
| `territory` | URI/string | Current/latest `territories[]` assignment |
| `wmoRegion` | URI/string | WMO Region |
| `programmes` | URI/string[] | All Observation programme affiliations |
| `currentProgrammes` | URI/string[] | Affiliations applicable to current Observations and current by `dates` when dates exist |
| `observedProperties` | URI/string[] | All Observation `observedProperty` values |
| `currentObservedProperties` | URI/string[] | Values with at least one current Configuration |
| `observedGeometries` | URI/string[] | Observation geometries |
| `observingMethods` | URI/string[] | Methods from Configurations, procedures and referenced Instruments |
| `currentObservingMethods` | URI/string[] | Methods associated with current Configurations |
| `instrumentManufacturers` | string[] | Manufacturers of referenced Instruments |
| `currentInstrumentManufacturers` | string[] | Manufacturers referenced by current Configurations |
| `instrumentModels` | string[] | Referenced Instrument models |
| `currentInstrumentModels` | string[] | Instrument models referenced by current Configurations |
| `currentObservationOperatingStatuses` | URI/string[] | Explicit `operatingStatus` values on current Configurations |
| `organizations` | string[] | Unique organizations from Facility/Observation/Configuration contacts |
| `observationCount` | integer | Number of WMDR2 Observations |
| `currentObservationCount` | integer | Number with at least one current Configuration |
| `mobile` | boolean | Derived from Facility type and/or root `temporalGeometry.type=MovingPoint` |

The `current*` fields are deliberate discovery-index duplication; they do not replace canonical Configuration history.

## 5. Controlled concepts

v0.4.0 uses objects such as:

```json
{
  "id": "12006",
  "url": "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/12006"
}
```

The flattened catalogue value is the `url` when present. The Portal may display the compact last path component. Identifier-only Concepts remain valid WMDR2; when one appears in a known controlled discovery field the compact value is retained and a build warning is recorded rather than fabricating a URI.

## 6. Programme and current-observation logic

For each Observation:

```text
current Observation
    = any Configuration.time contains evaluation date
```

For each ProgrammeAffiliation on such an Observation:

```text
current programme
    = dates absent OR dates contain evaluation date
```

`reportingStatus` and `operatingStatus` remain explicit independent assertions and are not inferred.

## 7. Territory selection

Canonical WMDR2 uses `properties.territories[]`. For the singular discovery facet:

1. prefer an occurrence whose `dates` contains the evaluation date (or has no dates);
2. otherwise use the latest available occurrence.

The canonical list remains available in WMDR2 and is not replaced by this flattened property.

## 8. Instruments and methods

`Configuration.instrument` is a record-local ID reference to `properties.instruments[].id` in wmdr2-devt v0.4.0. The projector resolves that reference to derive manufacturer/model and instrument-level `observingMethods[]`.

Instrument-level methods are useful for discovery when a Configuration `observingMethod` is `null` or absent.

## 9. Contacts and organizations

Facility contacts are retained in standard `properties.contacts`.

The `organizations` facet may include organizations found in Facility, Observation and Configuration contact occurrences. It is a discovery convenience only; contextual roles remain authoritative in the original WMDR2 occurrences.

## 10. Queryables required by the Portal

Minimum PoC queryables:

- `id`
- `externalIds`
- `additionalIds`
- `type`
- `bbox`
- `datetime`
- `q`
- `facilityType`
- `territory`
- `wmoRegion`
- `programmes`
- `currentProgrammes`
- `observedProperties`
- `currentObservedProperties`
- `observedGeometries`
- `observingMethods`
- `currentObservingMethods`
- `instrumentManufacturers`
- `currentInstrumentManufacturers`
- `instrumentModels`
- `currentInstrumentModels`
- `currentObservationOperatingStatuses`
- `organizations`
- `mobile`

CQL2 can be used later for server-side combinations, especially array membership and spatial predicates.

## 11. Compact Facility report

The compact report is a Portal view, not a second metadata model. Initial sections include:

1. Facility identity, location and lifetime;
2. total/current Observation counts;
3. current programmes and observed properties;
4. current methods and instruments;
5. organizations and Facility contacts;
6. links to the OGC catalogue record and canonical WMDR2 JSON.

Richer Observation/configuration/history reporting remains a Portal presentation task over canonical WMDR2.

## 12. Deferred decisions

- independent Observation catalogue records;
- trajectory visualization for moving facilities;
- richer derived Observation temporal coverage;
- production catalogue/search backend;
- catalogue editing/transactions;
- catalogue-side facet aggregation/CQL2 implementation.
