# Architecture

## Responsibilities

### WIGOS Node

Authoring, editing, validation and management of canonical WMDR2 JSON records.

### WMDR2 source

For the PoC, the published complete examples under `wmo-im/wmdr2-devt/results/wmdr2_json_examples` are the source dataset. The catalogue projector currently targets **WMDR2 development model v0.4.0**.

v0.4.0 uses canonical `observations[]`, `configurations[]`, `territories[]`, structured `programAffiliations[]`, reusable record-local Instruments and Concept objects (`id` plus optional `url`). The catalogue no longer needs the earlier ObservationSeries/deployment compatibility aliases.

### Global catalogue

Discovery/indexing service. pygeoapi exposes OGC API - Records Part 1 and reads a rebuildable TinyDB index in the PoC.

### WIGOS Portal

Read-only exploration/reporting client. The browser talks to OGC API - Records. No Portal-specific backend is required for the current PoC.

## Data/build flow

```text
wmo-im/wmdr2-devt v0.4.0 / results/wmdr2_json_examples
               |
               | GitHub synchronization
               | or direct local path
               v
        canonical WMDR2 JSON
               |
               | project_record()
               | - root id -> WSI
               | - Concept.url -> discovery machine value
               | - observations[] / configurations[]
               | - derive current* fields
               | - resolve record-local instruments
               | - preserve standard contacts
               | - report missing URI/provenance warnings
               v
        OGC Records GeoJSON
               |
               +--> individual records for inspection
               |
               +--> TinyDB index
                        |
                        v
                 pygeoapi OGC API - Records
                        |
                        v
                    Portal UI
```

The build is deterministic and disposable. The report includes the target WMDR2 model version, evaluation date, skipped documents, duplicate WSI choices, source filenames and controlled values that lack a canonical URI.

## Discovery semantics

- one OGC Record per WSI;
- root WMDR2 `id` is the Record `id`;
- generic `externalIds` is preserved unchanged;
- `additionalIds` carries additional WSI values when present;
- Facility `time` is the Record temporal extent;
- current observation discovery state is derived from `Configuration.time`;
- programme dates are considered separately from configuration validity;
- operating/reporting status is not used as a substitute for temporal validity;
- controlled discovery values use Concept `url` where available;
- Facility contacts remain the standard Record `contacts`; `organizations` is a convenience facet derived across contextual contact occurrences.

## Local development

1. `pytest -q`
2. `python scripts/rebuild_catalogue.py` or point it at a local `wmdr2-devt` clone;
3. `python scripts/run_catalogue.py`;
4. run the Vite frontend separately.

## Deployment

Current Render deployment uses two services:

1. `wigos-portal-poc` — static Vite frontend;
2. `wigos-catalogue-poc` — pygeoapi Web Service.

The catalogue filesystem/index remains disposable and is rebuilt from WMDR2 source data. The pygeoapi HTML shell uses `catalogue/templates/_base.html` solely to add a Documentation link to the GitHub README; other templates fall back to pygeoapi 0.24.0 defaults.

## Mapping

OpenLayers + proj4js support three overview projections:

- Global Mollweide (`ESRI:54009`);
- Arctic polar stereographic (`EPSG:3995`);
- Antarctic polar stereographic (`EPSG:3031`).

Natural Earth provides the overview basemap. A separate **Detailed map** control becomes available only after the user has zoomed to a sufficiently small geographic extent; it switches explicitly to Web Mercator/OSM and provides **Back to overview**.

## Search flow

```text
Portal state
  |-- free text -------------------------+
  |-- map extent / box ------------------+--> OGC API - Records
  |                                      |       q / bbox
  +-- cascading discovery facets --------+--> client-side refinement (PoC)
       programme
       observed property
       method
       instrument
       organization
                                                |
                                                v
                                         GeoJSON records
                                                |
                                                +--> map
                                                +--> compact report
```

The current client-side facet implementation validates the discovery profile against real WMDR2 records. Server-side CQL2/queryable faceting can replace the implementation later without changing the user interaction model.
