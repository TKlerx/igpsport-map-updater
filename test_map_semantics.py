"""Tests for baseline-vs-optimized Mapsforge semantic comparison."""

import struct

from igpsport_map_updater.map_semantics import (
    compare_mapsforge_semantics,
    read_mapsforge_semantics,
)


def _var_string(value):
    raw = value.encode("utf-8")
    assert len(raw) < 128
    return bytes([len(raw)]) + raw


def _fixture_map(
    *,
    file_size=1000,
    date_created=1,
    bbox=(47_000000, 7_000000, 48_000000, 8_000000),
    created_by="baseline-writer",
    poi_tags=("amenity=parking",),
    way_tags=("highway=primary", "surface=asphalt"),
    subfile_start=128,
    subfile_size=512,
):
    flags = 0x04
    header = (
        b"mapsforge binary OSM"
        + struct.pack(">I", 0)
        + struct.pack(">I", 5)
        + struct.pack(">Q", file_size)
        + struct.pack(">Q", date_created)
        + struct.pack(">iiii", *bbox)
        + struct.pack(">H", 256)
        + _var_string("Mercator")
        + bytes([flags])
        + _var_string(created_by)
        + struct.pack(">H", len(poi_tags))
        + b"".join(_var_string(tag) for tag in poi_tags)
        + struct.pack(">H", len(way_tags))
        + b"".join(_var_string(tag) for tag in way_tags)
        + bytes([1])
        + bytes([13, 12, 15])
        + struct.pack(">Q", subfile_start)
        + struct.pack(">Q", subfile_size)
    )
    return header + b"\x00" * 32


def test_reads_mapsforge_semantic_fields(tmp_path):
    path = tmp_path / "baseline.map"
    path.write_bytes(_fixture_map())

    semantics = read_mapsforge_semantics(path)

    assert semantics.file_version == 5
    assert semantics.bbox == (47.0, 7.0, 48.0, 8.0)
    assert semantics.tile_size == 256
    assert semantics.projection == "Mercator"
    assert semantics.poi_tags == ("amenity=parking",)
    assert semantics.way_tags == ("highway=primary", "surface=asphalt")
    assert semantics.zoom_intervals[0].base_zoom == 13


def test_baseline_and_osmium_preclip_maps_may_differ_only_in_nonsemantic_metadata(tmp_path):
    baseline = tmp_path / "baseline.map"
    preclip = tmp_path / "preclip.map"
    baseline.write_bytes(
        _fixture_map(
            file_size=1000,
            date_created=1,
            created_by="baseline-writer",
            subfile_start=128,
            subfile_size=512,
        )
    )
    preclip.write_bytes(
        _fixture_map(
            file_size=2000,
            date_created=2,
            created_by="osmium-preclip-writer",
            subfile_start=256,
            subfile_size=768,
        )
    )

    assert compare_mapsforge_semantics(baseline, preclip) == []


def test_baseline_and_osmium_preclip_maps_fail_when_way_tags_differ(tmp_path):
    baseline = tmp_path / "baseline.map"
    preclip = tmp_path / "preclip.map"
    baseline.write_bytes(_fixture_map(way_tags=("highway=primary", "surface=asphalt")))
    preclip.write_bytes(_fixture_map(way_tags=("highway=primary", "surface=gravel")))

    mismatches = compare_mapsforge_semantics(baseline, preclip)

    assert mismatches == [
        {
            "field": "way_tags",
            "baseline": ("highway=primary", "surface=asphalt"),
            "candidate": ("highway=primary", "surface=gravel"),
        }
    ]
