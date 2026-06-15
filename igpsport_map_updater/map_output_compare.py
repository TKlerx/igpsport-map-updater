"""Folder-level Mapsforge output comparison helpers."""

import argparse
import json
import sys
from pathlib import Path

from .map_semantics import MapSemanticError, compare_mapsforge_semantics
from .package_maps import map_key, parsed_map_files


class OutputComparisonError(ValueError):
    """Raised when output folders cannot be compared."""


def _indexed_maps(directory):
    maps = {}
    duplicates = []
    for parsed in parsed_map_files(directory):
        key = map_key(parsed)
        if key in maps:
            duplicates.append(key)
        maps[key] = parsed

    if duplicates:
        labels = ", ".join("/".join(key) for key in duplicates)
        raise OutputComparisonError(f"Duplicate tile identities in {directory}: {labels}")

    return maps


def compare_output_dirs(baseline_dir, candidate_dir):
    """Compare every matched baseline/candidate map by tile identity."""
    baseline = _indexed_maps(baseline_dir)
    candidate = _indexed_maps(candidate_dir)
    results = []

    baseline_keys = set(baseline)
    candidate_keys = set(candidate)

    for key in sorted(baseline_keys - candidate_keys):
        results.append(
            {
                "key": key,
                "status": "missing-candidate",
                "baseline": str(baseline[key]["path"]),
                "candidate": None,
                "mismatches": [],
            }
        )

    for key in sorted(candidate_keys - baseline_keys):
        results.append(
            {
                "key": key,
                "status": "missing-baseline",
                "baseline": None,
                "candidate": str(candidate[key]["path"]),
                "mismatches": [],
            }
        )

    for key in sorted(baseline_keys & candidate_keys):
        baseline_path = baseline[key]["path"]
        candidate_path = candidate[key]["path"]
        mismatches = compare_mapsforge_semantics(baseline_path, candidate_path)
        results.append(
            {
                "key": key,
                "status": "mismatch" if mismatches else "match",
                "baseline": str(baseline_path),
                "candidate": str(candidate_path),
                "mismatches": mismatches,
            }
        )

    return results


def has_failures(results):
    return any(result["status"] != "match" for result in results)


def _json_default(value):
    if isinstance(value, tuple):
        return list(value)
    return str(value)


def main():
    parser = argparse.ArgumentParser(
        description="Compare baseline and candidate map output folders semantically."
    )
    parser.add_argument("baseline_dir", help="Directory containing baseline .map outputs")
    parser.add_argument("candidate_dir", help="Directory containing candidate .map outputs")
    parser.add_argument("--json", action="store_true", help="Print machine-readable results")
    args = parser.parse_args()

    try:
        results = compare_output_dirs(Path(args.baseline_dir), Path(args.candidate_dir))
    except (OSError, OutputComparisonError, MapSemanticError, UnicodeDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    if args.json:
        print(json.dumps(results, indent=2, default=_json_default))
    else:
        for result in results:
            key = "/".join(result["key"])
            print(f"{result['status']}: {key}")
            for mismatch in result["mismatches"]:
                print(f"  - {mismatch['field']}: {mismatch['baseline']!r} != {mismatch['candidate']!r}")

    sys.exit(1 if has_failures(results) else 0)


if __name__ == "__main__":
    main()
