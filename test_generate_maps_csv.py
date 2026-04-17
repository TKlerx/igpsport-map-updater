"""Tests for generate_maps_csv.py"""

import math
import os
import tempfile

import pytest

from generate_maps_csv import (
    base36_decode,
    bbox_area,
    bbox_from_geometry,
    bbox_overlap_area,
    build_region_lookup,
    decode_geocode,
    find_best_match,
    parse_filename,
    pbf_url_to_poly_url,
    region_country_codes,
    tile_x_to_lon,
    tile_y_to_lat,
)


# --- base36_decode ---


class TestBase36Decode:
    def test_single_digit(self):
        assert base36_decode("0") == 0
        assert base36_decode("9") == 9
        assert base36_decode("A") == 10
        assert base36_decode("Z") == 35

    def test_multi_digit(self):
        assert base36_decode("10") == 36
        assert base36_decode("ZZ") == 35 * 36 + 35  # 1295
        assert base36_decode("100") == 1296

    def test_case_insensitive(self):
        assert base36_decode("abc") == base36_decode("ABC")

    def test_three_char_geocode_parts(self):
        # 3AO = 3*1296 + 10*36 + 24 = 4272
        assert base36_decode("3AO") == 4272
        # 23I = 2*1296 + 3*36 + 18 = 2718
        assert base36_decode("23I") == 2718


# --- tile coordinate conversions ---


class TestTileConversions:
    def test_tile_x_to_lon_edges(self):
        assert tile_x_to_lon(0) == -180.0
        assert tile_x_to_lon(2**13) == pytest.approx(180.0)
        assert tile_x_to_lon(2**13 / 2) == pytest.approx(0.0)

    def test_tile_y_to_lat_equator(self):
        assert tile_y_to_lat(2**13 / 2) == pytest.approx(0.0, abs=0.01)

    def test_tile_y_to_lat_north(self):
        # y=0 should be near +85.05 (max Mercator latitude)
        assert tile_y_to_lat(0) > 85.0

    def test_tile_y_to_lat_south(self):
        assert tile_y_to_lat(2**13) < -85.0


# --- decode_geocode ---


class TestDecodeGeocode:
    def test_hessen(self):
        # DE0700 map: geocode 3AO23I01L029
        min_lon, min_lat, max_lon, max_lat = decode_geocode("3AO23I01L029")
        # Hessen: roughly 7.7E-10.3E, 49.4N-51.7N
        assert 7.5 < min_lon < 8.0
        assert 49.0 < min_lat < 50.0
        assert 10.0 < max_lon < 10.5
        assert 51.0 < max_lat < 52.0

    def test_niedersachsen(self):
        min_lon, min_lat, max_lon, max_lat = decode_geocode("39R20Z03D02W")
        # Niedersachsen: roughly 6.3E-11.7E, 51.3N-54.1N
        assert 6.0 < min_lon < 6.5
        assert 51.0 < min_lat < 51.5
        assert 11.5 < max_lon < 12.0
        assert 53.5 < max_lat < 54.5

    def test_nrw(self):
        min_lon, min_lat, max_lon, max_lat = decode_geocode("39H22L02A029")
        # NRW: roughly 5.8E-9.5E, 50.3N-52.6N
        assert 5.5 < min_lon < 6.0
        assert 50.0 < min_lat < 50.5
        assert 9.0 < max_lon < 10.0
        assert 52.0 < max_lat < 53.0

    def test_returns_four_floats(self):
        result = decode_geocode("3AO23I01L029")
        assert len(result) == 4
        assert all(isinstance(v, float) for v in result)

    def test_min_less_than_max(self):
        min_lon, min_lat, max_lon, max_lat = decode_geocode("3AO23I01L029")
        assert min_lon < max_lon
        assert min_lat < max_lat


# --- parse_filename ---


class TestParseFilename:
    def test_valid_german_filename(self):
        result = parse_filename("DE07002303103AO23I01L029.map")
        assert result is not None
        assert result["country_code"] == "DE"
        assert result["product_code"] == "0700"
        assert result["date"] == "230310"
        assert result["geocode"] == "3AO23I01L029"
        assert len(result["bbox"]) == 4

    def test_valid_brazilian_filename(self):
        result = parse_filename("BR01002303102B83FO00N00E.map")
        assert result is not None
        assert result["country_code"] == "BR"
        assert result["product_code"] == "0100"

    def test_strips_directory_path(self):
        result = parse_filename("/some/path/DE07002303103AO23I01L029.map")
        assert result is not None
        assert result["filename"] == "DE07002303103AO23I01L029.map"

    def test_invalid_filename_returns_none(self):
        assert parse_filename("random_file.map") is None
        assert parse_filename("DE0700230310.map") is None  # geocode too short
        assert parse_filename("readme.txt") is None

    def test_lowercase_rejected(self):
        # Country code must be uppercase
        assert parse_filename("de07002303103AO23I01L029.map") is None


