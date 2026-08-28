#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def run(args: list[str]) -> None:
    print("+", " ".join(args))
    subprocess.run(args, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize WMDR2 examples and rebuild the local WIGOS catalogue.")
    parser.add_argument("--ref", default="main")
    parser.add_argument("--source-dir", type=Path, help="Use an existing local wmdr2_json_examples directory instead of GitHub.")
    parser.add_argument("--evaluation-date", help="Evaluate current* fields on YYYY-MM-DD (defaults to today).")
    args = parser.parse_args()

    python = sys.executable
    if args.source_dir:
        input_dir = args.source_dir
    else:
        input_dir = Path("data/wmdr2")
        run([python, "scripts/sync_wmdr2_examples.py", "--ref", args.ref, "--output", str(input_dir)])

    command = [python, "scripts/build_catalogue.py", "--input", str(input_dir)]
    if args.evaluation_date:
        command.extend(["--evaluation-date", args.evaluation_date])
    run(command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
