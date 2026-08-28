# WIGOS profile of OGC API - Records Part 1 — PoC v0.1

## 1. Purpose

This profile defines the discovery projection used by the WIGOS Portal PoC. One catalogue record describes one WIGOS facility. The catalogue record is derived and rebuildable; the WMDR2 JSON record remains authoritative.

## 2. Agreed semantics

1. One OGC Record represents one WIGOS Facility.
2. WMDR2 JSON is canonical; the catalogue record is a discovery projection.
3. The OGC Record `id` is the WIGOS Station Identifier (WSI).
4. OGC Record `time` represents the facility lifetime only.
5. Controlled concepts use canonical resolvable URIs as machine values. Human-readable labels are presentation metadata, not identifiers.
6. `current` means that the relevant `ObservingConfiguration.time` contains the evaluation date. Operational status remains an independent concept.
7. Fixed-point facilities are fully supported in the first PoC. Moving facilities use a current/latest point where available; trajectory visualization is deferred.

## 3. OGC Record core properties

The following use standard OGC API - Records properties and MUST NOT be duplicated as WIGOS-specific extensions unless a query optimization requires it.

| OGC Record member | WMDR2 source / meaning |
|---|---|
| `id` | WSI |
| `geometry` | current facility geometry / current position |
| `time` | facility lifetime |
| `properties.type` | `wigosFacility` |
| `properties.title` | facility title |
| `properties.description` | facility description, when present |
| `properties.externalIds` | WSI plus suitable additional facility identifiers |
| `properties.themes` | controlled WIGOS concepts where useful for generic catalogue clients |
| `properties.contacts` | WMDR2 contacts applicable to the facility/resource, including contextual roles |
| `links` | canonical WMDR2 JSON; Portal facility report; optional Node link |

### Contacts

OGC API - Records already defines a standard `contacts` property. The PoC maps WMDR2 contact information to it rather than inventing a WIGOS contact extension.

Where available, retain:

- contact identifier;
- person name;
- organization;
- position;
- email(s);
- phone(s);
- address(es);
- link(s);
- contextual role(s).

Facility-level and ObservationSeries-level assignments remain distinguishable in the full WMDR2 report. The discovery record may contain the contacts relevant for general discovery/reporting; it must not destroy contextual role information during projection.

## 4. WIGOS discovery/query properties

The following extension properties are intentionally denormalized for discovery. Arrays contain unique values. Controlled values are canonical URIs.

| Property | Type | Meaning |
|---|---|---|
| `facilityType` | URI | Facility/station/platform type |
| `territory` | URI/string | Current/latest territory assignment |
| `wmoRegion` | URI/string | WMO Region |
| `programmes` | URI[] | All programme/network affiliations represented in the record |
| `currentProgrammes` | URI[] | Programme affiliations current at evaluation date, where derivable |
| `observedProperties` | URI[] | All observed variables represented by ObservationSeries |
| `currentObservedProperties` | URI[] | Observed variables with at least one current observing configuration |
| `observedGeometries` | URI[] | Observed geometries |
| `observingMethods` | URI[] | All observing methods represented in configurations/procedures |
| `currentObservingMethods` | URI[] | Methods used by at least one current observing configuration |
| `instrumentManufacturers` | string[] | All manufacturers represented in referenced instruments |
| `currentInstrumentManufacturers` | string[] | Manufacturers of currently configured instruments |
| `instrumentModels` | string[] | All instrument models represented in the facility record |
| `currentInstrumentModels` | string[] | Models referenced by current observing configurations |
| `currentObservationOperatingStatuses` | URI[] | Explicit operating-status values on current configurations; absence is not fabricated |
| `organizations` | string[] | Unique organizations represented by projected contacts; convenience query/facet field |
| `observationSeriesCount` | integer | Number of ObservationSeries in the facility record |
| `currentObservationSeriesCount` | integer | Number with at least one current observing configuration |
| `mobile` | boolean | True when facility geometry represents a moving platform/facility |

The `current*` fields are deliberate index duplication. They avoid forcing clients or catalogue engines to reproduce WMDR2 temporal business logic while filtering.

## 5. Controlled concepts and labels

The authoritative value stored in queryable fields is the canonical URI, for example:

```json
{
  "observedProperties": [
    "https://codes.wmo.int/wmdr/ObservedVariable/..."
  ]
}
```

Labels are resolved for presentation and may be cached by the Portal. The URI, not a translated label or local notation, remains the query value.

## 6. Current versus operational

`current` is temporal validity:

```text
ObservingConfiguration.time contains evaluation date
```

Operational status is separate:

```text
ObservingConfiguration.operatingStatus
```

If `operatingStatus` is absent, the catalogue projection MUST NOT infer `operational`.

## 7. Queryables required by the Portal

Minimum PoC queryables:

- `id` / `externalIds`
- `type`
- `bbox`
- `datetime` (facility lifetime)
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

CQL2 is used where equality predicates are insufficient, especially for combinations of array membership and explicit spatial selection geometry.

## 8. Facility report

The compact report is a Portal view, not a second metadata model. It combines the discovery record with canonical WMDR2 content as needed.

Initial sections:

1. Facility identity, location, lifetime and high-level status.
2. Programmes.
3. ObservationSeries summary table: observed property, current status, method, instrument.
4. Instruments in use.
5. Observing methods in use.
6. Contacts and organizations.
7. Collapsible location/history, environment and additional metadata.
8. Links to OGC catalogue record and canonical WMDR2 JSON; optional "Open in WIGOS Node" link.

## 9. Deferred decisions

- independent ObservationSeries catalogue records;
- trajectory/track catalogue geometry and visualization for moving facilities;
- exact derived ObservationSeries temporal coverage property;
- production search backend (Elasticsearch/OpenSearch or catalogue implementation selected by the future global service);
- catalogue editing/transactions.
