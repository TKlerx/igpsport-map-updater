#!/usr/bin/env python3
"""
Package generated iGPSPORT map files with sharing README and manifest.

The packager matches generated output files back to the original input files by
country code, product code, and geocode. The date may differ because generated
maps use the source OpenStreetMap date.

Usage:
    python package_maps.py input
    python package_maps.py input --output-dir output --package-dir packages
    python package_maps.py input --label switzerland
"""

import argparse
import os
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .generate_maps_csv import parse_filename
from .map_md5_cfg import build_updated_map_md5_cfg

DEFAULT_OUTPUT_DIR = "output"
DEFAULT_PACKAGE_DIR = "packages"
DEFAULT_README = "MAP_PACKAGE_README.txt"
DEFAULT_PACKAGE_PREFIX = "IGPSport300-800"
IGS630_PACKAGE_PREFIX = "IGPSport-iGS630"


COUNTRY_LABELS = {
    "AT": "Austria",
    "BE": "Belgium",
    "BR": "Brazil",
    "CH": "Switzerland",
    "CZ": "Czech-Republic",
    "DE": "Germany",
    "DK": "Denmark",
    "ES": "Spain",
    "FR": "France",
    "GB": "United-Kingdom",
    "GR": "Greece",
    "IT": "Italy",
    "NL": "Netherlands",
    "NO": "Norway",
    "PL": "Poland",
    "PT": "Portugal",
    "SE": "Sweden",
    "US": "United-States",
}


def parsed_map_files(directory):
    """Return parsed iGPSPORT .map files from a directory."""
    result = []
    for path in sorted(Path(directory).glob("*.map")):
        parsed = parse_filename(path.name)
        if parsed:
            parsed["path"] = path
            result.append(parsed)
    return result


def map_key(parsed):
    """Stable tile identity that survives generated date changes."""
    return parsed["country_code"], parsed["product_code"], parsed["geocode"]


def find_matching_outputs(input_maps, output_dir):
    """Find generated output maps matching the original input tile identities."""
    wanted = {map_key(parsed) for parsed in input_maps}
    matches = []

    for parsed in parsed_map_files(output_dir):
        if map_key(parsed) in wanted:
            matches.append(parsed)

    return matches


def country_label(country_codes):
    """Create a package label from one or more country codes."""
    codes = sorted(country_codes)
    if len(codes) == 1:
        code = codes[0]
        return COUNTRY_LABELS.get(code, code)

    return "Mixed-" + "-".join(codes)


def default_package_prefix():
    """Return the default ZIP prefix for the active compatibility profile."""
    tag_profile = os.environ.get("MAP_TAG_PROFILE", "").strip().lower()
    if tag_profile in {"igs630", "strict", "compat"}:
        return IGS630_PACKAGE_PREFIX

    return DEFAULT_PACKAGE_PREFIX


def package_name(input_maps, output_maps, label=None, prefix=None):
    """Derive a deterministic package filename."""
    countries = {parsed["country_code"] for parsed in input_maps}
    label_part = label or country_label(countries)
    prefix_part = prefix or default_package_prefix()
    return f"{prefix_part}-{label_part}.zip"


