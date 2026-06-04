"""Tests for download_igpsport_maps.py"""

from igpsport_map_updater.download_igpsport_maps import (
    common_path_prefix,
    country_regions,
    existing_extracted_maps,
    find_downloads,
    find_regions,
    format_size,
    normalize,
    official_map_prefix,
    path_matches,
    term_matches_text,
)


TREE = [
    {
        "name": "europe",
        "subList": [
            {
                "name": "Switzerland",
                "subList": [
                    {
                        "name": "Aargau",
                        "mapVersion": "20260320",
                        "mapSize": 2875595,
                        "mapPathUrl": "https://example.test/CH0100.zip",
                        "subList": [],
                    },
                    {
                        "name": "Canton Of Graubünden",
                        "mapVersion": "20260320",
                        "mapSize": 3149475,
                        "mapPathUrl": "https://example.test/CH1000.zip",
                        "subList": [],
                    },
                ],
            },
            {
                "name": "Germany",
                "subList": [
                    {
                        "name": "Bayern",
                        "mapVersion": "20260320",
                        "mapSize": 1200,
                        "mapPathUrl": "https://example.test/DE0200.zip",
                        "subList": [],
                    },
                ],
            },
        ],
    },
]


def test_normalize_removes_accents_and_punctuation():
    assert normalize("Canton Of Graubünden") == "canton of graubunden"


def test_path_matches_ordered_terms():
    assert path_matches(["europe", "Switzerland", "Aargau"], ["europe", "switzerland"])
    assert path_matches(["europe", "Switzerland", "Aargau"], ["switzerland", "aargau"])
    assert not path_matches(["europe", "Switzerland", "Aargau"], ["aargau", "switzerland"])


def test_find_downloads_can_match_country():
    downloads = find_downloads(TREE, ["switzerland"])

    assert [path[-1] for path, _node in downloads] == [
        "Aargau",
        "Canton Of Graubünden",
    ]


def test_common_path_prefix_for_country_downloads():
    downloads = find_downloads(TREE, ["switzerland"])

    assert common_path_prefix(downloads) == ["europe", "Switzerland"]


def test_country_regions_lists_country_level_nodes():
    countries = country_regions(TREE)

    assert [path for path, _node in countries] == [
        ["europe", "Germany"],
        ["europe", "Switzerland"],
    ]


def test_find_regions_can_search_parent_region():
    regions = find_regions(TREE, ["swiss"])

    assert [path for path, _node in regions] == [["europe", "Switzerland"]]


def test_term_matches_text_accepts_prefixes():
    assert term_matches_text("swiss", "Switzerland")
    assert term_matches_text("graubund", "Canton Of Graubünden")
    assert not term_matches_text("xyz", "Switzerland")


def test_find_downloads_can_match_single_region_with_accentless_input():
    downloads = find_downloads(TREE, ["graubunden"])

    assert len(downloads) == 1
    assert downloads[0][0] == ["europe", "Switzerland", "Canton Of Graubünden"]
    assert downloads[0][1]["mapPathUrl"].endswith("CH1000.zip")


def test_format_size():
    assert format_size(0) == "unknown size"
    assert format_size(512) == "512 B"
    assert format_size(2048) == "2.0 KB"
    assert format_size(2 * 1024 * 1024) == "2.0 MB"


def test_official_map_prefix_from_zip_url():
    assert official_map_prefix("https://example.test/Mapinfo/V1/CH0100.zip") == "CH0100"
    assert official_map_prefix("https://example.test/no-prefix.zip") is None


def test_existing_extracted_maps(tmp_path):
    (tmp_path / "CH01002603203YR1DZ005004.map").write_bytes(b"map")
    (tmp_path / "CH02002603203YR1DZ005004.map").write_bytes(b"map")

    matches = existing_extracted_maps(tmp_path, "https://example.test/CH0100.zip")

    assert [path.name for path in matches] == ["CH01002603203YR1DZ005004.map"]
