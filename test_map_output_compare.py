"""Tests for folder-level Mapsforge output comparison."""

import struct

from igpsport_map_updater.map_output_compare import compare_output_dirs, has_failures


def _var_string(value):
    raw = value.encode("utf-8")
    return bytes([len(raw)]) + raw


def _fixture_map(way_tags=("highway=primary",), created_by="writer"):
    return (
        b"mapsforge binary OSM"
        + struct.pack(">I", 0)
        + struct.pack(">I", 5)
        + struct.pack(">Q", 1000)
        + struct.pack(">Q", 1)
        + struct.pack(">iiii", 47_000000, 7_000000, 48_000000, 8_000000)
        + struct.pack(">H", 256)
        + _var_string("Mercator")
        + bytes([0x04])
        + _var_string(created_by)
        + struct.pack(">H", 0)
        + struct.pack(">H", len(way_tags))
        + b"".join(_var_string(tag) for tag in way_tags)
        + bytes([1])
        + bytes([13, 12, 15])
        + struct.pack(">Q", 128)
        + struct.pack(">Q", 512)
    )


def test_compare_output_dirs_matches_by_tile_identity_not_date(tmp_path):
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    baseline.mkdir()
    candidate.mkdir()
    (baseline / "IT000026022039Y27X07X0A5.map").write_bytes(_fixture_map(created_by="baseline"))
    (candidate / "IT000026030139Y27X07X0A5.map").write_bytes(_fixture_map(created_by="preclip"))

    results = compare_output_dirs(baseline, candidate)

    assert results[0]["status"] == "match"
    assert results[0]["key"] == ("IT", "0000", "39Y27X07X0A5")
    assert has_failures(results) is False


def test_compare_output_dirs_reports_missing_candidate(tmp_path):
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    baseline.mkdir()
    candidate.mkdir()
    (baseline / "IT000026022039Y27X07X0A5.map").write_bytes(_fixture_map())

    results = compare_output_dirs(baseline, candidate)

    assert results[0]["status"] == "missing-candidate"
    assert has_failures(results) is True


def test_compare_output_dirs_reports_semantic_mismatch(tmp_path):
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    baseline.mkdir()
    candidate.mkdir()
    name = "IT000026022039Y27X07X0A5.map"
    (baseline / name).write_bytes(_fixture_map(way_tags=("highway=primary",)))
    (candidate / name).write_bytes(_fixture_map(way_tags=("highway=secondary",)))

    results = compare_output_dirs(baseline, candidate)

    assert results[0]["status"] == "mismatch"
    assert results[0]["mismatches"][0]["field"] == "way_tags"
    assert has_failures(results) is True
