# Architecture

## Responsibilities

### WIGOS Node

Authoring, editing, validation and management of canonical WMDR2 JSON records.

### WMDR2 example source

For the PoC, the published complete examples under `wmo-im/wmdr2-devt/results/wmdr2_json_examples` are the authoritative source dataset. This keeps Portal development coupled to the real converter outputs rather than a separate synthetic fixture set.

The source directory may also contain converter fragments and multiple dated outputs for the same WSI. The catalogue build stage classifies and deduplicates these; it never writes back to `wmdr2-devt`.

### Global catalogue

Discovery/indexing service. For the PoC, pygeoapi exposes OGC API - Records Part 1 and reads a rebuildable TinyDB index.

### WIGOS Portal

Read-only exploration and reporting client. The browser talks directly to OGC API - Records. No Portal-specific backend is introduced unless a later requirement demonstrates that one is needed.

## Data/build flow

```text
wmo-im/wmdr2-devt / results/wmdr2_json_examples
               |
               | GitHub synchronization
               | or direct local path
               v
        canonical WMDR2 cache
               |
               | project_record()
               | - identify WSI
               | - flatten discovery fields
               | - derive current* fields
               | - preserve standard contacts
               | - record warnings/provenance
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

The build is deterministic and disposable. A build report records skipped non-full documents, duplicate WSI choices, source filenames and controlled values that are still non-URI legacy values.

## Local development

The initial milestone is local-first:

1. synchronize/build the catalogue with `scripts/rebuild_catalogue.py`;
2. run pygeoapi with `scripts/run_catalogue.py`;
3. run the Vite frontend separately.

A developer working simultaneously on the WMDR2 converter can point the builder directly at a local `wmdr2-devt/results/wmdr2_json_examples` directory, avoiding a GitHub round trip.

## Deployment

The later Render deployment uses two services:

1. `wigos-portal-poc` — static Vite frontend;
2. `wigos-portal-poc-catalogue` — Docker web service running pygeoapi.

The catalogue filesystem remains disposable. The catalogue service can synchronize the published `wmdr2-devt` examples and rebuild its TinyDB index during startup/deployment, so new published examples become available without being copied into the Portal repository.

## Mapping

OpenLayers + proj4js are used so the application is not tied to Web Mercator.

Initial views:

- global: Mollweide (`ESRI:54009` / equivalent proj4 definition);
- Arctic: WGS 84 / Arctic Polar Stereographic (`EPSG:3995`);
- Antarctic: WGS 84 / Antarctic Polar Stereographic (`EPSG:3031`).

Projection switching is explicit (`Global | Arctic | Antarctic`) rather than automatic. GeoJSON source coordinates remain geographic; features are freshly projected into the active map view rather than repeatedly mutating existing geometries when the projection changes.

## Search flow

```text
Portal state
  |-- free text -------------------------+
  |-- map extent / user box -------------+--> OGC API - Records
  |                                      |       q / bbox
  +-- initial PoC discovery facets -------+--> client-side refinement
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

The first client-side facet implementation is intentional. It lets the team validate useful discovery fields against real WMDR2 examples before committing to the exact CQL2 predicates for array-valued queryables. pygeoapi remains the standards-facing catalogue API throughout.

The authoritative full WMDR2 JSON is linked from the discovery record and can be used for detailed facility reporting where the discovery projection is insufficient.
