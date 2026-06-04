#!/usr/bin/env python3
"""
Generate maps.csv from original iGPSport map files.

Parses iGPSport map filenames, decodes the geocode to a bounding box,
matches it against the Geofabrik region index, and generates a maps.csv
file with the correct PBF and polygon download URLs.

Usage:
    python generate_maps_csv.py <directory_with_original_maps>
    python generate_maps_csv.py <directory_with_original_maps> -o maps.csv

Example:
    python generate_maps_csv.py backup/
    python generate_maps_csv.py "C:\\Users\\me\\igpsport-maps\\original"
"""

import argparse
import json
import math
import os
import re
import sys
import urllib.request

GEOFABRIK_INDEX_URL = "https://download.geofabrik.de/index-v1.json"
GEOFABRIK_BASE_URL = "https://download.geofabrik.de"
BASE36_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ZOOM = 13
TILES = 2 ** ZOOM

# iGPSport filename pattern: [CC][RRRR][YYMMDD][GEOCODE_12chars].map
FILENAME_PATTERN = re.compile(
    r"^([A-Z]{2})(\d{4})(\d{6})([0-9A-Z]{12})\.map$"
)


def base36_decode(s):
    """Decode a base36 string to an integer."""
    result = 0
    for c in s.upper():
        result = result * 36 + BASE36_CHARS.index(c)
    return result


def tile_x_to_lon(x):
    """Convert tile X coordinate to longitude."""
    return (x / TILES) * 360.0 - 180.0


def tile_y_to_lat(y):
    """Convert tile Y coordinate to latitude."""
    n = math.pi * (1.0 - 2.0 * y / TILES)
    return math.degrees(math.atan(math.sinh(n)))


def decode_geocode(geocode):
    """Decode a 12-character geocode into a bounding box.

    Returns (min_lon, min_lat, max_lon, max_lat).
    """
    min_lon_x = base36_decode(geocode[0:3])
    max_lat_y = base36_decode(geocode[3:6])
    lon_span = base36_decode(geocode[6:9]) + 1
    lat_span = base36_decode(geocode[9:12]) + 1

    min_lon = tile_x_to_lon(min_lon_x)
    max_lon = tile_x_to_lon(min_lon_x + lon_span)
    max_lat = tile_y_to_lat(max_lat_y)
    min_lat = tile_y_to_lat(max_lat_y + lat_span)

    return min_lon, min_lat, max_lon, max_lat


def parse_filename(filename):
    """Parse an iGPSport map filename.

    Returns dict with country_code, product_code, date, geocode, bbox, or None.
    """
    basename = os.path.basename(filename)
    m = FILENAME_PATTERN.match(basename)
    if not m:
        return None

    country_code, product_code, date, geocode = m.groups()
    bbox = decode_geocode(geocode)

    return {
        "filename": basename,
        "country_code": country_code,
        "product_code": product_code,
        "date": date,
        "geocode": geocode,
        "bbox": bbox,
    }


def bbox_from_geometry(geometry):
    """Extract bounding box from a GeoJSON geometry."""
    min_lon = float("inf")
    min_lat = float("inf")
    max_lon = float("-inf")
    max_lat = float("-inf")

    for polygon in geometry["coordinates"]:
        for ring in polygon:
            for lon, lat in ring:
                min_lon = min(min_lon, lon)
                min_lat = min(min_lat, lat)
                max_lon = max(max_lon, lon)
                max_lat = max(max_lat, lat)

    return min_lon, min_lat, max_lon, max_lat


def bbox_overlap_area(bbox1, bbox2):
    """Calculate the overlap area between two bounding boxes."""
    min_lon = max(bbox1[0], bbox2[0])
    min_lat = max(bbox1[1], bbox2[1])
    max_lon = min(bbox1[2], bbox2[2])
    max_lat = min(bbox1[3], bbox2[3])

    if min_lon >= max_lon or min_lat >= max_lat:
        return 0.0

    return (max_lon - min_lon) * (max_lat - min_lat)


