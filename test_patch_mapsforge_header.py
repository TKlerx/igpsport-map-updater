"""Tests for Mapsforge header compatibility patching."""

import struct

from igpsport_map_updater.patch_mapsforge_header import (
    patch_bbox,
    patch_created_by,
    read_bbox_bytes,
    read_created_by,
)


def _minimal_map(created_by, bbox=(1, 2, 3, 4)):
    created_by_bytes = created_by.encode("ascii")
    return (
        b"mapsforge binary OSM"
        + b"\x00" * 24
        + struct.pack(">iiii", *bbox)
        + b"\x00" * 2
        + b"Mercator"
        b"\x04"
        + bytes([len(created_by_bytes)])
        + created_by_bytes
        + b"\x00\x00\x00\x14"
    )


def test_patch_created_by_copies_original_header_value(tmp_path):
    original = tmp_path / "original.map"
    generated = tmp_path / "generated.map"
    original.write_bytes(_minimal_map("mapsforge-map-writer-0.16.Q"))
    generated.write_bytes(_minimal_map("mapsforge-map-writer-0.27.0"))

    patch_created_by(original, generated)

    assert read_created_by(generated) == b"mapsforge-map-writer-0.16.Q"


def test_patch_bbox_copies_original_header_value(tmp_path):
    original = tmp_path / "original.map"
    generated = tmp_path / "generated.map"
    original.write_bytes(_minimal_map("mapsforge-map-writer-0.16.Q", (10, 20, 30, 40)))
    generated.write_bytes(_minimal_map("mapsforge-map-writer-0.16.Q", (1, 2, 3, 4)))

    patch_bbox(original, generated)

    assert read_bbox_bytes(generated) == struct.pack(">iiii", 10, 20, 30, 40)
