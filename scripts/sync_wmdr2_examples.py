#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_REPO = "wmo-im/wmdr2-devt"
DEFAULT_REF = "main"
DEFAULT_PATH = "results/wmdr2_json_examples"
FRAGMENT_MARKERS = (
    ".facility.json",
    "_facility.json",
    "_header.json",
    "_observations.json",
    "_observations_1.json",
    "_observations_5.json",
    "_deployments.json",
    "_deployments_1.json",
    "_deployments_3.json",
)


def request_json(url: str, token: str | None = None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "wigos-portal-poc"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "wigos-portal-poc"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize published WMDR2 JSON examples from GitHub.")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument("--path", default=DEFAULT_PATH)
    parser.add_argument("--output", type=Path, default=Path("data/wmdr2"))
    parser.add_argument("--include-fragments", action="store_true", help="Also download converter fragment files.")
    args = parser.parse_args()

    api_url = f"https://api.github.com/repos/{args.repo}/contents/{args.path}?ref={args.ref}"
    try:
        listing = request_json(api_url, os.environ.get("GITHUB_TOKEN"))
    except (HTTPError, URLError) as exc:
        print(f"ERROR: cannot list WMDR2 examples: {exc}", file=sys.stderr)
        return 2

    if not isinstance(listing, list):
        print("ERROR: GitHub response is not a directory listing", file=sys.stderr)
        return 2

    args.output.mkdir(parents=True, exist_ok=True)
    downloaded: list[dict] = []
    skipped: list[str] = []
    failures: list[dict] = []

    for item in listing:
        name = item.get("name", "")
        if item.get("type") != "file" or not name.endswith(".json"):
            continue
        if not args.include_fragments and any(name.endswith(marker) for marker in FRAGMENT_MARKERS):
            skipped.append(name)
            continue
        url = item.get("download_url")
        if not url:
            continue
        try:
            payload = download(url)
            # Validate JSON before replacing an existing cached copy.
            json.loads(payload)
            (args.output / name).write_bytes(payload)
            downloaded.append({"name": name, "sha": item.get("sha"), "url": url})
            print(f"synced {name}")
        except Exception as exc:  # keep the rest of the synchronization useful
            failures.append({"name": name, "error": str(exc)})
            print(f"WARNING: failed {name}: {exc}", file=sys.stderr)

    manifest = {
        "source": {
            "repository": args.repo,
            "ref": args.ref,
            "path": args.path,
            "api": api_url,
        },
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "downloaded": downloaded,
        "skippedFragments": skipped,
        "failures": failures,
    }
    (args.output / "source-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n{len(downloaded)} candidate full-record file(s) synchronized to {args.output}")
    if failures:
        print(f"{len(failures)} download(s) failed; see source-manifest.json", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
