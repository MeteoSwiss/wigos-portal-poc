# Catalogue service

The PoC catalogue uses **pygeoapi** with `TinyDBCatalogue` and exposes:

```text
/collections/wigos-facilities/items
```

The TinyDB database is generated, disposable discovery state. Canonical metadata remain the published WMDR2 JSON examples from `wmo-im/wmdr2-devt`.

## Local build

From the repository root:

```bash
python scripts/rebuild_catalogue.py
```

This synchronizes candidate full records from:

```text
https://github.com/wmo-im/wmdr2-devt/tree/main/results/wmdr2_json_examples
```

and then builds:

```text
data/records/*.json
data/records/build-report.json
data/wigos-facilities.tinydb
```

Converter fragments (`*_facility.json`, `*_observations*.json`, `*_deployments*.json`, etc.) are not downloaded by default. The builder also verifies by content that a JSON document is a complete facility Feature.

If more than one complete source record describes the same WSI, the builder selects the newest deterministically using `properties.updated`, then `properties.created`, then a leading `YYYYMMDD` filename date. The full decision is recorded in `data/records/build-report.json`.

### Build from a local wmdr2-devt clone

If you already have `wmdr2-devt` locally, no synchronization is needed:

```bash
python scripts/rebuild_catalogue.py --source-dir ../wmdr2-devt/results/wmdr2_json_examples
```

This is particularly convenient while developing the converter.

## Run pygeoapi locally

Create/activate a virtual environment and install:

```bash
pip install -r catalogue/requirements.txt
python scripts/run_catalogue.py
```

The catalogue is then available at `http://localhost:5000`.

`PYGEOAPI_SERVER_URL`, `PORT`, and `WIGOS_CATALOGUE_DB` can override the defaults.
