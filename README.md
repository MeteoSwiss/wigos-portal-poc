# WIGOS Portal PoC

Proof of concept for discovery and map-based exploration of WIGOS facilities described by WMDR2 JSON.

## Scope

The Portal is deliberately read-only. WMDR2 JSON is the canonical metadata representation; the OGC API - Records catalogue is a rebuildable discovery projection. Editing remains the responsibility of the WIGOS Node PoC.

The PoC targets:

- global facility display in Mollweide projection;
- Arctic and Antarctic stereographic views;
- zooming, panning and box selection;
- interactive facility points with compact hover summaries;
- facility search and filtering by facility, observation, programme, instrument, observing method and organization;
- compact facility reports including contacts/organizations;
- OGC API - Records Part 1 as the catalogue interface;
- pygeoapi + TinyDB for the initial catalogue implementation;
- Render deployment later, after the local v0 baseline is usable.

## Authoritative sample data

The PoC catalogue is built directly from the WMDR2 examples published by `wmo-im/wmdr2-devt`:

```text
https://github.com/wmo-im/wmdr2-devt/tree/main/results/wmdr2_json_examples
```

This is deliberate: when the WMDR2 converter produces updated or additional complete examples in that directory, a catalogue rebuild picks them up without maintaining a second Portal-specific sample dataset.

The source directory also contains converter fragments. The synchronization/build pipeline ignores fragments, identifies complete facility records by content, and deduplicates multiple complete records for the same WSI deterministically. See `data/records/build-report.json` after a build.

## Architecture

```text
wmo-im/wmdr2-devt
results/wmdr2_json_examples
        |
        | sync (or direct local path)
        v
cached canonical WMDR2 JSON
        |
        | deterministic discovery projection
        v
OGC API - Records GeoJSON records
        |
        v
pygeoapi + TinyDB  <------>  WIGOS Portal frontend
                               TypeScript / React / Vite / OpenLayers
```

See `docs/WIGOS_RECORDS_PROFILE.md` and `docs/ARCHITECTURE.md`.

## Repository layout

```text
frontend/       Portal UI
catalogue/      pygeoapi configuration and catalogue service
scripts/        WMDR2 sync, projection/build and local service helpers
tests/          projection unit tests
data/wmdr2/     cached canonical WMDR2 examples (generated, git-ignored)
data/records/   generated OGC Records + build report (git-ignored)
docs/           architecture and WIGOS Records profile
render.yaml     later Render Blueprint
```

## Local v0 workflow

### 1. Python environment

Python 3.12+ is required by current pygeoapi. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r catalogue/requirements.txt
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

### 2. Synchronize WMDR2 examples and build the catalogue

```bash
python scripts/rebuild_catalogue.py
```

This reads the published `main` branch, caches candidate full records under `data/wmdr2/`, and generates the discovery catalogue.

If `wmdr2-devt` is already cloned next to this repository, you can instead build directly from it:

```bash
python scripts/rebuild_catalogue.py --source-dir ../wmdr2-devt/results/wmdr2_json_examples
```

That is the preferred workflow while changing the converter because no publication/synchronization step is needed.

Run projection tests with:

```bash
python -m unittest discover -s tests -v
```

### 3. Run the OGC API - Records service

```bash
python scripts/run_catalogue.py
```

Useful endpoints:

```text
http://localhost:5000/
http://localhost:5000/collections/wigos-facilities
http://localhost:5000/collections/wigos-facilities/items
http://localhost:5000/collections/wigos-facilities/queryables
```

### 4. Run the Portal frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`). The frontend defaults to the local catalogue at `http://localhost:5000`.

## Catalogue-build behaviour

- One catalogue record is produced per WSI.
- WMDR2 remains canonical; generated OGC Records/TinyDB files are disposable.
- `properties.updated`, then `properties.created`, then a leading `YYYYMMDD` filename date determine which duplicate full source record wins.
- Controlled values are preserved exactly as present in WMDR2. Legacy numeric/non-URI controlled values are flagged in the build report, not rewritten or guessed.
- Once the WMDR2 converter emits canonical code-list URLs, those URLs flow into the Portal catalogue automatically on the next rebuild.
- `current*` discovery fields are evaluated from observing-configuration time validity; operating status remains separate.

## Status

Local v0 baseline. The catalogue source/build pipeline, first map interactions, initial facets, hover summary and compact report are present. The next work is to exercise the current published WMDR2 examples end-to-end and tighten the projector wherever the current schema exposes structures not yet covered by the compatibility adapter.
