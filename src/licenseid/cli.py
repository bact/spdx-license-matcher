# SPDX-FileCopyrightText: 2026 SPDX
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import json
import os
import sys
from pathlib import Path
from typing import Optional

import click

from licenseid.matcher import AggregatedLicenseMatcher
from licenseid.database import LicenseDatabase


def get_default_db_path() -> str:
    """Get the default path for the license database."""
    home = Path.home()
    db_dir = home / ".local" / "share" / "licenseid"
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / "licenses.db")


@click.group()
def cli() -> None:
    """SPDX License ID matcher tool."""
    pass


@cli.command()
@click.option("--db", help="Path to the license database.")
def update(db: Optional[str]) -> None:
    """Update the license database from remote sources."""
    db_path = db or get_default_db_path()
    database = LicenseDatabase(db_path)
    database.update_from_remote()
    click.echo(f"Database updated at {db_path}")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True), required=False)
@click.option("--text", help="License text to match.")
@click.option("--db", help="Path to the license database.")
@click.option("--json", "json_output", is_flag=True, help="Output results in JSON format.")
@click.option("--threshold", type=float, default=0.0, help="Minimum score threshold.")
def match(
    input_file: Optional[str],
    text: Optional[str],
    db: Optional[str],
    json_output: bool,
    threshold: float
) -> None:
    """Identify license text and return the closest matched SPDX License ID."""
    db_path = db or get_default_db_path()
    
    if not os.path.exists(db_path):
        click.echo(f"Error: Database not found at {db_path}. Please run 'licenseid update' first.", err=True)
        sys.exit(1)

    license_text = ""
    if input_file:
        with open(input_file, "r", encoding="utf-8") as f:
            license_text = f.read()
    elif text:
        license_text = text
    else:
        # Try reading from stdin
        if not sys.stdin.isatty():
            license_text = sys.stdin.read()
        else:
            click.echo("Error: No input text provided. Provide a file, --text, or pipe to stdin.", err=True)
            sys.exit(1)

    matcher = AggregatedLicenseMatcher(db_path)
    results = matcher.match(license_text)

    # Filter by threshold
    results = [r for r in results if r["score"] >= threshold]

    if json_output:
        click.echo(json.dumps(results, indent=2))
    else:
        if not results:
            click.echo("ERROR: No matching license found.", err=True)
            sys.exit(1)
        
        # Standard output: line-delimited, KEY=VALUE
        for r in results:
            click.echo(f"LICENSEID={r['licenseId']} SCORE={r['score']:.4f}")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
