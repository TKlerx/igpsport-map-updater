"""Inspect iGPSPORT filename geocodes against Mapsforge header bounding boxes."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from igpsport_map_updater.map_semantics import read_mapsforge_semantics


BASE36_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ZOOM = 2**13
METERS_PER_DEGREE_LAT = 111_320.0


def base36_to_int(value: str) -> int:
    result = 0
    for char in value.upper():
        digit = BASE36_CHARS.index(char)
        result = result * 36 + digit
    return result


def tile_x_to_lon(x: int) -> float:
    return (x / ZOOM) * 360.0 - 180.0


def tile_y_to_lat(y: int) -> float:
    n = math.pi * (1.0 - 2.0 * y / ZOOM)
    return math.degrees(math.atan(math.sinh(n)))


def filename_bbox(filename: str) -> tuple[float, float, float, float]:
    geocode = Path(filename).stem[12:24]
    min_lon_x = base36_to_int(geocode[0:3])
    max_lat_y = base36_to_int(geocode[3:6])
    lon_span = base36_to_int(geocode[6:9]) + 1
    lat_span = base36_to_int(geocode[9:12]) + 1

    return (
        tile_y_to_lat(max_lat_y + lat_span),
        tile_x_to_lon(min_lon_x),
        tile_y_to_lat(max_lat_y),
        tile_x_to_lon(min_lon_x + lon_span),
    )


def max_delta_meters(
    header_bbox: tuple[float, float, float, float],
    geocode_bbox: tuple[float, float, float, float],
) -> tuple[float, float]:
    lat_delta = max(
        abs(header_bbox[0] - geocode_bbox[0]),
        abs(header_bbox[2] - geocode_bbox[2]),
    )
    mid_lat = (geocode_bbox[0] + geocode_bbox[2]) / 2.0
    lon_delta = max(
        abs(header_bbox[1] - geocode_bbox[1]),
        abs(header_bbox[3] - geocode_bbox[3]),
    )
    return (
        lat_delta * METERS_PER_DEGREE_LAT,
        lon_delta * METERS_PER_DEGREE_LAT * math.cos(math.radians(mid_lat)),
    )


def inspect(path: Path) -> dict[str, object]:
    header_bbox = read_mapsforge_semantics(path).bbox
    geocode_bbox = filename_bbox(path.name)
    lat_delta_m, lon_delta_m = max_delta_meters(header_bbox, geocode_bbox)
    return {
        "path": path,
        "header_bbox": header_bbox,
        "geocode_bbox": geocode_bbox,
        "lat_delta_m": lat_delta_m,
        "lon_delta_m": lon_delta_m,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare map header bboxes with the bbox encoded in iGPSPORT filenames."
    )
    parser.add_argument("paths", nargs="+", help="Map files or directories to inspect")
    parser.add_argument(
        "--pattern",
        default="*.map",
        help="Glob used when a path is a directory (default: *.map)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum rows to print after sorting by filename (default: all)",
    )
    args = parser.parse_args()

    map_paths: list[Path] = []
    for raw_path in args.paths:
        path = Path(raw_path)
        if path.is_dir():
            map_paths.extend(sorted(path.glob(args.pattern)))
        else:
            map_paths.append(path)

    rows = [inspect(path) for path in sorted(map_paths)]
    if args.limit:
        rows = rows[: args.limit]

    for row in rows:
        header = tuple(round(value, 6) for value in row["header_bbox"])
        geocode = tuple(round(value, 6) for value in row["geocode_bbox"])
        print(
            f"{row['path'].name}: "
            f"lat_delta_m={row['lat_delta_m']:.1f} "
            f"lon_delta_m={row['lon_delta_m']:.1f} "
            f"header={header} geocode={geocode}"
        )


if __name__ == "__main__":
    main()