# --- bbox helpers ---


class TestBboxHelpers:
    def test_bbox_area(self):
        assert bbox_area((0, 0, 10, 10)) == 100.0
        assert bbox_area((5, 5, 5, 5)) == 0.0

    def test_bbox_overlap_full(self):
        box = (0, 0, 10, 10)
        assert bbox_overlap_area(box, box) == 100.0

    def test_bbox_overlap_partial(self):
        box1 = (0, 0, 10, 10)
        box2 = (5, 5, 15, 15)
        assert bbox_overlap_area(box1, box2) == 25.0

    def test_bbox_overlap_none(self):
        box1 = (0, 0, 5, 5)
        box2 = (10, 10, 15, 15)
        assert bbox_overlap_area(box1, box2) == 0.0

    def test_bbox_overlap_touching_edge(self):
        box1 = (0, 0, 5, 5)
        box2 = (5, 0, 10, 5)
        assert bbox_overlap_area(box1, box2) == 0.0


# --- bbox_from_geometry ---


class TestBboxFromGeometry:
    def test_simple_polygon(self):
        geometry = {
            "type": "MultiPolygon",
            "coordinates": [[[[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [1.0, 2.0]]]],
        }
        assert bbox_from_geometry(geometry) == (1.0, 2.0, 5.0, 6.0)

    def test_multi_polygon(self):
        geometry = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[0.0, 0.0], [1.0, 1.0], [0.0, 0.0]]],
                [[[10.0, 10.0], [20.0, 20.0], [10.0, 10.0]]],
            ],
        }
        assert bbox_from_geometry(geometry) == (0.0, 0.0, 20.0, 20.0)


# --- pbf_url_to_poly_url ---


class TestPbfUrlToPolyUrl:
    def test_german_state(self):
        pbf = "https://download.geofabrik.de/europe/germany/hessen-latest.osm.pbf"
        expected = "https://download.geofabrik.de/europe/germany/hessen.poly"
        assert pbf_url_to_poly_url(pbf) == expected

    def test_country_level(self):
        pbf = "https://download.geofabrik.de/europe/france-latest.osm.pbf"
        expected = "https://download.geofabrik.de/europe/france.poly"
        assert pbf_url_to_poly_url(pbf) == expected

    def test_south_america(self):
        pbf = "https://download.geofabrik.de/south-america/brazil-latest.osm.pbf"
        expected = "https://download.geofabrik.de/south-america/brazil.poly"
        assert pbf_url_to_poly_url(pbf) == expected


# --- find_best_match ---


def _make_region(name, region_id, bbox, parent="germany"):
    """Helper to create a fake Geofabrik region feature."""
    min_lon, min_lat, max_lon, max_lat = bbox
    return {
        "properties": {
            "id": region_id,
            "name": name,
            "parent": parent,
            "urls": {
                "pbf": f"https://download.geofabrik.de/europe/{parent}/{region_id}-latest.osm.pbf",
            },
        },
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [[[[min_lon, min_lat], [max_lon, min_lat],
                              [max_lon, max_lat], [min_lon, max_lat],
                              [min_lon, min_lat]]]],
        },
    }


def _make_country(name, region_id, bbox, iso_code, parent="europe"):
    region = _make_region(name, region_id, bbox, parent=parent)
    region["properties"]["iso3166-1:alpha2"] = [iso_code]
    return region


