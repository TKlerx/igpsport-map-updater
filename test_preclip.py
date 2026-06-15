"""Tests for Osmium preclip cache and command helpers."""

import pytest

from igpsport_map_updater.preclip import (
    PreclipRequest,
    build_osmium_extract_command,
    cache_paths,
    cache_valid,
    expected_cache_metadata,
    normalize_preclip_mode,
    osmium_available,
)


def _request(tmp_path, source):
    return PreclipRequest(
        source_pbf=source,
        cache_dir=tmp_path / "cache",
        tile_geocode="39Y27X07X0A5",
        bbox=(7.0, 47.0, 8.0, 48.0),
    )


def test_normalize_preclip_mode_defaults_to_disabled():
    assert normalize_preclip_mode(None) == "disabled"
    assert normalize_preclip_mode("off") == "disabled"
    assert normalize_preclip_mode("auto") == "auto"
    assert normalize_preclip_mode("required") == "required"
    with pytest.raises(ValueError):
        normalize_preclip_mode("always")


def test_osmium_available_reports_missing_binary(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda executable: None)

    assert osmium_available() is False


def test_osmium_extract_command_uses_bbox_strategy_output_and_source(tmp_path):
    source = tmp_path / "source.osm.pbf"
    source.write_bytes(b"pbf")
    request = _request(tmp_path, source)
    output = tmp_path / "clipped.osm.pbf"

    assert build_osmium_extract_command(request, output) == [
        "osmium",
        "extract",
        "-b",
        "7.0,47.0,8.0,48.0",
        "-s",
        "smart",
        "-f",
        "pbf",
        "--overwrite",
        "-o",
        str(output),
        str(source),
    ]


def test_cache_validates_matching_metadata(tmp_path):
    source = tmp_path / "source.osm.pbf"
    source.write_bytes(b"pbf")
    request = _request(tmp_path, source)
    request.cache_dir.mkdir()
    clipped, meta_path = cache_paths(request)
    clipped.write_bytes(b"clipped")
    meta_path.write_text(
        __import__("json").dumps(expected_cache_metadata(request)),
        encoding="utf-8",
    )

    assert cache_valid(request) is True


def test_cache_invalidates_source_bbox_and_strategy_changes(tmp_path):
    source = tmp_path / "source.osm.pbf"
    source.write_bytes(b"pbf")
    request = _request(tmp_path, source)
    request.cache_dir.mkdir()
    clipped, meta_path = cache_paths(request)
    clipped.write_bytes(b"clipped")
    meta_path.write_text(
        __import__("json").dumps(expected_cache_metadata(request)),
        encoding="utf-8",
    )

    source.write_bytes(b"changed")
    assert cache_valid(request) is False

    source.write_bytes(b"pbf")
    changed_bbox = PreclipRequest(source, request.cache_dir, request.tile_geocode, (7.1, 47.0, 8.0, 48.0))
    assert cache_valid(changed_bbox) is False

    changed_strategy = PreclipRequest(source, request.cache_dir, request.tile_geocode, request.bbox, "complete_ways")
    assert cache_valid(changed_strategy) is False


def test_multi_source_requests_keep_one_cache_per_source(tmp_path):
    first = tmp_path / "first.osm.pbf"
    second = tmp_path / "second.osm.pbf"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    first_request = _request(tmp_path, first)
    second_request = _request(tmp_path, second)

    first_cache, _ = cache_paths(first_request)
    second_cache, _ = cache_paths(second_request)

    assert first_cache != second_cache
    assert first_cache.name.startswith("first.osm.pbf")
    assert second_cache.name.startswith("second.osm.pbf")