def git_commit():
    """Return the current short git commit when available."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"

    return completed.stdout.strip() or "unknown"


def build_manifest(input_maps, output_maps, package_filename, md5_cfg_path=None):
    """Build a reproducibility manifest for the ZIP."""
    country_counts = Counter(parsed["country_code"] for parsed in input_maps)
    lines = [
        "iGPSPORT map package manifest",
        f"Package: {package_filename}",
        f"Created UTC: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"Generator commit: {git_commit()}",
    ]

    if md5_cfg_path:
        lines.append(f"iGS630 MD5 cfg base: {md5_cfg_path}")

    lines.extend([
        "",
        "Input summary:",
    ])

    for country_code, count in sorted(country_counts.items()):
        lines.append(f"- {country_code}: {count} original map file(s)")

    lines.extend([
        "",
        "Included generated maps:",
    ])

    for parsed in sorted(output_maps, key=lambda item: item["filename"]):
        lines.append(f"- {parsed['filename']}")

    lines.extend([
        "",
        "Original input maps used for matching:",
    ])

    for parsed in sorted(input_maps, key=lambda item: item["filename"]):
        lines.append(f"- {parsed['filename']}")

    return "\n".join(lines) + "\n"


def create_package(input_maps, output_maps, readme_path, package_path, md5_cfg_path=None):
    """Create the ZIP package."""
    manifest = build_manifest(input_maps, output_maps, package_path.name, md5_cfg_path)

    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(readme_path, "README.txt")
        archive.writestr("MANIFEST.txt", manifest)

        for parsed in sorted(output_maps, key=lambda item: item["filename"]):
            archive.write(parsed["path"], parsed["filename"])

        if md5_cfg_path:
            archive.writestr(
                "map_md5_list.cfg",
                build_updated_map_md5_cfg(
                    md5_cfg_path,
                    [parsed["path"] for parsed in output_maps],
                ),
            )


def main():
    parser = argparse.ArgumentParser(
        description="Package generated iGPSPORT maps with README and manifest."
    )
    parser.add_argument(
        "input_dir",
        help="Directory containing the original input .map files used for generation",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory containing generated .map files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--package-dir",
        default=DEFAULT_PACKAGE_DIR,
        help=f"Directory for the generated ZIP package (default: {DEFAULT_PACKAGE_DIR})",
    )
    parser.add_argument(
        "--readme",
        default=DEFAULT_README,
        help=f"README template to include as README.txt (default: {DEFAULT_README})",
    )
    parser.add_argument(
        "--label",
        help="Override the package label, e.g. switzerland or brazil",
    )
    parser.add_argument(
        "--name",
        help="Override the full ZIP filename",
    )
    parser.add_argument(
        "--package-prefix",
        help=(
            f"Override the default ZIP prefix (default: {DEFAULT_PACKAGE_PREFIX}, "
            f"or {IGS630_PACKAGE_PREFIX} when MAP_TAG_PROFILE=igs630)"
        ),
    )
    parser.add_argument(
        "--md5-cfg",
        help=(
            "Optional iGS630 map_md5_list.cfg to refresh with generated map checksums "
            "and include in the ZIP"
        ),
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    package_dir = Path(args.package_dir)
    readme_path = Path(args.readme)
    md5_cfg_path = Path(args.md5_cfg) if args.md5_cfg else None

    if not input_dir.is_dir():
        print(f"Error: input directory does not exist: {input_dir}", file=sys.stderr)
        sys.exit(1)

    if not output_dir.is_dir():
        print(f"Error: output directory does not exist: {output_dir}", file=sys.stderr)
        sys.exit(1)

    if not readme_path.is_file():
        print(f"Error: README template does not exist: {readme_path}", file=sys.stderr)
        sys.exit(1)

    if md5_cfg_path and not md5_cfg_path.is_file():
        print(f"Error: MD5 cfg does not exist: {md5_cfg_path}", file=sys.stderr)
        sys.exit(1)

    input_maps = parsed_map_files(input_dir)
    if not input_maps:
        print(f"Error: no valid iGPSPORT input maps found in {input_dir}", file=sys.stderr)
        sys.exit(1)

    output_maps = find_matching_outputs(input_maps, output_dir)
    if not output_maps:
        print(
            "Error: no generated output maps matched the input country/product/geocode.",
            file=sys.stderr,
        )
        sys.exit(1)

    filename = args.name or package_name(
        input_maps,
        output_maps,
        args.label,
        args.package_prefix,
    )
    if not filename.lower().endswith(".zip"):
        filename += ".zip"

    package_dir.mkdir(parents=True, exist_ok=True)
    package_path = package_dir / filename

    create_package(input_maps, output_maps, readme_path, package_path, md5_cfg_path)

    print(f"Packaged {len(output_maps)} map file(s): {package_path}")


if __name__ == "__main__":
    main()
