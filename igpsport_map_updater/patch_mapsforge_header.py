#!/usr/bin/env python3
"""Patch Mapsforge header metadata for iGPSPORT compatibility tests."""

import argparse
import sys
from pathlib import Path


MAGIC = b"mapsforge binary OSM"
BBOX_OFFSET = len(MAGIC) + 4 + 4 + 8 + 8
BBOX_LENGTH = 16


def _require_mapsforge(data):
    if not data.startswith(MAGIC):
        raise ValueError("Not a Mapsforge map file")


def read_bbox_bytes(path):
    """Read the raw Mapsforge bounding-box header bytes."""
    data = Path(path).read_bytes()
    _require_mapsforge(data)
    end = BBOX_OFFSET + BBOX_LENGTH
    if len(data) < end:
        raise ValueError("Map header ended before bounding-box field")
    return bytes(data[BBOX_OFFSET:end])


def patch_bbox(source_map, target_map, output_map=None):
    """Copy source_map's raw bounding-box header bytes into target_map."""
    replacement = read_bbox_bytes(source_map)
    target_path = Path(target_map)
    data = bytearray(target_path.read_bytes())
    _require_mapsforge(data)
    end = BBOX_OFFSET + BBOX_LENGTH
    if len(data) < end:
        raise ValueError("Target map header ended before bounding-box field")

    data[BBOX_OFFSET:end] = replacement
    output_path = Path(output_map) if output_map else target_path
    output_path.write_bytes(data)
    return output_path


def _created_by_span(data):
    """Return the byte span for the Mapsforge created_by string."""
    _require_mapsforge(data)
    header = data[:2048]
    projection = b"Mercator"
    projection_index = header.find(projection)
    if projection_index < 0:
        raise ValueError("Could not find Mercator projection marker in map header")

    flags_index = projection_index + len(projection)
    if flags_index + 2 > len(header):
        raise ValueError("Map header ended before flags/created_by fields")

    flags = header[flags_index]
    created_by_flag = 0x04
    if not flags & created_by_flag:
        raise ValueError("Map header does not contain a created_by field")

    length_index = flags_index + 1
    length = header[length_index]
    start = length_index + 1
    end = start + length
    if end > len(header):
        raise ValueError("created_by field extends beyond inspected header")

    return start, end


def read_created_by(path):
    """Read the raw created_by bytes from a Mapsforge map file."""
    data = Path(path).read_bytes()
    start, end = _created_by_span(data)
    return data[start:end]


def patch_created_by(source_map, target_map, output_map=None):
    """Copy source_map's created_by bytes into target_map."""
    replacement = read_created_by(source_map)
    target_path = Path(target_map)
    data = bytearray(target_path.read_bytes())
    start, end = _created_by_span(data)

    current_length = end - start
    if len(replacement) != current_length:
        raise ValueError(
            f"created_by length mismatch: source has {len(replacement)} bytes, "
            f"target has {current_length} bytes"
        )

    data[start:end] = replacement
    output_path = Path(output_map) if output_map else target_path
    output_path.write_bytes(data)
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Copy selected Mapsforge header values from one map to another."
    )
    parser.add_argument("source_map", help="Original iGPSPORT map to copy created_by from")
    parser.add_argument("target_map", help="Generated map to patch")
    parser.add_argument(
        "output_map",
        nargs="?",
        help="Optional output path. If omitted, target_map is patched in place.",
    )
    parser.add_argument(
        "--bbox",
        action="store_true",
        help="Copy the source map bounding-box header instead of created_by",
    )
    args = parser.parse_args()

    try:
        if args.bbox:
            output_path = patch_bbox(args.source_map, args.target_map, args.output_map)
        else:
            output_path = patch_created_by(args.source_map, args.target_map, args.output_map)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.bbox:
        print("Patched bounding-box header")
    else:
        created_by = read_created_by(output_path).decode("utf-8", errors="replace").rstrip("\x00")
        print(f"Patched created_by header: {created_by}")


if __name__ == "__main__":
    main()
