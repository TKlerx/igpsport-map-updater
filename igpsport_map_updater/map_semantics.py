"""Semantic comparison helpers for Mapsforge map outputs."""

import argparse
import json
import struct
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


MAGIC = b"mapsforge binary OSM"


@dataclass(frozen=True)
class ZoomInterval:
    base_zoom: int
    min_zoom: int
    max_zoom: int


@dataclass(frozen=True)
class MapsforgeSemantics:
    file_version: int
    bbox: tuple[float, float, float, float]
    tile_size: int
    projection: str
    flags: dict[str, bool]
    map_start_position: tuple[float, float] | None
    start_zoom: int | None
    language: str | None
    poi_tags: tuple[str, ...]
    way_tags: tuple[str, ...]
    zoom_intervals: tuple[ZoomInterval, ...]


class MapSemanticError(ValueError):
    """Raised when a map cannot be read as a Mapsforge semantic fixture."""


def _read_exact(handle, size):
    data = handle.read(size)
    if len(data) != size:
        raise MapSemanticError("Map ended before semantic header fields were complete")
    return data


def _read_var_uint(handle):
    result = 0
    shift = 0
    while True:
        byte = handle.read(1)
        if not byte:
            raise MapSemanticError("Map ended inside variable-length integer")
        value = byte[0]
        result |= (value & 0x7F) << shift
        if (value & 0x80) == 0:
            return result
        shift += 7


def _read_utf8(handle):
    length = _read_var_uint(handle)
    if length == 0:
        return ""
    return _read_exact(handle, length).decode("utf-8", errors="strict")


def read_mapsforge_semantics(path):
    """Read map-reader-visible Mapsforge header semantics from a `.map` file."""
    with Path(path).open("rb") as handle:
        magic = _read_exact(handle, len(MAGIC))
        if magic != MAGIC:
            raise MapSemanticError("Not a Mapsforge map file")

        _header_size = struct.unpack(">I", _read_exact(handle, 4))[0]
        file_version = struct.unpack(">I", _read_exact(handle, 4))[0]
        _file_size = struct.unpack(">Q", _read_exact(handle, 8))[0]
        _date_created = struct.unpack(">Q", _read_exact(handle, 8))[0]

        min_lat = struct.unpack(">i", _read_exact(handle, 4))[0] / 1_000_000.0
        min_lon = struct.unpack(">i", _read_exact(handle, 4))[0] / 1_000_000.0
        max_lat = struct.unpack(">i", _read_exact(handle, 4))[0] / 1_000_000.0
        max_lon = struct.unpack(">i", _read_exact(handle, 4))[0] / 1_000_000.0
        bbox = (min_lat, min_lon, max_lat, max_lon)

        tile_size = struct.unpack(">H", _read_exact(handle, 2))[0]
        projection = _read_utf8(handle)
        flags_byte = _read_exact(handle, 1)[0]
        flags = {
            "debug_info": bool(flags_byte & 0x80),
            "map_start_position": bool(flags_byte & 0x40),
            "start_zoom": bool(flags_byte & 0x20),
            "language_preference": bool(flags_byte & 0x10),
            "comment": bool(flags_byte & 0x08),
            "created_by": bool(flags_byte & 0x04),
        }

        map_start_position = None
        if flags["map_start_position"]:
            start_lat = struct.unpack(">i", _read_exact(handle, 4))[0] / 1_000_000.0
            start_lon = struct.unpack(">i", _read_exact(handle, 4))[0] / 1_000_000.0
            map_start_position = (start_lat, start_lon)

        start_zoom = None
        if flags["start_zoom"]:
            start_zoom = _read_exact(handle, 1)[0]

        language = None
        if flags["language_preference"]:
            language = _read_utf8(handle)

        if flags["comment"]:
            _read_utf8(handle)

        if flags["created_by"]:
            _read_utf8(handle)

        poi_tags = tuple(_read_utf8(handle) for _ in range(struct.unpack(">H", _read_exact(handle, 2))[0]))
        way_tags = tuple(_read_utf8(handle) for _ in range(struct.unpack(">H", _read_exact(handle, 2))[0]))

        zoom_intervals = []
        for _ in range(_read_exact(handle, 1)[0]):
            zoom_intervals.append(
                ZoomInterval(
                    base_zoom=_read_exact(handle, 1)[0],
                    min_zoom=_read_exact(handle, 1)[0],
                    max_zoom=_read_exact(handle, 1)[0],
                )
            )
            _read_exact(handle, 8)
            _read_exact(handle, 8)

    return MapsforgeSemantics(
        file_version=file_version,
        bbox=bbox,
        tile_size=tile_size,
        projection=projection,
        flags=flags,
        map_start_position=map_start_position,
        start_zoom=start_zoom,
        language=language,
        poi_tags=poi_tags,
        way_tags=way_tags,
        zoom_intervals=tuple(zoom_intervals),
    )


def compare_mapsforge_semantics(baseline_map, candidate_map):
    """Return semantic mismatches between baseline and candidate Mapsforge maps."""
    baseline = read_mapsforge_semantics(baseline_map)
    candidate = read_mapsforge_semantics(candidate_map)
    mismatches = []

    for field in (
        "file_version",
        "bbox",
        "tile_size",
        "projection",
        "flags",
        "map_start_position",
        "start_zoom",
        "language",
        "poi_tags",
        "way_tags",
        "zoom_intervals",
    ):
        baseline_value = getattr(baseline, field)
        candidate_value = getattr(candidate, field)
        if baseline_value != candidate_value:
            mismatches.append(
                {
                    "field": field,
                    "baseline": baseline_value,
                    "candidate": candidate_value,
                }
            )

    return mismatches


def _json_default(value):
    if isinstance(value, ZoomInterval):
        return asdict(value)
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def main():
    parser = argparse.ArgumentParser(
        description="Compare Mapsforge maps for baseline-vs-optimized semantic equivalence."
    )
    parser.add_argument("baseline_map", help="Baseline map generated without optimization")
    parser.add_argument("candidate_map", help="Candidate map generated with optimization")
    parser.add_argument("--json", action="store_true", help="Print mismatch details as JSON")
    args = parser.parse_args()

    try:
        mismatches = compare_mapsforge_semantics(args.baseline_map, args.candidate_map)
    except (OSError, MapSemanticError, UnicodeDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    if mismatches:
        if args.json:
            print(json.dumps(mismatches, indent=2, default=_json_default))
        else:
            print("Mapsforge semantic comparison failed:")
            for mismatch in mismatches:
                print(f"- {mismatch['field']}: {mismatch['baseline']!r} != {mismatch['candidate']!r}")
        sys.exit(1)

    print("Mapsforge semantic comparison passed")


if __name__ == "__main__":
    main()
