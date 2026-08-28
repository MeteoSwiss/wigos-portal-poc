#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys

from wmdr2_projection import SourceRecord, choose_latest_by_wsi, extract_wsi, is_full_facility_record, project_record


def source_urls(input_dir: Path) -> dict[str, str]:
    manifest_path = input_dir / "source-manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {
        str(item.get("name")): str(item.get("url"))
        for item in manifest.get("downloaded", [])
        if item.get("name") and item.get("url")
    }


def load_sources(input_dir: Path) -> tuple[list[SourceRecord], list[dict]]:
    urls = source_urls(input_dir)
    sources: list[SourceRecord] = []
    skipped: list[dict] = []
    for path in sorted(input_dir.glob("*.json")):
        if path.name in {"source-manifest.json", "build-report.json"}:
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            skipped.append({"file": path.name, "reason": f"invalid JSON: {exc}"})
            continue
        if not is_full_facility_record(document):
            skipped.append({"file": path.name, "reason": "not a complete WMDR2 facility Feature"})
            continue
        wsi = extract_wsi(document)
        if not wsi:
            skipped.append({"file": path.name, "reason": "no WSI found"})
            continue
        sources.append(SourceRecord(path=path, document=document, wsi=wsi, source_url=urls.get(path.name)))
    return sources, skipped


def write_tinydb(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {"_default": {str(index + 1): record for index, record in enumerate(records)}}
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the WIGOS OGC API - Records discovery catalogue from WMDR2 examples.")
    parser.add_argument("--input", type=Path, default=Path("data/wmdr2"))
    parser.add_argument("--records-dir", type=Path, default=Path("data/records"))
    parser.add_argument("--tinydb", type=Path, default=Path("data/wigos-facilities.tinydb"))
    parser.add_argument("--evaluation-date", type=date.fromisoformat, default=date.today(), metavar="YYYY-MM-DD")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: input directory does not exist: {args.input}", file=sys.stderr)
        return 2

    sources, skipped = load_sources(args.input)
    selected, duplicates = choose_latest_by_wsi(sources)
    args.records_dir.mkdir(parents=True, exist_ok=True)
    for old in args.records_dir.glob("*.json"):
        old.unlink()

    records: list[dict] = []
    record_reports: list[dict] = []
    for source in selected:
        record, warnings = project_record(source, args.evaluation_date)
        records.append(record)
        (args.records_dir / f"{source.wsi}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        record_reports.append({
            "wsi": source.wsi,
            "sourceFile": source.path.name,
            "warnings": warnings,
        })

    write_tinydb(records, args.tinydb)
    report = {
        "builtAt": datetime.now(timezone.utc).isoformat(),
        "evaluationDate": args.evaluation_date.isoformat(),
        "inputDirectory": str(args.input),
        "candidateFullRecords": len(sources),
        "catalogueRecords": len(records),
        "duplicates": duplicates,
        "skipped": skipped,
        "records": record_reports,
    }
    (args.records_dir / "build-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Built {len(records)} WIGOS facility record(s) into {args.tinydb}")
    if duplicates:
        print(f"Resolved duplicate source records for {len(duplicates)} WSI(s); see data/records/build-report.json")
    warning_count = sum(len(item["warnings"]) for item in record_reports)
    if warning_count:
        print(f"Preserved {warning_count} legacy/non-URI controlled value(s); see build report")
    if not records:
        print("WARNING: catalogue is empty", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
