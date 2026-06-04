#!/usr/bin/env python3
"""
Package an experimental BiNavi map update.

The package uses an official BiNavi folder as a template, preserves Router/
and non-standard map files, and replaces only the parseable main country map
with a generated map from output/.

Usage:
    uv run python package_binavi.py tmp/test-binavi/IT00
    uv run python package_binavi.py tmp/test-binavi/IT00 --label Italy
"""

import argparse
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .generate_maps_csv import parse_filename
from .package_maps import COUNTRY_LABELS, find_matching_outputs, git_commit, map_key, parsed_map_files

DEFAULT_OUTPUT_DIR = "output"
DEFAULT_PACKAGE_DIR = "packages"
DEFAULT_README = "BINAVI_EXPERIMENTAL_README.txt"


def binavi_maps_dir(base_dir):
    return Path(base_dir) / "Maps"


def binavi_router_dir(base_dir):
    return Path(base_dir) / "Router"


def parseable_binavi_maps(base_dir):
    """Return parseable BiNavi maps from the official package Maps folder."""
    return parsed_map_files(binavi_maps_dir(base_dir))


def main_binavi_map(base_dir):
    """Return the one parseable main map from a BiNavi package."""
    maps = parseable_binavi_maps(base_dir)
    if len(maps) != 1:
        raise ValueError(
            f"Expected exactly one parseable main map in {binavi_maps_dir(base_dir)}, found {len(maps)}"
        )

    return maps[0]


def binavi_package_label(main_map, label=None):
    if label:
        return label

    country_code = main_map["country_code"]
    return COUNTRY_LABELS.get(country_code, country_code)


def binavi_package_name(main_map, label=None):
    return f"IGPSport-BiNavi-{binavi_package_label(main_map, label)}-Experimental.zip"


def build_manifest(base_dir, main_map, replacement_map, package_filename):
    lines = [
        "iGPSPORT BiNavi experimental map package manifest",
        f"Package: {package_filename}",
        f"Created UTC: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"Generator commit: {git_commit()}",
        "",
        "Updated map:",
        f"- Original: Maps/{main_map['filename']}",
        f"- Replacement: Maps/{replacement_map['filename']}",
        "",
        "Preserved official package files:",
    ]

    for path in sorted(Path(base_dir).rglob("*")):
        if path.is_file():
            rel = path.relative_to(base_dir).as_posix()
            if rel == f"Maps/{main_map['filename']}":
                continue
            lines.append(f"- {rel}")

    lines.extend([
        "",
        "Limitations:",
        "- Router/*.rtd files are copied from the official package and are not regenerated.",
        "- Contour/overview map files are copied from the official package and are not regenerated.",
    ])

    return "\n".join(lines) + "\n"


def create_binavi_package(base_dir, replacement_map, readme_path, package_path, main_map=None):
    """Create a BiNavi ZIP preserving official package structure."""
    base_dir = Path(base_dir)
    main_map = main_map or main_binavi_map(base_dir)
    manifest = build_manifest(base_dir, main_map, replacement_map, package_path.name)

    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(readme_path, "README.txt")
        archive.writestr("MANIFEST.txt", manifest)

        for path in sorted(base_dir.rglob("*")):
            if not path.is_file():
                continue

            rel = path.relative_to(base_dir).as_posix()
            if rel == f"Maps/{main_map['filename']}":
                continue

            archive.write(path, rel)

        archive.write(replacement_map["path"], f"Maps/{replacement_map['filename']}")


def main():
    parser = argparse.ArgumentParser(
        description="Package an experimental BiNavi map update."
    )
    parser.add_argument(
        "base_dir",
        help="Official extracted BiNavi package folder containing Maps/ and Router/",
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
        help="Override package label, e.g. Italy",
    )
    parser.add_argument(
        "--name",
        help="Override full ZIP filename",
    )
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    output_dir = Path(args.output_dir)
    package_dir = Path(args.package_dir)
    readme_path = Path(args.readme)

    if not binavi_maps_dir(base_dir).is_dir():
        print(f"Error: missing BiNavi Maps folder: {binavi_maps_dir(base_dir)}", file=sys.stderr)
        sys.exit(1)

    if not binavi_router_dir(base_dir).is_dir():
        print(f"Error: missing BiNavi Router folder: {binavi_router_dir(base_dir)}", file=sys.stderr)
        sys.exit(1)

    if not output_dir.is_dir():
        print(f"Error: output directory does not exist: {output_dir}", file=sys.stderr)
        sys.exit(1)

    if not readme_path.is_file():
        print(f"Error: README template does not exist: {readme_path}", file=sys.stderr)
        sys.exit(1)

    try:
        main_map = main_binavi_map(base_dir)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    matches = find_matching_outputs([main_map], output_dir)
    if not matches:
        key = "/".join(map_key(main_map))
        print(f"Error: no generated output map matched BiNavi main map key {key}", file=sys.stderr)
        sys.exit(1)

    replacement_map = sorted(matches, key=lambda item: item["date"])[-1]
    filename = args.name or binavi_package_name(main_map, args.label)
    if not filename.lower().endswith(".zip"):
        filename += ".zip"

    package_dir.mkdir(parents=True, exist_ok=True)
    package_path = package_dir / filename
    create_binavi_package(base_dir, replacement_map, readme_path, package_path, main_map)

    print(f"Packaged experimental BiNavi map: {package_path}")
    print(f"  Replaced: Maps/{main_map['filename']}")
    print(f"  With:     Maps/{replacement_map['filename']}")
    print("  Preserved Router/ and non-standard Maps/*.map files from the official package.")


if __name__ == "__main__":
    main()