def bbox_intersection(bbox1, bbox2):
    """Return the overlapping bbox or None when there is no overlap."""
    min_lon = max(bbox1[0], bbox2[0])
    min_lat = max(bbox1[1], bbox2[1])
    max_lon = min(bbox1[2], bbox2[2])
    max_lat = min(bbox1[3], bbox2[3])

    if min_lon >= max_lon or min_lat >= max_lat:
        return None

    return min_lon, min_lat, max_lon, max_lat


def bbox_area(bbox):
    """Calculate the area of a bounding box."""
    return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])


def rect_union_area(rectangles):
    """Calculate union area of axis-aligned rectangles."""
    rects = [r for r in rectangles if r is not None]
    if not rects:
        return 0.0

    xs = sorted({rect[0] for rect in rects} | {rect[2] for rect in rects})
    area = 0.0

    for i in range(len(xs) - 1):
        x1 = xs[i]
        x2 = xs[i + 1]
        if x1 >= x2:
            continue

        intervals = []
        for min_lon, min_lat, max_lon, max_lat in rects:
            if min_lon < x2 and max_lon > x1:
                intervals.append((min_lat, max_lat))

        if not intervals:
            continue

        intervals.sort()
        covered_y = 0.0
        current_start, current_end = intervals[0]

        for start, end in intervals[1:]:
            if start <= current_end:
                current_end = max(current_end, end)
            else:
                covered_y += current_end - current_start
                current_start, current_end = start, end

        covered_y += current_end - current_start
        area += (x2 - x1) * covered_y

    return area


def pbf_url_to_poly_url(pbf_url):
    """Derive the polygon URL from a Geofabrik PBF URL."""
    # https://download.geofabrik.de/europe/germany/hessen-latest.osm.pbf
    # -> https://download.geofabrik.de/europe/germany/hessen.poly
    path = pbf_url.replace(f"{GEOFABRIK_BASE_URL}/", "")
    path = re.sub(r"-latest\.osm\.pbf$", "", path)
    return f"{GEOFABRIK_BASE_URL}/{path}.poly"