class TestFindBestMatch:
    def test_exact_match(self):
        regions = [_make_region("Hessen", "hessen", (7.7, 49.4, 10.3, 51.7))]
        match = find_best_match((7.7, 49.4, 10.3, 51.7), regions)
        assert match is not None
        assert match["feature"]["properties"]["id"] == "hessen"
        assert match["overlap_ratio"] == pytest.approx(1.0)

    def test_prefers_smaller_region(self):
        regions = [
            _make_region("Germany", "germany", (5.0, 47.0, 15.5, 55.0), parent="europe"),
            _make_region("Hessen", "hessen", (7.7, 49.4, 10.3, 51.7)),
        ]
        match = find_best_match((7.7, 49.4, 10.3, 51.7), regions)
        assert match["feature"]["properties"]["id"] == "hessen"

    def test_no_match_when_no_overlap(self):
        regions = [_make_region("Hessen", "hessen", (7.7, 49.4, 10.3, 51.7))]
        match = find_best_match((100.0, 30.0, 110.0, 40.0), regions)
        assert match is None

    def test_no_match_for_zero_area_bbox(self):
        regions = [_make_region("Hessen", "hessen", (7.7, 49.4, 10.3, 51.7))]
        match = find_best_match((5.0, 5.0, 5.0, 5.0), regions)
        assert match is None

    def test_skips_regions_without_geometry(self):
        regions = [{"properties": {"id": "x", "urls": {"pbf": "http://x"}}, "geometry": None}]
        match = find_best_match((7.7, 49.4, 10.3, 51.7), regions)
        assert match is None

    def test_skips_regions_without_pbf_url(self):
        regions = [
            {
                "properties": {"id": "x", "urls": {}},
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [[[[7.7, 49.4], [10.3, 49.4], [10.3, 51.7], [7.7, 51.7], [7.7, 49.4]]]],
                },
            }
        ]
        match = find_best_match((7.7, 49.4, 10.3, 51.7), regions)
        assert match is None

    def test_falls_back_to_larger_region_when_needed(self):
        # Map bbox is bigger than the small region but smaller than the large one
        regions = [
            _make_region("Small", "small", (8.0, 50.0, 9.0, 51.0)),
            _make_region("Large", "large", (5.0, 47.0, 15.0, 55.0), parent="europe"),
        ]
        # Map bbox that mostly falls outside the small region
        match = find_best_match((5.0, 47.0, 15.0, 55.0), regions)
        assert match["feature"]["properties"]["id"] == "large"

    def test_prefers_same_country_via_parent_chain(self):
        regions = [
            _make_country("Czech Republic", "czech-republic", (12.0, 48.0, 19.0, 51.5), "CZ"),
            _make_country("Germany", "germany", (5.0, 47.0, 15.5, 55.0), "DE"),
            _make_region("Jihočeský kraj", "jihocesky", (13.0, 48.4, 15.6, 49.9), parent="czech-republic"),
            _make_region("Bayern", "bayern", (11.9, 47.2, 13.5, 50.6), parent="germany"),
        ]
        match = find_best_match((12.04, 49.87, 13.36, 50.49), regions, country_code="CZ")
        assert match is not None
        assert match["feature"]["properties"]["id"] != "bayern"

    def test_falls_back_to_foreign_region_when_no_same_country_exists(self):
        regions = [
            _make_country("Germany", "germany", (5.0, 47.0, 15.5, 55.0), "DE"),
            _make_region("Bayern", "bayern", (11.9, 47.2, 13.5, 50.6), parent="germany"),
        ]
        match = find_best_match((12.04, 49.87, 13.36, 50.49), regions, country_code="CZ")
        assert match is not None
        assert match["feature"]["properties"]["id"] == "bayern"


class TestRegionCountryCodes:
    def test_resolves_country_code_from_parent_chain(self):
        regions = [
            _make_country("Czech Republic", "czech-republic", (12.0, 48.0, 19.0, 51.5), "CZ"),
            _make_region("Jihočeský kraj", "jihocesky", (13.0, 48.4, 15.6, 49.9), parent="czech-republic"),
        ]
        lookup = build_region_lookup(regions)
        codes = region_country_codes(regions[1], lookup)
        assert codes == {"CZ"}


# --- integration: parse real filenames and verify bounding boxes ---


class TestRealFilenames:
    """Test against the actual iGPSport filenames from the user's device."""

    FILENAMES = [
        ("DE07002303103AO23I01L029.map", "DE", "0700", (7.5, 49.0, 10.5, 52.0)),
        ("DE090023031039R20Z03D02W.map", "DE", "0900", (6.0, 51.0, 12.0, 54.5)),
        ("DE100023031039H22L02A029.map", "DE", "1000", (5.5, 50.0, 10.0, 53.0)),
        ("BR01002303102B83FO00N00E.map", "BR", "0100", (-49.0, -16.5, -46.5, -14.5)),
    ]

    @pytest.mark.parametrize("filename,country,product,approx_bbox", FILENAMES)
    def test_parse_and_bbox_in_range(self, filename, country, product, approx_bbox):
        result = parse_filename(filename)
        assert result is not None
        assert result["country_code"] == country
        assert result["product_code"] == product

        min_lon, min_lat, max_lon, max_lat = result["bbox"]
        exp_min_lon, exp_min_lat, exp_max_lon, exp_max_lat = approx_bbox
        assert exp_min_lon < min_lon < exp_max_lon
        assert exp_min_lat < min_lat < exp_max_lat
        assert exp_min_lon < max_lon < exp_max_lon
        assert exp_min_lat < max_lat < exp_max_lat
