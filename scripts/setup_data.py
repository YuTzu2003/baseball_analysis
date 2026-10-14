"""Prepare the local CPBL source data and rebuild the SQLite database."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SOURCE_REPOSITORY = "https://github.com/ldkrsi/cpbl-opendata.git"


def source_is_ready(source: Path) -> bool:
    root = source / "CPBL"
    return (
        (root / "battings").is_dir()
        and (root / "pitchings").is_dir()
        and (root / "standings.csv").is_file()
        and any((root / "battings").glob("*.csv"))
    )


def download_source(source: Path) -> None:
    source.parent.mkdir(parents=True, exist_ok=True)
    if source.exists() and any(source.iterdir()):
        raise SystemExit(
            f"Source directory exists but is incomplete: {source}\n"
            "Remove it or fix it, then run this command again."
        )
    subprocess.run(["git", "clone", "--depth", "1", SOURCE_REPOSITORY, str(source)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download CPBL data if needed and build local SQLite.")
    parser.add_argument("--source", type=Path, default=Path("data/sources/cpbl-opendata"))
    parser.add_argument("--database", type=Path, default=Path("data/cpbl.sqlite"))
    parser.add_argument("--download", action="store_true", help="Download the source repository when it is missing.")
    args = parser.parse_args()

    if not source_is_ready(args.source):
        if not args.download:
            raise SystemExit(
                f"CPBL source data not found at {args.source}.\n"
                "Run again with --download, or place the source repository there manually."
            )
        print(f"Downloading CPBL source data into {args.source}...")
        download_source(args.source)

    subprocess.run(
        [sys.executable, "scripts/import_cpbl_sqlite.py", "--source", str(args.source), "--database", str(args.database)],
        check=True,
    )


if __name__ == "__main__":
    main()