def fetch_geofabrik_index():
    """Download and parse the Geofabrik region index."""
    print("Downloading Geofabrik region index...")
    req = urllib.request.Request(GEOFABRIK_INDEX_URL, headers={"User-Agent": "igpsport-map-updater"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    print(f"  Found {len(data['features'])} regions.")
    return data


def build_region_lookup(regions):
    """Build a lookup from Geofabrik region id to feature."""
    lookup = {}
    for region in regions:
        props = region.get("properties", {})
        region_id = props.get("id")
        if region_id:
            lookup[region_id] = region
    return lookup


def region_country_codes(region, region_lookup):
    """Resolve ISO alpha-2 country codes through the parent chain."""
    props = region.get("properties", {})
    visited = set()

    while props:
        iso_codes = props.get("iso3166-1:alpha2")
        if iso_codes:
            return set(iso_codes)

        parent_id = props.get("parent")
        if not parent_id or parent_id in visited:
            break

        visited.add(parent_id)
        parent = region_lookup.get(parent_id)
        if not parent:
            break

        props = parent.get("properties", {})

    return set()


def region_country_metadata(region, region_lookup):
    """Resolve country codes, root country id, and depth-to-country."""
    props = region.get("properties", {})
    current = region
    depth = 0
    visited = set()

    while props:
        iso_codes = props.get("iso3166-1:alpha2")
        if iso_codes:
            return {
                "country_codes": set(iso_codes),
                "country_id": props.get("id"),
                "depth": depth,
            }

        parent_id = props.get("parent")
        if not parent_id or parent_id in visited:
            break

        visited.add(parent_id)
        parent = region_lookup.get(parent_id)
        if not parent:
            break

        current = parent
        props = current.get("properties", {})
        depth += 1

    return {
        "country_codes": set(),
        "country_id": None,
        "depth": depth,
    }


def find_candidate_regions(map_bbox, regions, country_code=None):
    """Build scored candidate regions for a map bbox."""
    map_area = bbox_area(map_bbox)
    if map_area == 0:
        return []

    region_lookup = build_region_lookup(regions)
    candidates = []

    for region in regions:
        if "geometry" not in region or region["geometry"] is None:
            continue

        props = region["properties"]
        if "pbf" not in props.get("urls", {}):
            continue

        region_bbox = bbox_from_geometry(region["geometry"])
        overlap_bbox = bbox_intersection(map_bbox, region_bbox)
        overlap = bbox_area(overlap_bbox) if overlap_bbox else 0.0
        overlap_ratio = overlap / map_area

        if overlap_ratio < 0.15:
            continue

        country_meta = region_country_metadata(region, region_lookup)
        candidates.append({
            "feature": region,
            "overlap_ratio": overlap_ratio,
            "region_area": bbox_area(region_bbox),
            "region_bbox": region_bbox,
            "intersection_bbox": overlap_bbox,
            "country_codes": country_meta["country_codes"],
            "country_id": country_meta["country_id"],
            "depth": country_meta["depth"],
        })

    if country_code:
        same_country = [
            candidate for candidate in candidates
            if country_code in candidate["country_codes"]
        ]
        if same_country:
            return same_country

    return candidates


def find_best_match(map_bbox, regions, country_code=None):
    """Find the best matching Geofabrik region for a bounding box.

    Strategy: find the region with the highest overlap ratio (overlap / map_area)
    that is also reasonably small (prefer specific regions over continents).
    If a country code is available from the original filename, prefer regions
    whose Geofabrik parent chain resolves to that same country.
    """
    candidates = [
        candidate for candidate in find_candidate_regions(map_bbox, regions, country_code)
        if candidate["overlap_ratio"] >= 0.5
    ]

    if not candidates:
        return None

    # Sort by: high overlap ratio first, then smallest region (most specific)
    candidates.sort(key=lambda c: (-c["overlap_ratio"], -c["depth"], c["region_area"]))

    # Among candidates with >90% overlap, prefer the smallest region
    good = [c for c in candidates if c["overlap_ratio"] > 0.9]
    if good:
        good.sort(key=lambda c: (-c["depth"], c["region_area"]))
        return good[0]

    return candidates[0]


def find_region_combo(map_bbox, candidates, max_regions=4, coverage_target=0.98):
    """Greedily pick a small region set that covers most of the map bbox."""
    map_area = bbox_area(map_bbox)
    if map_area == 0:
        return None

    pool = [
        candidate for candidate in candidates
        if candidate["depth"] > 0 and candidate["intersection_bbox"] is not None
    ]
    if len(pool) < 2:
        return None

    selected = []
    covered_rects = []
    covered_area = 0.0
    remaining = list(pool)

    while remaining and len(selected) < max_regions:
        best = None
        best_gain = 0.0

        for candidate in remaining:
            new_area = rect_union_area(covered_rects + [candidate["intersection_bbox"]])
            gain = new_area - covered_area
            if gain > best_gain + 1e-12:
                best = candidate
                best_gain = gain
            elif best is not None and abs(gain - best_gain) <= 1e-12:
                best_key = (best["overlap_ratio"], best["depth"], -best["region_area"])
                candidate_key = (candidate["overlap_ratio"], candidate["depth"], -candidate["region_area"])
                if candidate_key > best_key:
                    best = candidate

        if best is None or best_gain <= 0:
            break

        selected.append(best)
        covered_rects.append(best["intersection_bbox"])
        covered_area = rect_union_area(covered_rects)
        remaining.remove(best)

        if covered_area / map_area >= coverage_target:
            break

    coverage_ratio = covered_area / map_area
    if len(selected) < 2:
        return None

    return {
        "mode": "multi",
        "matches": selected,
        "coverage_ratio": coverage_ratio,
    }


def find_region_sources(map_bbox, regions, country_code=None):
    """Choose one or more source regions for a map tile."""
    candidates = find_candidate_regions(map_bbox, regions, country_code)
    if not candidates:
        return None

    if country_code == "UK":
        min_lon, _min_lat, max_lon, _max_lat = map_bbox
        center_lon = (min_lon + max_lon) / 2
        if center_lon < -5.0:
            ireland_ni = [
                candidate for candidate in candidates
                if candidate["feature"]["properties"].get("id") == "ireland-and-northern-ireland"
            ]
            best = None
            if ireland_ni:
                best = max(ireland_ni, key=lambda candidate: candidate["overlap_ratio"])
                if best["overlap_ratio"] < 0.8:
                    best = None
            if best:
                return {
                    "mode": "single",
                    "matches": [best],
                    "coverage_ratio": best["overlap_ratio"],
                }

    best_single = find_best_match(map_bbox, regions, country_code)
    best_combo = find_region_combo(map_bbox, candidates)

    if best_combo is not None and best_single is not None:
        combo_ratio = best_combo["coverage_ratio"]
        single_ratio = best_single["overlap_ratio"]

        if best_single["depth"] == 0 and combo_ratio >= 0.85:
            return best_combo

        if combo_ratio >= max(0.92, single_ratio + 0.03):
            return best_combo

    return {
        "mode": "single",
        "matches": [best_single],
        "coverage_ratio": best_single["overlap_ratio"],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate maps.csv from original iGPSport map files."
    )
    parser.add_argument(
        "directory",
        help="Directory containing original iGPSport .map files",
    )
    parser.add_argument(
        "-o", "--output",
        default="maps.csv",
        help="Output CSV file path (default: maps.csv)",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    # Find and parse map files
    map_files = []
    for f in sorted(os.listdir(args.directory)):
        if f.upper().endswith(".MAP"):
            parsed = parse_filename(f)
            if parsed:
                map_files.append(parsed)
            else:
                print(f"  Skipping '{f}' (does not match iGPSport filename pattern)")

    if not map_files:
        print("Error: No valid iGPSport map files found.", file=sys.stderr)
        sys.exit(1)

    print(f"\nFound {len(map_files)} map file(s):\n")
    for mf in map_files:
        bbox = mf["bbox"]
        print(f"  {mf['filename']}")
        print(f"    Country: {mf['country_code']}  Product: {mf['product_code']}  Date: {mf['date']}")
        print(f"    Bounding box: {bbox[0]:.2f}E {bbox[1]:.2f}N  to  {bbox[2]:.2f}E {bbox[3]:.2f}N")
        print()

    # Fetch Geofabrik index
    index = fetch_geofabrik_index()
    regions = index["features"]

    # Match each map file to a region
    csv_rows = []
    for mf in map_files:
        print(f"Matching {mf['filename']}...")
        selection = find_region_sources(mf["bbox"], regions, country_code=mf["country_code"])

        if selection is None:
            print(f"  WARNING: No matching region found! Skipping.")
            continue

        matches = selection["matches"]
        pbf_urls = [match["feature"]["properties"]["urls"]["pbf"] for match in matches]
        poly_urls = [pbf_url_to_poly_url(pbf_url) for pbf_url in pbf_urls]
        coverage_pct = selection["coverage_ratio"] * 100

        if selection["mode"] == "multi":
            region_label = ", ".join(match["feature"]["properties"]["id"] for match in matches)
            print(
                f"  Matched: multi-region blend ({len(matches)} regions, coverage: {coverage_pct:.1f}%)"
            )
            print(f"  Regions: {region_label}")
        else:
            props = matches[0]["feature"]["properties"]
            print(f"  Matched: {props['name']} (id: {props['id']}, overlap: {coverage_pct:.1f}%)")

        for pbf_url in pbf_urls:
            print(f"  PBF:  {pbf_url}")
        for poly_url in poly_urls:
            print(f"  Poly: {poly_url}")
        print()

        csv_rows.append({
            "filename": mf["filename"],
            "pbf_url": ";".join(pbf_urls),
            "poly_url": ";".join(poly_urls),
            "selection_mode": selection["mode"],
        })

    if not csv_rows:
        print("Error: Could not match any map files to Geofabrik regions.", file=sys.stderr)
        sys.exit(1)

    # Write CSV
    with open(args.output, "w", newline="") as f:
        f.write("Original filename,OSM BPF URL,Poly URL\n")
        for row in csv_rows:
            f.write(f"{row['filename']},{row['pbf_url']},{row['poly_url']}\n")

    print(f"Written {len(csv_rows)} entries to {args.output}")
    print("\nPlease verify the matched regions are correct before running the map generation script.")


if __name__ == "__main__":
    main()
