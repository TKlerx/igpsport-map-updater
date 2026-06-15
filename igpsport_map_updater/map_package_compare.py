"""Compare iGPSPORT map packages and highlight map identity drift."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .generate_maps_csv import parse_filename
from .map_semantics import MapsforgeSemantics, ZoomInterval, read_mapsforge_semantics


BASE36_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ZOOM = 2**13
METERS_PER_DEGREE_LAT = 111_320.0


@dataclass(frozen=True)
class MapInfo:
    filename: str
    path: Path
    size: int
    filename_key: tuple[str, str, str]
    data_key: tuple[str, str, str]
    filename_bbox: tuple[float, float, float, float]
    header: MapsforgeSemantics


def _base36_decode(value: str) -> int:
    result = 0
    for char in value.upper():
        result = result * 36 + BASE36_CHARS.index(char)
    return result


def _to_base36(value: int, length: int) -> str:
    value = max(0, value)
    result = ""
    for _ in range(length):
        result = BASE36_CHARS[value % 36] + result
        value //= 36
    return result


def _tile_x_to_lon(x: int) -> float:
    return (x / ZOOM) * 360.0 - 180.0


def _tile_y_to_lat(y: int) -> float:
    n = math.pi * (1.0 - 2.0 * y / ZOOM)
    return math.degrees(math.atan(math.sinh(n)))


def _lon_to_tile_x(lon: float) -> int:
    return math.floor(((lon + 180.0) / 360.0) * ZOOM)


def _lat_to_tile_y(lat: float) -> int:
    lat_rad = math.radians(lat)
    return math.floor(
        ((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0)
        * ZOOM
    )


def filename_bbox(geocode: str) -> tuple[float, float, float, float]:
    """Return bbox as (min_lat, min_lon, max_lat, max_lon)."""
    min_lon_x = _base36_decode(geocode[0:3])
    max_lat_y = _base36_decode(geocode[3:6])
    lon_span = _base36_decode(geocode[6:9]) + 1
    lat_span = _base36_decode(geocode[9:12]) + 1
    return (
        _tile_y_to_lat(max_lat_y + lat_span),
        _tile_x_to_lon(min_lon_x),
        _tile_y_to_lat(max_lat_y),
        _tile_x_to_lon(min_lon_x + lon_span),
    )


def geocode_from_bbox(bbox: tuple[float, float, float, float]) -> str:
    min_lat, min_lon, max_lat, max_lon = bbox
    x_start = _lon_to_tile_x(min_lon)
    y_start = _lat_to_tile_y(max_lat)
    x_end = _lon_to_tile_x(max_lon)
    y_end = _lat_to_tile_y(min_lat)
    return (
        _to_base36(x_start, 3)
        + _to_base36(y_start, 3)
        + _to_base36(x_end - x_start, 3)
        + _to_base36(y_end - y_start, 3)
    )


def max_bbox_delta_meters(
    baseline: tuple[float, float, float, float],
    candidate: tuple[float, float, float, float],
) -> tuple[float, float]:
    lat_delta = max(abs(baseline[0] - candidate[0]), abs(baseline[2] - candidate[2]))
    mid_lat = (baseline[0] + baseline[2] + candidate[0] + candidate[2]) / 4.0
    lon_delta = max(abs(baseline[1] - candidate[1]), abs(baseline[3] - candidate[3]))
    return (
        lat_delta * METERS_PER_DEGREE_LAT,
        lon_delta * METERS_PER_DEGREE_LAT * math.cos(math.radians(mid_lat)),
    )


def prepare_input(path: Path, work_dir: Path, label: str) -> Path:
    if path.is_dir():
        return path
    if path.is_file() and path.suffix.lower() == ".zip":
        target = work_dir / label
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path) as archive:
            archive.extractall(target)
        return target
    raise ValueError(f"Input is not a directory or ZIP file: {path}")


def read_package_maps(directory: Path) -> list[MapInfo]:
    maps: list[MapInfo] = []
    for path in sorted(directory.rglob("*.map")):
        parsed = parse_filename(path.name)
        if not parsed:
            continue
        header = read_mapsforge_semantics(path)
        filename_key = (
            parsed["country_code"],
            parsed["product_code"],
            parsed["geocode"],
        )
        data_geocode = geocode_from_bbox(header.bbox)
        maps.append(
            MapInfo(
                filename=path.name,
                path=path,
                size=path.stat().st_size,
                filename_key=filename_key,
                data_key=(parsed["country_code"], parsed["product_code"], data_geocode),
                filename_bbox=filename_bbox(parsed["geocode"]),
                header=header,
            )
        )
    return maps


def _index_unique(maps: list[MapInfo], key_name: str) -> tuple[dict[tuple[str, str, str], MapInfo], dict[str, list[str]]]:
    indexed: dict[tuple[str, str, str], MapInfo] = {}
    duplicates: dict[str, list[str]] = {}
    for item in maps:
        key = getattr(item, key_name)
        label = "/".join(key)
        if key in indexed:
            duplicates.setdefault(label, [indexed[key].filename]).append(item.filename)
        else:
            indexed[key] = item
    return indexed, duplicates


def _tag_diff(baseline: tuple[str, ...], candidate: tuple[str, ...]) -> dict[str, list[str]]:
    baseline_set = set(baseline)
    candidate_set = set(candidate)
    return {
        "added": sorted(candidate_set - baseline_set),
        "removed": sorted(baseline_set - candidate_set),
    }


def _zoom_intervals(value: tuple[ZoomInterval, ...]) -> list[dict[str, int]]:
    return [asdict(item) for item in value]


def compare_matched_maps(baseline: MapInfo, candidate: MapInfo) -> dict[str, Any]:
    lat_delta_m, lon_delta_m = max_bbox_delta_meters(baseline.header.bbox, candidate.header.bbox)
    poi_tags = _tag_diff(baseline.header.poi_tags, candidate.header.poi_tags)
    way_tags = _tag_diff(baseline.header.way_tags, candidate.header.way_tags)

    differences: dict[str, Any] = {
        "baseline_filename": baseline.filename,
        "candidate_filename": candidate.filename,
        "size": {
            "baseline": baseline.size,
            "candidate": candidate.size,
            "delta": candidate.size - baseline.size,
            "ratio": round(candidate.size / baseline.size, 4) if baseline.size else None,
        },
        "bbox": {
            "baseline": baseline.header.bbox,
            "candidate": candidate.header.bbox,
            "max_lat_delta_m": round(lat_delta_m, 1),
            "max_lon_delta_m": round(lon_delta_m, 1),
        },
        "filename_geocode": {
            "baseline": baseline.filename_key[2],
            "candidate": candidate.filename_key[2],
        },
        "data_geocode": {
            "baseline": baseline.data_key[2],
            "candidate": candidate.data_key[2],
        },
    }

    header_fields = {}
    for field in (
        "file_version",
        "tile_size",
        "projection",
        "flags",
        "map_start_position",
        "start_zoom",
        "language",
    ):
        baseline_value = getattr(baseline.header, field)
        candidate_value = getattr(candidate.header, field)
        if baseline_value != candidate_value:
            header_fields[field] = {
                "baseline": baseline_value,
                "candidate": candidate_value,
            }

    if baseline.header.zoom_intervals != candidate.header.zoom_intervals:
        header_fields["zoom_intervals"] = {
            "baseline": _zoom_intervals(baseline.header.zoom_intervals),
            "candidate": _zoom_intervals(candidate.header.zoom_intervals),
        }

    if header_fields:
        differences["header_fields"] = header_fields
    if poi_tags["added"] or poi_tags["removed"]:
        differences["poi_tags"] = poi_tags
    if way_tags["added"] or way_tags["removed"]:
        differences["way_tags"] = way_tags

    return differences


def package_identity_drift(maps: list[MapInfo]) -> list[dict[str, Any]]:
    drift = []
    for item in maps:
        if item.filename_key != item.data_key:
            lat_delta_m, lon_delta_m = max_bbox_delta_meters(item.filename_bbox, item.header.bbox)
            drift.append(
                {
                    "filename": item.filename,
                    "filename_key": item.filename_key,
                    "data_key": item.data_key,
                    "filename_vs_header_max_lat_delta_m": round(lat_delta_m, 1),
                    "filename_vs_header_max_lon_delta_m": round(lon_delta_m, 1),
                }
            )

    return sorted(drift, key=lambda item: item["filename"])


def compare_packages(baseline_maps: list[MapInfo], candidate_maps: list[MapInfo]) -> dict[str, Any]:
    baseline_by_filename, baseline_filename_duplicates = _index_unique(baseline_maps, "filename_key")
    candidate_by_filename, candidate_filename_duplicates = _index_unique(candidate_maps, "filename_key")
    baseline_by_data, baseline_data_duplicates = _index_unique(baseline_maps, "data_key")
    candidate_by_data, candidate_data_duplicates = _index_unique(candidate_maps, "data_key")

    filename_baseline_keys = set(baseline_by_filename)
    filename_candidate_keys = set(candidate_by_filename)
    data_baseline_keys = set(baseline_by_data)
    data_candidate_keys = set(candidate_by_data)

    matched_by_data = []
    for key in sorted(data_baseline_keys & data_candidate_keys):
        matched_by_data.append(
            {
                "key": key,
                "differences": compare_matched_maps(baseline_by_data[key], candidate_by_data[key]),
            }
        )

    return {
        "summary": {
            "baseline_count": len(baseline_maps),
            "candidate_count": len(candidate_maps),
            "baseline_total_size": sum(item.size for item in baseline_maps),
            "candidate_total_size": sum(item.size for item in candidate_maps),
            "filename_identity_matches": len(filename_baseline_keys & filename_candidate_keys),
            "data_identity_matches": len(data_baseline_keys & data_candidate_keys),
        },
        "duplicates": {
            "baseline_filename_keys": baseline_filename_duplicates,
            "candidate_filename_keys": candidate_filename_duplicates,
            "baseline_data_keys": baseline_data_duplicates,
            "candidate_data_keys": candidate_data_duplicates,
        },
        "filename_identity": {
            "missing_candidate": sorted(filename_baseline_keys - filename_candidate_keys),
            "missing_baseline": sorted(filename_candidate_keys - filename_baseline_keys),
        },
        "data_identity": {
            "missing_candidate": sorted(data_baseline_keys - data_candidate_keys),
            "missing_baseline": sorted(data_candidate_keys - data_baseline_keys),
            "matched": matched_by_data,
        },
        "baseline_identity_drift": package_identity_drift(baseline_maps),
        "candidate_identity_drift": package_identity_drift(candidate_maps),
    }


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, ZoomInterval):
        return asdict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _format_key(key: tuple[str, str, str]) -> str:
    return "/".join(key)


def print_text_report(report: dict[str, Any], verbose: bool = False) -> None:
    summary = report["summary"]
    print("Summary")
    print(f"  Baseline maps:  {summary['baseline_count']} ({summary['baseline_total_size']} bytes)")
    print(f"  Candidate maps: {summary['candidate_count']} ({summary['candidate_total_size']} bytes)")
    print(f"  Filename identity matches: {summary['filename_identity_matches']}")
    print(f"  Data/header identity matches: {summary['data_identity_matches']}")
    print()

    filename_identity = report["filename_identity"]
    print("Filename Identity")
    print(f"  Missing candidate: {len(filename_identity['missing_candidate'])}")
    for key in filename_identity["missing_candidate"]:
        print(f"    - {_format_key(key)}")
    print(f"  Missing baseline: {len(filename_identity['missing_baseline'])}")
    for key in filename_identity["missing_baseline"]:
        print(f"    - {_format_key(key)}")
    print()

    data_identity = report["data_identity"]
    print("Data/Header Identity")
    print(f"  Missing candidate: {len(data_identity['missing_candidate'])}")
    for key in data_identity["missing_candidate"]:
        print(f"    - {_format_key(key)}")
    print(f"  Missing baseline: {len(data_identity['missing_baseline'])}")
    for key in data_identity["missing_baseline"]:
        print(f"    - {_format_key(key)}")
    print()

    for label, field in (
        ("Baseline Filename vs Header Drift", "baseline_identity_drift"),
        ("Candidate Filename vs Header Drift", "candidate_identity_drift"),
    ):
        print(label)
        if not report[field]:
            print("  none")
        for item in report[field]:
            print(
                "  "
                f"{item['filename']}: filename={_format_key(item['filename_key'])} "
                f"header={_format_key(item['data_key'])} "
                f"delta(lat={item['filename_vs_header_max_lat_delta_m']}m, "
                f"lon={item['filename_vs_header_max_lon_delta_m']}m)"
            )
        print()

    print("Matched Data/Header Maps")
    if not data_identity["matched"]:
        print("  none")
    for match in data_identity["matched"]:
        differences = match["differences"]
        size = differences["size"]
        bbox = differences["bbox"]
        print(
            f"  {_format_key(match['key'])}: "
            f"{differences['baseline_filename']} -> {differences['candidate_filename']}; "
            f"size_delta={size['delta']} ratio={size['ratio']}; "
            f"bbox_delta(lat={bbox['max_lat_delta_m']}m, lon={bbox['max_lon_delta_m']}m)"
        )
        if verbose:
            for field in ("header_fields", "poi_tags", "way_tags"):
                if field in differences:
                    print(f"    {field}: {differences[field]}")


def has_differences(report: dict[str, Any]) -> bool:
    if any(report["duplicates"].values()):
        return True
    if report["filename_identity"]["missing_candidate"]:
        return True
    if report["filename_identity"]["missing_baseline"]:
        return True
    if report["data_identity"]["missing_candidate"]:
        return True
    if report["data_identity"]["missing_baseline"]:
        return True
    if report["baseline_identity_drift"]:
        return True
    if report["candidate_identity_drift"]:
        return True

    for match in report["data_identity"]["matched"]:
        differences = match["differences"]
        if differences["size"]["delta"] != 0:
            return True
        if differences["bbox"]["max_lat_delta_m"] != 0:
            return True
        if differences["bbox"]["max_lon_delta_m"] != 0:
            return True
        for field in ("header_fields", "poi_tags", "way_tags"):
            if field in differences:
                return True

    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare two iGPSPORT map folders or ZIP packages."
    )
    parser.add_argument("baseline", help="Baseline package ZIP or directory")
    parser.add_argument("candidate", help="Candidate package ZIP or directory")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include detailed tag/header differences for matched data identities",
    )
    parser.add_argument(
        "--work-dir",
        help="Optional extraction work directory. A temp directory is used by default.",
    )
    parser.add_argument(
        "--keep-work-dir",
        action="store_true",
        help="Do not delete the temporary extraction work directory",
    )
    parser.add_argument(
        "--no-fail",
        action="store_true",
        help="Always exit 0 after writing the report",
    )
    args = parser.parse_args()

    auto_work_dir: Path | None = None
    try:
        if args.work_dir:
            work_dir = Path(args.work_dir)
            work_dir.mkdir(parents=True, exist_ok=True)
        else:
            work_dir = Path(tempfile.mkdtemp(prefix="igpsport-map-compare-"))
            auto_work_dir = work_dir

        baseline_dir = prepare_input(Path(args.baseline), work_dir, "baseline")
        candidate_dir = prepare_input(Path(args.candidate), work_dir, "candidate")
        report = compare_packages(read_package_maps(baseline_dir), read_package_maps(candidate_dir))

        if args.json:
            print(json.dumps(report, indent=2, default=_json_default))
        else:
            print_text_report(report, verbose=args.verbose)
            if args.keep_work_dir or args.work_dir:
                print(f"Work dir: {work_dir}")
        if has_differences(report) and not args.no_fail:
            sys.exit(1)
    except (OSError, ValueError, zipfile.BadZipFile, UnicodeDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
    finally:
        if auto_work_dir and not args.keep_work_dir:
            shutil.rmtree(auto_work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
