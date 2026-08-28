#!/usr/bin/env python3
"""Build and run the local pygeoapi catalogue from the project virtualenv.

Docker-free local launcher.  The virtual environment is identified via
``sys.prefix`` rather than by resolving the Python executable symlink: on
Ubuntu a venv's ``bin/python`` commonly resolves to ``/usr/bin/pythonX.Y``.
"""
from __future__ import annotations

import argparse
from importlib import metadata
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).absolute().parents[1]
CONFIG = ROOT / "catalogue" / "pygeoapi-config.yml"
OPENAPI = ROOT / "catalogue" / "openapi.yml"
DB = ROOT / "data" / "wigos-facilities.tinydb"
SOURCE_DIR = ROOT / "data" / "wmdr2"


def run(command: list[str], *, env: dict[str, str] | None = None, check: bool = True) -> int:
    print("+", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env, check=check)
    return result.returncode


def venv_tools() -> tuple[Path, Path, str]:
    if sys.version_info < (3, 12):
        raise RuntimeError(
            f"Python 3.12+ is required for this PoC; current interpreter is {sys.version.split()[0]}"
        )

    if sys.prefix == sys.base_prefix:
        raise RuntimeError(
            "No Python virtual environment is active.\n"
            "Activate it first with:\n"
            "  source .venv/bin/activate"
        )

    # IMPORTANT: do not Path.resolve() these paths.  On Ubuntu the venv Python
    # is normally a symlink to /usr/bin/pythonX.Y; resolving it would make a
    # perfectly valid venv look like the system interpreter.
    venv_dir = Path(sys.prefix)
    bin_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
    python_exe = bin_dir / ("python.exe" if os.name == "nt" else "python")
    pygeoapi_cli = bin_dir / ("pygeoapi.exe" if os.name == "nt" else "pygeoapi")

    if not python_exe.exists():
        # sys.executable is still safe to use inside an active venv; this is a
        # fallback for unusual virtual-environment layouts.
        python_exe = Path(sys.executable)

    if not pygeoapi_cli.is_file():
        raise RuntimeError(
            "pygeoapi is not installed in the active project virtual environment.\n"
            "Install the catalogue requirements with:\n"
            "  python -m pip install -r catalogue/requirements.txt"
        )

    try:
        version = metadata.version("pygeoapi")
    except metadata.PackageNotFoundError as exc:
        raise RuntimeError(
            "The pygeoapi command exists in the venv, but the Python package is not importable there.\n"
            "Reinstall with:\n"
            "  python -m pip install -r catalogue/requirements.txt"
        ) from exc

    return python_exe, pygeoapi_cli, version


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local WIGOS pygeoapi catalogue service.")
    parser.add_argument(
        "--no-rebuild",
        action="store_true",
        help="Do not rebuild the TinyDB catalogue before starting pygeoapi.",
    )
    args = parser.parse_args()

    try:
        python_exe, pygeoapi_cli, version = venv_tools()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Virtualenv: {Path(sys.prefix)}")
    print(f"Python:     {python_exe} ({sys.version.split()[0]})")
    print(f"pygeoapi:   {pygeoapi_cli} ({version})")

    if not args.no_rebuild:
        if SOURCE_DIR.exists() and any(SOURCE_DIR.glob("*.json")):
            run([str(python_exe), "scripts/build_catalogue.py", "--input", "data/wmdr2"])
        elif not DB.exists():
            print(
                "No cached WMDR2 examples or catalogue found. First run:\n"
                "  python scripts/rebuild_catalogue.py",
                file=sys.stderr,
            )
            return 2

    if not DB.exists():
        print(f"Catalogue database not found: {DB}", file=sys.stderr)
        return 2

    env = os.environ.copy()
    env.setdefault("PYGEOAPI_CONFIG", str(CONFIG))
    env.setdefault("PYGEOAPI_OPENAPI", str(OPENAPI))
    env.setdefault("PYGEOAPI_SERVER_URL", "http://localhost:5000")
    env.setdefault("WIGOS_CATALOGUE_DB", str(DB))
    env.setdefault("PORT", "5000")

    run(
        [str(pygeoapi_cli), "openapi", "generate", str(CONFIG), "--output-file", str(OPENAPI)],
        env=env,
    )

    print("Starting pygeoapi at http://localhost:5000", flush=True)
    return run([str(pygeoapi_cli), "serve"], env=env, check=False)


if __name__ == "__main__":
    raise SystemExit(main())
